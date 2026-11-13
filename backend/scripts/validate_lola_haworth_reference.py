from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window


HAWORTH_DEM_URL = (
    "https://pgda.gsfc.nasa.gov/data/LOLA_5mpp/Haworth/"
    "Haworth_final_adj_5mpp_surf.tif"
)
HAWORTH_PRODUCT_PAGE = "https://pgda.gsfc.nasa.gov/products/78"
MAX_DOWNLOAD_BYTES = 256 * 1024 * 1024
SOURCE_SHAPE = (7_584, 7_584)
WINDOW_SIZE = 512
MIN_VALID_PIXELS_PER_WINDOW = 100_000


def download_reference(url: str, destination: Path) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "ORBITOPS-Scientific-Data-Validation/1.0"},
    )
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".part", dir=destination.parent
    )
    total = 0
    digest = hashlib.sha256()
    try:
        with os.fdopen(fd, "wb") as output, urllib.request.urlopen(
            request, timeout=60
        ) as response:
            content_type = response.headers.get("Content-Type", "").lower()
            if "image/tiff" not in content_type and "application/octet-stream" not in content_type:
                raise RuntimeError(
                    f"Unexpected Haworth DEM response content type: {content_type!r}"
                )
            declared_length = response.headers.get("Content-Length")
            if declared_length and int(declared_length) > MAX_DOWNLOAD_BYTES:
                raise RuntimeError(
                    f"Haworth DEM exceeds the {MAX_DOWNLOAD_BYTES}-byte download limit"
                )
            while chunk := response.read(1024 * 1024):
                total += len(chunk)
                if total > MAX_DOWNLOAD_BYTES:
                    raise RuntimeError(
                        f"Haworth DEM exceeded the {MAX_DOWNLOAD_BYTES}-byte download limit"
                    )
                digest.update(chunk)
                output.write(chunk)
            output.flush()
            os.fsync(output.fileno())
        if total < 1024:
            raise RuntimeError("Haworth DEM download is unexpectedly small")
        os.replace(temporary_name, destination)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise

    return {"url": url, "bytes": total, "sha256": digest.hexdigest()}


def _validate_reference(dataset: rasterio.DatasetReader) -> str:
    if dataset.count != 1:
        raise RuntimeError(f"Expected one Haworth DEM band, got {dataset.count}")
    if dataset.crs is None:
        raise RuntimeError("Haworth DEM does not declare a CRS")
    wkt = dataset.crs.to_wkt()
    crs_parameters = dataset.crs.to_dict()
    # GDAL may serialize a planetary CRS without preserving the body name in
    # its WKT. Validate the numeric projection/body parameters instead. The
    # PGDA Product 78 page is the authority for MOON_ME / JPL DE421; the raster
    # must independently declare south-polar stereographic geometry on the
    # 1,737,400 m lunar reference sphere.
    projection_declared = crs_parameters.get("proj") == "stere"
    south_polar = math.isclose(
        float(crs_parameters.get("lat_0", math.nan)), -90.0, abs_tol=1e-8
    )
    lunar_radius = math.isclose(
        float(crs_parameters.get("a", math.nan)), 1_737_400.0, abs_tol=1e-3
    )
    if not (projection_declared and south_polar and lunar_radius):
        raise RuntimeError(
            "Haworth DEM CRS does not match the required lunar south-polar "
            "stereographic geometry on a 1,737,400 m sphere; "
            f"parameters={crs_parameters!r}, WKT={wkt}"
        )
    if not math.isclose(abs(dataset.transform.a), 5.0, abs_tol=1e-6):
        raise RuntimeError(
            f"Expected 5 m/pixel Haworth DEM, got X pixel size {dataset.transform.a}"
        )
    if not math.isclose(abs(dataset.transform.e), 5.0, abs_tol=1e-6):
        raise RuntimeError(
            f"Expected 5 m/pixel Haworth DEM, got Y pixel size {dataset.transform.e}"
        )
    if dataset.nodata is None:
        raise RuntimeError("Haworth DEM has no declared nodata value")
    return wkt


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _metrics(raw_height: np.ndarray, reference: np.ma.MaskedArray) -> tuple[dict[str, object], np.ndarray]:
    ref = np.ma.asarray(reference, dtype=np.float64)
    raw = np.asarray(raw_height, dtype=np.float64)
    valid = (
        ~np.ma.getmaskarray(ref)
        & np.isfinite(ref.filled(np.nan))
        & np.isfinite(raw)
    )
    if ref.fill_value is not None:
        valid &= ref.filled(np.nan) != ref.fill_value
    difference = ref.data[valid] - raw[valid]
    if difference.size < MIN_VALID_PIXELS_PER_WINDOW:
        raise RuntimeError(
            f"Only {difference.size} valid pixels in selected Haworth comparison window"
        )
    absolute = np.abs(difference)
    return (
        {
            "valid_pixel_pairs": int(difference.size),
            "reference_minus_source_bias_m": float(np.mean(difference)),
            "median_difference_m": float(np.median(difference)),
            "mean_absolute_difference_m": float(np.mean(absolute)),
            "root_mean_square_difference_m": float(math.sqrt(np.mean(np.square(difference)))),
            "absolute_difference_p95_m": float(np.percentile(absolute, 95)),
            "absolute_difference_p99_m": float(np.percentile(absolute, 99)),
            "minimum_difference_m": float(np.min(difference)),
            "maximum_difference_m": float(np.max(difference)),
        },
        difference,
    )


