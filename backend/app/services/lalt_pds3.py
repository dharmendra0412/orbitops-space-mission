from __future__ import annotations

import math
import re
import struct
from pathlib import Path
from typing import Any

from app.services.pds3_label import PdsLabelError, parse_pds3_label


LALT_GT_SP_DATA_SET_ID = "SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0"
LALT_GT_SP_LINES = 1_408
LALT_GT_SP_SAMPLES = 11_520
LALT_GT_SP_SAMPLE_BYTES = 4
LALT_GT_SP_IMAGE_BYTES = LALT_GT_SP_LINES * LALT_GT_SP_SAMPLES * LALT_GT_SP_SAMPLE_BYTES
LALT_GT_SP_DUMMY_KM = 99.999
LALT_GT_SP_RADIUS_KM = 1_737.4
LALT_GT_SP_MAXIMUM_LATITUDE = -79.00390625
LALT_GT_SP_MINIMUM_LATITUDE = -89.99609375
LALT_GT_SP_WESTERNMOST_LONGITUDE = 0.015625
LALT_GT_SP_EASTERNMOST_LONGITUDE = 359.984375
LALT_GT_SP_LATITUDE_PIXELS_PER_DEGREE = 128.0
LALT_GT_SP_LONGITUDE_PIXELS_PER_DEGREE = 32.0
LALT_GT_SP_IMAGE_URL = (
    "https://data.darts.isas.jaxa.jp/pub/pds3/"
    "sln-l-lalt-5-topo-gt-sp-img-v2.0/data/LALT_GT_SP_IMG.IMG"
)
LALT_GT_SP_LABEL_URL = (
    "https://data.darts.isas.jaxa.jp/pub/pds3/"
    "sln-l-lalt-5-topo-gt-sp-img-v2.0/data/LALT_GT_SP_IMG.lbl"
)


class LaltPdsError(ValueError):
    """Raised when a Kaguya LALT PDS3 product does not match its documented layout."""


_NUMBER_WITH_UNIT = re.compile(
    r"^\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)"
    r"\s*(?:<([^>]+)>)?\s*$"
)


def _number(metadata: dict[str, str], key: str, unit: str | None = None) -> float:
    raw = metadata.get(key)
    match = _NUMBER_WITH_UNIT.fullmatch(raw or "")
    if not match:
        raise LaltPdsError(f"LALT label field {key} is missing or not numeric")
    if unit is not None and (match.group(2) or "").strip().upper() != unit.upper():
        raise LaltPdsError(f"LALT label field {key} must use {unit}")
    value = float(match.group(1))
    if not math.isfinite(value):
        raise LaltPdsError(f"LALT label field {key} must be finite")
    return value


def _integer(metadata: dict[str, str], key: str) -> int:
    value = _number(metadata, key)
    if not value.is_integer():
        raise LaltPdsError(f"LALT label field {key} must be an integer")
    return int(value)


