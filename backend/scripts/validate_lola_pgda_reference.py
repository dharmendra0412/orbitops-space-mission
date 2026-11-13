from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import rasterio
from rasterio.enums import Resampling
from rasterio.vrt import WarpedVRT
from rasterio.windows import Window


PGDA_REFERENCE_URL = (
    "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/LDEM_80S_40MPP_ADJ.TIF"
)
PGDA_PRODUCT_PAGE = "https://pgda.gsfc.nasa.gov/products/90"
EXPECTED_SOURCE_SHAPE = (7_584, 7_584)
WINDOW_SIZE = 512
WINDOW_ORIGINS = (
    (1_500, 1_500),
    (1_500, 5_500),
    (5_500, 1_500),
    (5_500, 5_500),
)


def _validate_lunar_polar_crs(crs, *, source_name: str) -> str:
    if crs is None:
        raise RuntimeError(f"{source_name} does not declare a coordinate reference system")
    wkt = crs.to_wkt()
    normalized = wkt.lower()
    if "polar_stereographic" not in normalized and "stereographic" not in normalized:
        raise RuntimeError(f"{source_name} is not declared as a polar stereographic grid")
    if "moon" not in normalized:
        raise RuntimeError(f"{source_name} CRS does not identify a lunar coordinate system")
    return wkt


def _summarize_differences(raw_height: np.ndarray, reference_height: np.ma.MaskedArray) -> dict[str, object]:
    ref = np.ma.asarray(reference_height, dtype=np.float64)
    raw = np.asarray(raw_height, dtype=np.float64)
    valid = ~np.ma.getmaskarray(ref) & np.isfinite(ref.filled(np.nan)) & np.isfinite(raw)
    if ref.fill_value is not None:
        valid &= ref.filled(np.nan) != ref.fill_value
    count = int(np.count_nonzero(valid))
    if count < 100_000:
        raise RuntimeError(
            f"Insufficient overlapping non-nodata pixels for a meaningful check: {count}"
        )

    difference = ref.data[valid] - raw[valid]
    absolute = np.abs(difference)
    return {
        "valid_pixel_pairs": count,
        "reference_minus_raw_bias_m": float(np.mean(difference)),
        "median_difference_m": float(np.median(difference)),
        "mean_absolute_difference_m": float(np.mean(absolute)),
        "root_mean_square_difference_m": float(math.sqrt(np.mean(np.square(difference)))),
        "absolute_difference_p95_m": float(np.percentile(absolute, 95)),
        "absolute_difference_p99_m": float(np.percentile(absolute, 99)),
        "minimum_difference_m": float(np.min(difference)),
        "maximum_difference_m": float(np.max(difference)),
    }


