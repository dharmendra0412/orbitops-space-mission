from __future__ import annotations

import math
import re
import struct
from collections.abc import Iterator
from typing import Any


LOLA_MEAN_EARTH_REFERENCE_RADIUS_M = 1_737_400.0


class LolaRasterError(ValueError):
    """Raised when a LOLA GDR image or its map metadata is inconsistent."""


def _number(metadata: dict[str, str], key: str, *, unit: str | None = None) -> float:
    raw = metadata.get(key)
    if raw is None:
        raise LolaRasterError(f"Required PDS label field {key} is missing")
    match = re.fullmatch(
        r"\s*([+-]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][+-]?\d+)?)\s*(?:<([^>]+)>)?\s*",
        raw,
    )
    if not match:
        raise LolaRasterError(f"PDS label field {key} is not a supported numeric value")
    value, actual_unit = match.groups()
    if unit is not None and actual_unit != unit:
        raise LolaRasterError(f"PDS label field {key} must use {unit}")
    return float(value)


def _positive_int(metadata: dict[str, str], key: str) -> int:
    raw = metadata.get(key)
    if raw is None or not raw.isdigit() or int(raw) <= 0:
        raise LolaRasterError(f"Required PDS label field {key} must be a positive integer")
    return int(raw)


def validate_lola_gdr_label(metadata: dict[str, str]) -> tuple[int, int, int]:
    """Validate the selected PDS3 LOLA GDR's fixed-length signed-16-bit layout."""
    if metadata.get("PDS_VERSION_ID") != "PDS3":
        raise LolaRasterError("Only PDS3 LOLA GDR labels are supported")
    if metadata.get("DATA_SET_ID") != "LRO-L-LOLA-4-GDR-V1.0":
        raise LolaRasterError("Unexpected LOLA GDR data set identifier")
    if metadata.get("FILE_NAME") != "LDEM_85S_40M.IMG":
        raise LolaRasterError("Unexpected LOLA raster filename")
    if metadata.get("^IMAGE") != '"LDEM_85S_40M.IMG"' and metadata.get("^IMAGE") != "LDEM_85S_40M.IMG":
        raise LolaRasterError("PDS image pointer does not identify the selected raster")
    if metadata.get("RECORD_TYPE") != "FIXED_LENGTH":
        raise LolaRasterError("LOLA raster must declare FIXED_LENGTH records")
    if metadata.get("NAME") != "HEIGHT":
        raise LolaRasterError("LOLA image object is not identified as HEIGHT")
    if metadata.get("SAMPLE_TYPE") != "LSB_INTEGER" or metadata.get("SAMPLE_BITS") != "16":
        raise LolaRasterError("Only 16-bit little-endian signed LOLA samples are supported")
    if metadata.get("UNIT") != "METER":
        raise LolaRasterError("LOLA height samples must declare METER units")

    lines = _positive_int(metadata, "LINES")
    samples = _positive_int(metadata, "LINE_SAMPLES")
    records = _positive_int(metadata, "FILE_RECORDS")
    record_bytes = _positive_int(metadata, "RECORD_BYTES")
    if lines != samples or records != lines:
        raise LolaRasterError("LOLA polar image must be square with one record per line")
    if record_bytes != samples * 2:
        raise LolaRasterError("Record byte count does not match 16-bit image samples")
    return lines, samples, record_bytes


def iter_lola_gdr_rows(data: bytes | bytearray | memoryview, metadata: dict[str, str]) -> Iterator[tuple[int, ...]]:
    """Iterate raw signed DN rows after strict length and PDS-label validation.

    Values remain digital numbers (DN). This function intentionally performs
    no height/radius conversion and allocates at most one decoded row at a time.
    """
    lines, samples, record_bytes = validate_lola_gdr_label(metadata)
    view = memoryview(data)
    if not view.contiguous:
        raise LolaRasterError("Raster buffer must be contiguous")
    try:
        byte_view = view.cast("B")
    except TypeError as exc:
        raise LolaRasterError("Raster buffer must be byte-addressable") from exc

    expected_bytes = lines * record_bytes
    if len(byte_view) != expected_bytes:
        raise LolaRasterError(
            f"Raster byte count mismatch: expected {expected_bytes}, received {len(byte_view)}"
        )

    def rows() -> Iterator[tuple[int, ...]]:
        for line_index in range(lines):
            start = line_index * record_bytes
            row_view = byte_view[start : start + record_bytes]
            row = tuple(value[0] for value in struct.iter_unpack("<h", row_view))
            if len(row) != samples:
                raise LolaRasterError("Decoded row length does not match LINE_SAMPLES")
            yield row

    return rows()