def validate_lalt_gt_sp_label(metadata: dict[str, str]) -> dict[str, Any]:
    """Validate the exact PDS3 LALT south-polar gridded image layout."""
    expected_strings = {
        "PDS_VERSION_ID": "PDS3",
        "DATA_SET_ID": LALT_GT_SP_DATA_SET_ID,
        "SAMPLE_TYPE": "PC_REAL",
        "COORDINATE_SYSTEM_NAME": "MEAN EARTH/POLAR AXIS OF DE421",
        "COORDINATE_SYSTEM_TYPE": "BODY-FIXED ROTATING",
        "MAP_PROJECTION_TYPE": "N/A",
        "POSITIVE_LONGITUDE_DIRECTION": "EAST",
        "TARGET_NAME": "MOON",
        "INSTRUMENT_ID": "LALT",
        "FILE_NAME": "LALT_GT_SP_IMG.IMG",
        "PRODUCT_VERSION_ID": "2.0",
        "BAND_STORAGE_TYPE": "BAND_SEQUENTIAL",
        "COMPRESSION_TYPE": "N/A",
        "STRETCHED_FLAG": "FALSE",
        "MAP_RESOLUTION": "NULL",
        "MAP_SCALE": "NULL",
    }
    for key, expected in expected_strings.items():
        if metadata.get(key) != expected:
            raise LaltPdsError(
                f"LALT label field {key} must be {expected!r}; got {metadata.get(key)!r}"
            )

    expected_numbers = {
        "LINES": (LALT_GT_SP_LINES, None),
        "LINE_SAMPLES": (LALT_GT_SP_SAMPLES, None),
        "BANDS": (1, None),
        "SAMPLE_BITS": (32, None),
        "LINE_FIRST_PIXEL": (1, None),
        "LINE_LAST_PIXEL": (LALT_GT_SP_LINES, None),
        "SAMPLE_FIRST_PIXEL": (1, None),
        "SAMPLE_LAST_PIXEL": (LALT_GT_SP_SAMPLES, None),
        "CENTER_LATITUDE": (-84.5, "DEGREE"),
        "CENTER_LONGITUDE": (180.0, "DEGREE"),
        "LINE_PROJECTION_OFFSET": (703.5, "PIXEL"),
        "SAMPLE_PROJECTION_OFFSET": (5759.5, "PIXEL"),
        "MAP_PROJECTION_ROTATION": (0.0, "DEGREE"),
        "SCALING_FACTOR": (1.0, None),
        "OFFSET": (0.0, None),
        "DUMMY_DATA": (LALT_GT_SP_DUMMY_KM, None),
        "A_AXIS_RADIUS": (LALT_GT_SP_RADIUS_KM, "KM"),
        "B_AXIS_RADIUS": (LALT_GT_SP_RADIUS_KM, "KM"),
        "C_AXIS_RADIUS": (LALT_GT_SP_RADIUS_KM, "KM"),
        "MAXIMUM_LATITUDE": (LALT_GT_SP_MAXIMUM_LATITUDE, None),
        "MINIMUM_LATITUDE": (LALT_GT_SP_MINIMUM_LATITUDE, None),
        "WESTERNMOST_LONGITUDE": (LALT_GT_SP_WESTERNMOST_LONGITUDE, None),
        "EASTERNMOST_LONGITUDE": (LALT_GT_SP_EASTERNMOST_LONGITUDE, None),
        "MAP_RESOLUTION_LATITUDE": (LALT_GT_SP_LATITUDE_PIXELS_PER_DEGREE, "PIXEL/DEGREE"),
        "MAP_RESOLUTION_LONGITUDE": (LALT_GT_SP_LONGITUDE_PIXELS_PER_DEGREE, "PIXEL/DEGREE"),
    }
    for key, (expected, unit) in expected_numbers.items():
        actual = _number(metadata, key, unit)
        if not math.isclose(actual, expected, rel_tol=0.0, abs_tol=1e-9):
            raise LaltPdsError(
                f"LALT label field {key} expected {expected} {unit or ''}; got {actual}"
            )

    if metadata.get("PRODUCT_ID") != "LALT_GT_SP_IMG":
        raise LaltPdsError("LALT label is not the LALT_GT_SP_IMG product")
    if "LALT_GT_SP_IMG.IMG" not in metadata.get("^IMAGE", ""):
        raise LaltPdsError("LALT label does not point to the expected detached IMG file")

    return {
        "dataset_id": metadata["DATA_SET_ID"],
        "product_id": metadata["PRODUCT_ID"],
        "lines": LALT_GT_SP_LINES,
        "line_samples": LALT_GT_SP_SAMPLES,
        "sample_type": "PC_REAL (little-endian IEEE 754 float32)",
        "sample_bits": 32,
        "image_bytes": LALT_GT_SP_IMAGE_BYTES,
        "dummy_value_km": LALT_GT_SP_DUMMY_KM,
        "height_unit": "km",
        "reference_sphere_radius_km": LALT_GT_SP_RADIUS_KM,
        "coordinate_system": metadata["COORDINATE_SYSTEM_NAME"],
        "coordinate_system_type": metadata["COORDINATE_SYSTEM_TYPE"],
        "map_projection_type": metadata["MAP_PROJECTION_TYPE"],
        "maximum_latitude_degrees": LALT_GT_SP_MAXIMUM_LATITUDE,
        "minimum_latitude_degrees": LALT_GT_SP_MINIMUM_LATITUDE,
        "westernmost_longitude_degrees": LALT_GT_SP_WESTERNMOST_LONGITUDE,
        "easternmost_longitude_degrees": LALT_GT_SP_EASTERNMOST_LONGITUDE,
        "latitude_pixels_per_degree": LALT_GT_SP_LATITUDE_PIXELS_PER_DEGREE,
        "longitude_pixels_per_degree": LALT_GT_SP_LONGITUDE_PIXELS_PER_DEGREE,
        "source_label": metadata,
    }