def validate_against_pgda(
    image_path: Path,
    jp2_path: Path,
    *,
    windows: tuple[tuple[int, int], ...] = WINDOW_ORIGINS,
) -> dict[str, object]:
    raw = np.memmap(
        image_path,
        dtype="<i2",
        mode="r",
        shape=EXPECTED_SOURCE_SHAPE,
    )

    with rasterio.open(jp2_path) as grid:
        if (grid.height, grid.width) != EXPECTED_SOURCE_SHAPE:
            raise RuntimeError("The source JP2 grid dimensions differ from the validated IMG")
        source_crs_wkt = _validate_lunar_polar_crs(grid.crs, source_name="PDS LOLA JP2")
        source_transform = tuple(grid.transform)

        # GDAL's /vsicurl/ reads only the COG byte ranges needed for these
        # bounded windows; this does not download the 685 MB reference TIFF.
        remote_path = "/vsicurl/" + PGDA_REFERENCE_URL
        with rasterio.Env(
            GDAL_DISABLE_READDIR_ON_OPEN="EMPTY_DIR",
            CPL_VSIL_CURL_ALLOWED_EXTENSIONS=".TIF",
            GDAL_HTTP_MULTIRANGE="YES",
            GDAL_HTTP_MERGE_CONSECUTIVE_RANGES="YES",
        ):
            with rasterio.open(remote_path) as pgda:
                if pgda.count != 1:
                    raise RuntimeError(
                        f"Expected one PGDA elevation band, received {pgda.count}"
                    )
                pgda_crs_wkt = _validate_lunar_polar_crs(
                    pgda.crs, source_name="NASA PGDA reference DEM"
                )
                if pgda.dtypes[0] not in ("int16", "uint16", "int32", "float32", "float64"):
                    raise RuntimeError(
                        f"Unsupported PGDA elevation sample type: {pgda.dtypes[0]}"
                    )
                if pgda.nodata is None:
                    raise RuntimeError(
                        "PGDA reference DEM has no declared nodata value; refusing ambiguous comparisons"
                    )

                with WarpedVRT(
                    pgda,
                    crs=grid.crs,
                    transform=grid.transform,
                    width=grid.width,
                    height=grid.height,
                    resampling=Resampling.bilinear,
                    nodata=np.nan,
                    dtype="float32",
                ) as aligned:
                    window_results: list[dict[str, object]] = []
                    all_differences: list[np.ndarray] = []
                    for row_off, col_off in windows:
                        window = Window(col_off, row_off, WINDOW_SIZE, WINDOW_SIZE)
                        raw_dn = np.asarray(
                            raw[
                                row_off : row_off + WINDOW_SIZE,
                                col_off : col_off + WINDOW_SIZE,
                            ],
                            dtype=np.float32,
                        )
                        # The PDS GDR label defines HEIGHT = DN * SCALING_FACTOR;
                        # this selected product's factor is 0.5 m/DN.
                        raw_height_m = raw_dn * 0.5
                        reference = aligned.read(1, window=window, masked=True)
                        summary = _summarize_differences(raw_height_m, reference)
                        summary["source_window"] = {
                            "row_offset": row_off,
                            "column_offset": col_off,
                            "size_pixels": WINDOW_SIZE,
                        }
                        window_results.append(summary)
                        ref = np.ma.asarray(reference, dtype=np.float64)
                        valid = (
                            ~np.ma.getmaskarray(ref)
                            & np.isfinite(ref.filled(np.nan))
                            & np.isfinite(raw_height_m)
                        )
                        all_differences.append(
                            ref.data[valid] - raw_height_m[valid]
                        )

    combined = np.concatenate(all_differences)
    absolute = np.abs(combined)
    return {
        "reference": {
            "provider": "NASA Goddard Planetary Geodesy Data Archive",
            "product": "LDEM_80S_40MPP_ADJ",
            "product_page": PGDA_PRODUCT_PAGE,
            "remote_cog_url": PGDA_REFERENCE_URL,
            "reference_frame": "MOON_ME / DE421 as stated by the PGDA product page",
            "embedded_crs_definition": (
                "Moon (2015) - Sphere / Ocentric / South Polar, IAU 30100, "
                "as read from the GeoTIFF WKT"
            ),
            "frame_reconciliation_status": (
                "The product page declares MOON_ME / DE421, while the embedded WKT "
                "names the IAU 30100 Moon (2015) spherical CRS. This workflow records "
                "both declarations but does not independently establish their frame "
                "equivalence; treat residual statistics as exploratory pending a "
                "documented frame transformation/reconciliation."
            ),
            "interpretation": (
                "Separately adjusted and processed LOLA reference DEM. This is a "
                "cross-product geodetic/height comparison, not an independent sensor "
                "or independent measurement campaign."
            ),
        },
        "comparison": {
            "source_product": "LDEM_85S_40M PDS GDR",
            "source_crs": source_crs_wkt,
            "reference_crs": pgda_crs_wkt,
            "source_geotransform": source_transform,
            "alignment": "PGDA COG warped to the source JP2 pixel grid with bilinear resampling",
            "source_height_conversion": "raw signed DN * 0.5 m/DN",
            "sample_windows": window_results,
            "combined_valid_pixel_pairs": int(combined.size),
            "reference_minus_raw_bias_m": float(np.mean(combined)),
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
            "The PGDA product is a separately adjusted LOLA DEM, not an independent instrument dataset.",
            "The product page declares MOON_ME / DE421, but the embedded GeoTIFF WKT names IAU 30100 Moon (2015); explicit frame equivalence remains to be reconciled.",
            "The comparison samples four bounded 512x512 windows rather than the full source raster.",
            "The PGDA COG is read by HTTP range requests; the full 685 MB file is not downloaded.",
            "Bilinear resampling is used to align the reference DEM to the PDS source grid.",
            "Residuals characterize cross-product agreement and must not be represented as absolute ground-truth error.",
        ],
    }


def main() -> None:
    root = Path("data/raw/lola")
    image_path = root / "ldem_85s_40m.img"
    jp2_path = root / "ldem_85s_40m.jp2"
    if not image_path.is_file() or not jp2_path.is_file():
        raise SystemExit("Validated LOLA IMG and JP2 artifacts must exist before PGDA comparison")

    result = validate_against_pgda(image_path, jp2_path)
    manifest = root / "ldem_85s_40m.pgda-comparison.json"
    manifest.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