def lola_polar_pixel_to_latlon(
    metadata: dict[str, str], *, line_index: int, sample_index: int
) -> tuple[float, float]:
    """Return planetocentric (latitude, east longitude) from 0-based pixel indices.

    Implements the LOLA team's DSMAP_POLAR.CAT equations for the south pole.
    The projection catalog defines pixel registration, a spherical 1737.4 km
    reference radius, and the positive-Y direction used below.
    """
    lines, samples, _ = validate_lola_gdr_label(metadata)
    if not 0 <= line_index < lines or not 0 <= sample_index < samples:
        raise LolaRasterError("Pixel index is outside the image bounds")

    if metadata.get("MAP_PROJECTION_TYPE") != "POLAR STEREOGRAPHIC":
        raise LolaRasterError("Unsupported LOLA map projection")
    if metadata.get("KEYWORD_LATITUDE_TYPE") != "PLANETOCENTRIC":
        raise LolaRasterError("LOLA projection requires planetocentric latitude")
    if metadata.get("POSITIVE_LONGITUDE_DIRECTION") != '"EAST"' and metadata.get("POSITIVE_LONGITUDE_DIRECTION") != "EAST":
        raise LolaRasterError("LOLA projection requires east-positive longitude")
    if metadata.get("COORDINATE_SYSTEM_NAME") != "MEAN EARTH/POLAR AXIS OF DE421":
        raise LolaRasterError("Unexpected LOLA coordinate reference frame")
    if not math.isclose(_number(metadata, "CENTER_LATITUDE", unit="deg"), -90.0):
        raise LolaRasterError("Selected product is not centered on the lunar south pole")
    if not math.isclose(_number(metadata, "CENTER_LONGITUDE", unit="deg"), 0.0):
        raise LolaRasterError("Unexpected LOLA polar projection center longitude")
    if not math.isclose(_number(metadata, "MAP_PROJECTION_ROTATION"), 0.0):
        raise LolaRasterError("Rotated LOLA polar projections are not supported")

    radius_m = _number(metadata, "A_AXIS_RADIUS", unit="km") * 1000.0
    b_radius_m = _number(metadata, "B_AXIS_RADIUS", unit="km") * 1000.0
    c_radius_m = _number(metadata, "C_AXIS_RADIUS", unit="km") * 1000.0
    if not all(math.isclose(value, LOLA_MEAN_EARTH_REFERENCE_RADIUS_M) for value in (radius_m, b_radius_m, c_radius_m)):
        raise LolaRasterError("LOLA projection axes do not match the catalog's 1737.4 km sphere")

    map_scale = _number(metadata, "MAP_SCALE", unit="m/pix")
    line_offset = _number(metadata, "LINE_PROJECTION_OFFSET", unit="pix")
    sample_offset = _number(metadata, "SAMPLE_PROJECTION_OFFSET", unit="pix")
    expected_offset = lines / 2.0 - 0.5
    if not math.isclose(line_offset, expected_offset) or not math.isclose(sample_offset, expected_offset):
        raise LolaRasterError("Projection offsets do not match the catalog's pixel-center convention")

    # DSMAP_POLAR.CAT: X=(I-N/2-0.5)*scale;
    # Y=(J-N/2-0.5)*scale*NS, with NS=-1 in the southern hemisphere.
    x = (sample_index - sample_offset) * map_scale
    y = (line_index - line_offset) * map_scale * -1.0
    radial_distance = math.hypot(x, y)
    latitude = -90.0 + math.degrees(
        2.0 * math.atan(0.5 * radial_distance / LOLA_MEAN_EARTH_REFERENCE_RADIUS_M)
    )
    longitude = math.degrees(math.atan2(x, y)) % 360.0
    return latitude, longitude
