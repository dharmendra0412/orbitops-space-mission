from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import math
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx
import numpy as np
import rasterio
from pyproj import CRS, Transformer

from app.services.lalt_client import LaltClient
from app.services.lalt_pds3 import (
    LALT_GT_SP_DUMMY_KM,
    LALT_GT_SP_EASTERNMOST_LONGITUDE,
    LALT_GT_SP_IMAGE_BYTES,
    LALT_GT_SP_IMAGE_URL,
    LALT_GT_SP_LABEL_URL,
    LALT_GT_SP_LINES,
    LALT_GT_SP_MAXIMUM_LATITUDE,
    LALT_GT_SP_MINIMUM_LATITUDE,
    LALT_GT_SP_RADIUS_KM,
    LALT_GT_SP_SAMPLES,
    LALT_GT_SP_WESTERNMOST_LONGITUDE,
    parse_and_validate_lalt_gt_sp_label,
    validate_lalt_gt_sp_image_file,
)
from app.services.pds3_label import parse_pds3_label


MAX_LABEL_BYTES = 64_000
EXPECTED_LOLA_IMAGE_BYTES = 115_034_112
LOLA_LINES = 7_584
LOLA_SAMPLES = 7_584
LOLA_REFERENCE_RADIUS_M = 1_737_400.0
LALT_FIRST_OVERLAP_LATITUDE = -85.0