def compare_haworth_site_dem(
    image_path: Path,
    jp2_path: Path,
    haworth_path: Path,
) -> dict[str, object]:
    raw = np.memmap(image_path, dtype="<i2", mode="r", shape=SOURCE_SHAPE)
    selected: list[tuple[int, int, int]] = []
    window_results: list[dict[str, object]] = []
    differences: list[np.ndarray] = []

    with rasterio.open(jp2_path) as source_grid:
        if (source_grid.height, source_grid.width) != SOURCE_SHAPE:
            raise RuntimeError("PDS source JP2 dimensions do not match validated IMG")
        with rasterio.open(haworth_path) as haworth:
            haworth_wkt = _validate_reference(haworth)
            reference_raster_metadata = {
                "width": haworth.width,
                "height": haworth.height,
                "dtype": haworth.dtypes[0],
                "nodata": haworth.nodata,
                "transform": tuple(haworth.transform),
            }
            with WarpedVRT(
                haworth,
                crs=source_grid.crs,
                transform=source_grid.transform,
                width=source_grid.width,
                height=source_grid.height,
                resampling=Resampling.bilinear,
                nodata=np.nan,
                dtype="float32",
            ) as aligned:
                # Tile the source grid without overlap and select up to four
                # tiles with the strongest real Haworth DEM coverage.
                candidates: list[tuple[int, int, int]] = []
                for row_off in range(0, SOURCE_SHAPE[0] - WINDOW_SIZE + 1, WINDOW_SIZE):
                    for col_off in range(0, SOURCE_SHAPE[1] - WINDOW_SIZE + 1, WINDOW_SIZE):
                        window = Window(col_off, row_off, WINDOW_SIZE, WINDOW_SIZE)
                        valid_count = int(np.count_nonzero(aligned.read_masks(1, window=window)))
                        if valid_count >= MIN_VALID_PIXELS_PER_WINDOW:
                            candidates.append((valid_count, row_off, col_off))
                candidates.sort(reverse=True)
                selected = candidates[:4]
                if not selected:
                    raise RuntimeError(
                        "Haworth 5 m DEM has no 512x512 source-grid tile with at least "
                        f"{MIN_VALID_PIXELS_PER_WINDOW} valid pixels"
                    )

                for valid_count, row_off, col_off in selected:
                    window = Window(col_off, row_off, WINDOW_SIZE, WINDOW_SIZE)
                    source_dn = np.asarray(
                        raw[
                            row_off : row_off + WINDOW_SIZE,
                            col_off : col_off + WINDOW_SIZE,
                        ],
                        dtype=np.float32,
                    )
                    # PDS source label: HEIGHT = DN * 0.5 m/DN.
                    source_height_m = source_dn * 0.5
                    reference = aligned.read(1, window=window, masked=True)
                    metrics, residuals = _metrics(source_height_m, reference)
                    metrics["source_window"] = {
                        "row_offset": row_off,
                        "column_offset": col_off,
                        "size_pixels": WINDOW_SIZE,
                        "valid_mask_pixels": valid_count,
                    }
                    window_results.append(metrics)
                    differences.append(residuals)

    combined = np.concatenate(differences)
    absolute = np.abs(combined)
    return {
        "reference": {
            "provider": "NASA Goddard Planetary Geodesy Data Archive",
            "product": "Haworth_final_adj_5mpp_surf.tif",
            "product_page": HAWORTH_PRODUCT_PAGE,
            "source_url": HAWORTH_DEM_URL,
            "pixel_scale_m": 5,
            "horizontal_reference_frame": "MOON_ME / JPL DE421, as declared by PGDA product page",
            "vertical_datum": "height relative to lunar mean radius 1,737,400 m",
            "processing": (
                "LOLA tracks iteratively co-adjusted for this site; this is a "
                "separate regional LOLA processing product, not independent sensor truth."
            ),
            "known_quality_context": (
                "PGDA reports median RMS Z error around 0.30-0.50 m within site ROIs; "
                "roughly 90% of 5 m pixels are interpolated."
            ),
            "embedded_crs_wkt": haworth_wkt,
            "raster_metadata": reference_raster_metadata,
        },
        "comparison": {
            "source_product": "LDEM_85S_40M PDS GDR",
            "source_height_conversion": "raw signed DN * 0.5 m/DN",
            "alignment": "5 m Haworth DEM bilinearly resampled onto the PDS 40 m pixel grid",
            "selected_non_overlapping_windows": window_results,
            "valid_pixel_pairs": int(combined.size),
            "reference_minus_source_bias_m": float(np.mean(combined)),
            "median_difference_m": float(np.median(combined)),
            "mean_absolute_difference_m": float(np.mean(absolute)),
            "root_mean_square_difference_m": float(math.sqrt(np.mean(np.square(combined)))),
            "absolute_difference_p95_m": float(np.percentile(absolute, 95)),
            "absolute_difference_p99_m": float(np.percentile(absolute, 99)),
            "minimum_difference_m": float(np.min(combined)),
            "maximum_difference_m": float(np.max(combined)),
        },
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
        "limitations": [
            "The reference is a separately co-adjusted LOLA regional DEM, not an independent instrument dataset.",
            "The comparison samples up to four non-overlapping 512x512 windows with real Haworth coverage.",
            "The 5 m DEM is bilinearly resampled to the PDS 40 m grid.",
            "PGDA reports substantial interpolation in the 5 m regional DEM; its published uncertainty context must be considered.",
            "Residuals are cross-product consistency statistics, not absolute accuracy or ground-truth error.",
        ],
    }


def main() -> None:
    root = Path("data/raw/lola")
    image_path = root / "ldem_85s_40m.img"
    jp2_path = root / "ldem_85s_40m.jp2"
    if not image_path.is_file() or not jp2_path.is_file():
        raise SystemExit("Validated PDS LOLA IMG and JP2 artifacts are required first")

    reference_path = root / "haworth_5mpp_surf.tif"
    download = (
        {"cached": True, "bytes": reference_path.stat().st_size}
        if reference_path.is_file()
        else download_reference(HAWORTH_DEM_URL, reference_path)
    )
    download["sha256"] = download.get("sha256") or _sha256_file(reference_path)
    result = compare_haworth_site_dem(image_path, jp2_path, reference_path)
    result["download"] = download
    manifest = root / "ldem_85s_40m.haworth-comparison.json"
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