def parse_and_validate_lalt_gt_sp_label(label_text: str) -> dict[str, Any]:
    try:
        metadata = parse_pds3_label(label_text, max_characters=64_000)
    except PdsLabelError as exc:
        raise LaltPdsError(str(exc)) from exc
    return validate_lalt_gt_sp_label(metadata)


def lalt_grid_node_to_lat_lon(line_index: int, sample_index: int) -> tuple[float, float]:
    """Return the source-defined coordinate for a zero-based LALT grid node."""
    if not isinstance(line_index, int) or isinstance(line_index, bool):
        raise LaltPdsError("LALT line index must be an integer")
    if not isinstance(sample_index, int) or isinstance(sample_index, bool):
        raise LaltPdsError("LALT sample index must be an integer")
    if not 0 <= line_index < LALT_GT_SP_LINES:
        raise LaltPdsError("LALT line index is outside the image bounds")
    if not 0 <= sample_index < LALT_GT_SP_SAMPLES:
        raise LaltPdsError("LALT sample index is outside the image bounds")
    latitude = LALT_GT_SP_MAXIMUM_LATITUDE - (
        line_index / LALT_GT_SP_LATITUDE_PIXELS_PER_DEGREE
    )
    longitude = LALT_GT_SP_WESTERNMOST_LONGITUDE + (
        sample_index / LALT_GT_SP_LONGITUDE_PIXELS_PER_DEGREE
    )
    return latitude, longitude


def decode_lalt_pc_real_sample(raw_bytes: bytes) -> float | None:
    """Decode one PDS PC_REAL float32 sample; return None for the declared dummy."""
    if len(raw_bytes) != LALT_GT_SP_SAMPLE_BYTES:
        raise LaltPdsError("A LALT PC_REAL sample must contain exactly four bytes")
    value = struct.unpack("<f", raw_bytes)[0]
    if not math.isfinite(value):
        raise LaltPdsError("LALT PC_REAL sample is not finite")
    if math.isclose(value, LALT_GT_SP_DUMMY_KM, rel_tol=0.0, abs_tol=1e-5):
        return None
    return value


def validate_lalt_gt_sp_image_file(path: Path) -> dict[str, int]:
    """Check the downloaded detached image has the exact label-derived byte size."""
    size = Path(path).stat().st_size
    if size != LALT_GT_SP_IMAGE_BYTES:
        raise LaltPdsError(
            f"LALT image byte size mismatch: expected {LALT_GT_SP_IMAGE_BYTES}, got {size}"
        )
    return {
        "bytes": size,
        "lines": LALT_GT_SP_LINES,
        "line_samples": LALT_GT_SP_SAMPLES,
        "samples": LALT_GT_SP_LINES * LALT_GT_SP_SAMPLES,
    }