def _download_fixed_source(url: str, destination: Path, *, expected_bytes: int | None, max_bytes: int) -> tuple[int, str]:
    if not url.startswith("https://data.darts.isas.jaxa.jp/"):
        raise RuntimeError("Refusing an unapproved Kaguya LALT source URL")
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix(destination.suffix + ".part")
    digest = hashlib.sha256()
    total = 0
    try:
        with httpx.Client(timeout=90.0, follow_redirects=False) as client:
            with client.stream(
                "GET",
                url,
                headers={"Accept": "application/octet-stream", "Accept-Encoding": "identity"},
            ) as response:
                if response.is_redirect:
                    raise RuntimeError("Kaguya LALT source redirected; refusing an unverified destination")
                if response.status_code != 200:
                    response.raise_for_status()
                    raise RuntimeError(f"Unexpected Kaguya LALT HTTP status {response.status_code}")
                if response.url.host != "data.darts.isas.jaxa.jp":
                    raise RuntimeError("Kaguya LALT response came from an unexpected host")
                content_length = response.headers.get("content-length")
                if expected_bytes is not None and content_length is not None:
                    if int(content_length) != expected_bytes:
                        raise RuntimeError("Kaguya LALT Content-Length does not match the PDS3 label")
                with temporary.open("wb") as output:
                    for chunk in response.iter_bytes(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        total += len(chunk)
                        if total > max_bytes:
                            raise RuntimeError("Kaguya LALT response exceeded the configured size limit")
                        output.write(chunk)
                        digest.update(chunk)
        if expected_bytes is not None and total != expected_bytes:
            raise RuntimeError(
                f"Kaguya LALT byte count mismatch: expected {expected_bytes}, received {total}"
            )
        os.replace(temporary, destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return total, digest.hexdigest()


def _number(metadata: dict[str, str], key: str) -> float:
    value = float(metadata[key].split("<", 1)[0].strip())
    if not math.isfinite(value):
        raise RuntimeError(f"LOLA label field {key} is not finite")
    return value


def _stats(values: np.ndarray) -> dict[str, float | int]:
    if values.size == 0:
        raise RuntimeError("No valid cross-sensor comparison samples were found")
    absolute = np.abs(values)
    return {
        "sample_count": int(values.size),
        "bias_m": float(np.mean(values)),
        "median_residual_m": float(np.median(values)),
        "mae_m": float(np.mean(absolute)),
        "rmse_m": float(np.sqrt(np.mean(np.square(values)))),
        "p95_absolute_residual_m": float(np.percentile(absolute, 95)),
        "p99_absolute_residual_m": float(np.percentile(absolute, 99)),
        "maximum_absolute_residual_m": float(np.max(absolute)),
    }


def compare_lalt_grid_to_lola(
    *,
    lalt_image: Path,
    lola_image: Path,
    lola_jp2: Path,
    lola_label: Path,
) -> dict[str, Any]:
    lola_metadata = parse_pds3_label(lola_label.read_text(encoding="ascii"))
    if lola_metadata.get("FILE_NAME") != "LDEM_85S_40M.IMG":
        raise RuntimeError("Unexpected LOLA reference image label")
    lola_scale_m = _number(lola_metadata, "SCALING_FACTOR")
    if lola_metadata.get("COORDINATE_SYSTEM_NAME") != "MEAN EARTH/POLAR AXIS OF DE421":
        raise RuntimeError("LOLA reference frame does not match the LALT DE421 Mean Earth/Polar Axis frame")
    lola_radius_km = _number(lola_metadata, "A_AXIS_RADIUS")
    if not math.isclose(lola_radius_km, LALT_GT_SP_RADIUS_KM, abs_tol=1e-9):
        raise RuntimeError("LOLA and LALT reference sphere radii do not match")
    lola_min_dn = int(float(lola_metadata["DERIVED_MINIMUM"]))
    lola_max_dn = int(float(lola_metadata["DERIVED_MAXIMUM"]))

    if lola_image.stat().st_size != EXPECTED_LOLA_IMAGE_BYTES:
        raise RuntimeError("LOLA reference IMG does not match its validated PDS3 byte size")
    validate_lalt_gt_sp_image_file(lalt_image)

    lalt_grid = np.memmap(
        lalt_image,
        dtype="<f4",
        mode="r",
        shape=(LALT_GT_SP_LINES, LALT_GT_SP_SAMPLES),
    )
    lola_grid = np.memmap(
        lola_image,
        dtype="<i2",
        mode="r",
        shape=(LOLA_LINES, LOLA_SAMPLES),
    )

    with rasterio.open(lola_jp2) as reference:
        if reference.width != LOLA_SAMPLES or reference.height != LOLA_LINES or reference.crs is None:
            raise RuntimeError("LOLA JP2 reference lacks the expected dimensions or CRS")
        geographic_crs = CRS.from_proj4(
            "+proj=longlat +R=1737400 +no_defs +type=crs"
        )
        transformer = Transformer.from_crs(geographic_crs, reference.crs, always_xy=True)
        inverse_affine = ~reference.transform

        longitude = (
            LALT_GT_SP_WESTERNMOST_LONGITUDE
            + np.arange(LALT_GT_SP_SAMPLES, dtype=np.float64) / 32.0
        )
        longitude_signed = np.where(longitude > 180.0, longitude - 360.0, longitude)
        nearest_residual_rows: list[np.ndarray] = []
        neighborhood_residual_rows: list[np.ndarray] = []
        neighborhood_valid_count = 0
        total_overlap_cells = 0
        total_lalt_valid_cells = 0
        total_matched_cells = 0
        total_lalt_dummy_cells = 0
        total_out_of_bounds_cells = 0

        for line_index in range(LALT_GT_SP_LINES):
            latitude = (
                LALT_GT_SP_MAXIMUM_LATITUDE
                - line_index / 128.0
            )
            if latitude > LALT_FIRST_OVERLAP_LATITUDE:
                continue

            total_overlap_cells += LALT_GT_SP_SAMPLES
            lalt_km = np.asarray(lalt_grid[line_index], dtype=np.float64)
            lalt_valid = (
                np.isfinite(lalt_km)
                & (np.abs(lalt_km - LALT_GT_SP_DUMMY_KM) > 1e-5)
            )
            total_lalt_valid_cells += int(np.count_nonzero(lalt_valid))
            total_lalt_dummy_cells += int(LALT_GT_SP_SAMPLES - np.count_nonzero(lalt_valid))

            latitude_values = np.full(LALT_GT_SP_SAMPLES, latitude, dtype=np.float64)
            x_map, y_map = transformer.transform(longitude_signed, latitude_values)
            column_corner = (
                inverse_affine.a * x_map
                + inverse_affine.b * y_map
                + inverse_affine.c
            )
            row_corner = (
                inverse_affine.d * x_map
                + inverse_affine.e * y_map
                + inverse_affine.f
            )
            lola_columns = np.rint(column_corner - 0.5).astype(np.int32)
            lola_rows = np.rint(row_corner - 0.5).astype(np.int32)
            in_bounds = (
                (lola_rows >= 1)
                & (lola_rows < LOLA_LINES - 1)
                & (lola_columns >= 1)
                & (lola_columns < LOLA_SAMPLES - 1)
            )
            total_out_of_bounds_cells += int(LALT_GT_SP_SAMPLES - np.count_nonzero(in_bounds))
            valid = lalt_valid & in_bounds
            if not np.any(valid):
                continue

            rows = lola_rows[valid]
            columns = lola_columns[valid]
            lola_dn = np.asarray(lola_grid[rows, columns], dtype=np.int32)
            lola_valid = (lola_dn >= lola_min_dn) & (lola_dn <= lola_max_dn)
            if not np.any(lola_valid):
                continue

            lalt_height_m = lalt_km[valid][lola_valid] * 1000.0
            lola_height_m = lola_dn[lola_valid].astype(np.float64) * lola_scale_m
            nearest_residual_rows.append(lalt_height_m - lola_height_m)
            total_matched_cells += int(lola_valid.sum())

            valid_rows = rows[lola_valid]
            valid_columns = columns[lola_valid]
            neighbors = np.stack(
                [
                    np.asarray(
                        lola_grid[valid_rows + row_delta, valid_columns + column_delta],
                        dtype=np.float64,
                    )
                    for row_delta in (-1, 0, 1)
                    for column_delta in (-1, 0, 1)
                ],
                axis=0,
            )
            neighbors = np.where(
                (neighbors >= lola_min_dn) & (neighbors <= lola_max_dn),
                neighbors,
                np.nan,
            )
            neighborhood_median_dn = np.nanmedian(neighbors, axis=0)
            neighborhood_valid = np.isfinite(neighborhood_median_dn)
            neighborhood_valid_count += int(np.count_nonzero(neighborhood_valid))
            if np.any(neighborhood_valid):
                neighborhood_median = neighborhood_median_dn[neighborhood_valid] * lola_scale_m
                neighborhood_residual_rows.append(
                    lalt_height_m[neighborhood_valid] - neighborhood_median
                )

    nearest_residuals = np.concatenate(nearest_residual_rows)
    neighborhood_residuals = np.concatenate(neighborhood_residual_rows)
    return {
        "comparison": "Kaguya SELENE LALT GT south-polar grid versus LRO LOLA LDEM_85S_40M",
        "lalt_dataset_id": "SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0",
        "lalt_grid": {
            "lines": LALT_GT_SP_LINES,
            "line_samples": LALT_GT_SP_SAMPLES,
            "sample_type": "PC_REAL little-endian float32",
            "height_unit": "km converted to m",
            "dummy_value_km": LALT_GT_SP_DUMMY_KM,
            "reference_sphere_radius_km": LALT_GT_SP_RADIUS_KM,
            "coordinate_reference": "MEAN EARTH/POLAR AXIS OF DE421",
            "latitude_coverage_degrees": [LALT_GT_SP_MAXIMUM_LATITUDE, LALT_GT_SP_MINIMUM_LATITUDE],
            "latitude_spacing_degrees": 1.0 / 128.0,
            "longitude_spacing_degrees": 1.0 / 32.0,
        },
        "lola_grid": {
            "lines": LOLA_LINES,
            "line_samples": LOLA_SAMPLES,
            "map_scale_m_per_pixel": 40.0,
            "height_scaling_factor_m_per_dn": lola_scale_m,
            "reference_sphere_radius_m": LOLA_REFERENCE_RADIUS_M,
            "coordinate_reference": lola_metadata.get("COORDINATE_SYSTEM_NAME"),
        },
        "overlap": {
            "latitude_range_degrees": [-90.0, LALT_FIRST_OVERLAP_LATITUDE],
            "candidate_lalt_cells": total_overlap_cells,
            "valid_lalt_cells": total_lalt_valid_cells,
            "lalt_dummy_or_nonfinite_cells": total_lalt_dummy_cells,
            "lola_in_bounds_cells": total_overlap_cells - total_out_of_bounds_cells,
            "out_of_bounds_cells": total_out_of_bounds_cells,
            "matched_valid_cells": total_matched_cells,
            "matched_cells_with_valid_3x3_neighborhood": neighborhood_valid_count,
        },
        "nearest_lola_pixel": _stats(nearest_residuals),
        "lola_3x3_neighborhood_median": _stats(neighborhood_residuals),
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "This is a cross-sensor consistency comparison, not independent geodetic ground truth. "
            "The LALT image is a spherical-interpolation grid derived from LALT_LGT_TS and rounded "
            "to 0.001 km; it is not raw laser shots. Both labels identify the DE421 Mean Earth/Polar "
            "Axis frame and 1737.4 km reference sphere. Horizontal orbit/geolocation uncertainty, "
            "grid interpolation, differing spatial resolutions, and local terrain slope can affect "
            "residuals. Nearest-pixel and 3x3 LOLA-neighborhood-median statistics are both reported; "
            "neither is a substitute for independent control."
        ),
    }


async def _verify_live_label_client_matches_downloaded_label(label_path: Path) -> dict[str, Any]:
    client = LaltClient()
    source_url, source_label = await client.fetch_gt_sp_label()
    local_bytes = label_path.read_bytes()
    source_bytes = source_label.encode("ascii")
    if source_url != LALT_GT_SP_LABEL_URL:
        raise RuntimeError("Live LALT label client returned an unexpected source URL")
    if source_bytes != local_bytes:
        raise RuntimeError("Live LALT label client differs from the detached label downloaded for validation")
    return {
        "source_url": source_url,
        "bytes_checked": len(source_bytes),
        "sha256": hashlib.sha256(source_bytes).hexdigest(),
        "matches_downloaded_validation_label": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate Kaguya LALT PDS3 south-polar grid and compare with LOLA.")
    parser.add_argument("--lola-image", type=Path, required=True)
    parser.add_argument("--lola-jp2", type=Path, required=True)
    parser.add_argument("--lola-label", type=Path, required=True)
    parser.add_argument("--lalt-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    args.lalt_dir.mkdir(parents=True, exist_ok=True)
    label_path = args.lalt_dir / "LALT_GT_SP_IMG.lbl"
    image_path = args.lalt_dir / "LALT_GT_SP_IMG.IMG"
    label_bytes, label_sha256 = _download_fixed_source(
        LALT_GT_SP_LABEL_URL,
        label_path,
        expected_bytes=None,
        max_bytes=MAX_LABEL_BYTES,
    )
    label_text = label_path.read_text(encoding="ascii")
    lalt_metadata = parse_and_validate_lalt_gt_sp_label(label_text)
    live_label_validation = asyncio.run(_verify_live_label_client_matches_downloaded_label(label_path))
    image_bytes, image_sha256 = _download_fixed_source(
        LALT_GT_SP_IMAGE_URL,
        image_path,
        expected_bytes=LALT_GT_SP_IMAGE_BYTES,
        max_bytes=LALT_GT_SP_IMAGE_BYTES,
    )
    image_validation = validate_lalt_gt_sp_image_file(image_path)
    comparison = compare_lalt_grid_to_lola(
        lalt_image=image_path,
        lola_image=args.lola_image,
        lola_jp2=args.lola_jp2,
        lola_label=args.lola_label,
    )
    result = {
        "source": {
            "label_url": LALT_GT_SP_LABEL_URL,
            "image_url": LALT_GT_SP_IMAGE_URL,
            "label_bytes": label_bytes,
            "label_sha256": label_sha256,
            "image_bytes": image_bytes,
            "image_sha256": image_sha256,
            "image_validation": image_validation,
            "live_api_label_client_validation": live_label_validation,
            "metadata": {
                key: value
                for key, value in lalt_metadata.items()
                if key != "source_label"
            },
        },
        "comparison": comparison,
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
