from __future__ import annotations

import re


# Keep the parser deliberately narrow: these are scalar fields needed to
# validate selected LOLA and Kaguya LALT products. Complex PDS3 objects and
# multiline descriptions remain in the original source labels.
_LABEL_FIELDS = {
    "PDS_VERSION_ID", "PRODUCT_VERSION_ID", "DATA_SET_ID",
    "INSTRUMENT_HOST_NAME", "INSTRUMENT_NAME", "INSTRUMENT_ID", "TARGET_NAME",
    "START_TIME", "STOP_TIME", "PRODUCT_CREATION_TIME", "FILE_NAME",
    "FILE_RECORDS", "RECORD_BYTES", "RECORD_TYPE", "^IMAGE", "LINES", "LINE_SAMPLES", "NAME", "DERIVED_MINIMUM", "DERIVED_MAXIMUM",
    "SAMPLE_TYPE", "SAMPLE_BITS", "UNIT", "SCALING_FACTOR", "OFFSET",
    "MAP_PROJECTION_TYPE", "KEYWORD_LATITUDE_TYPE", "MAP_RESOLUTION", "A_AXIS_RADIUS", "B_AXIS_RADIUS", "C_AXIS_RADIUS",
    "POSITIVE_LONGITUDE_DIRECTION", "CENTER_LATITUDE", "CENTER_LONGITUDE",
    "MAP_SCALE", "MAP_PROJECTION_ROTATION", "LINE_PROJECTION_OFFSET", "SAMPLE_PROJECTION_OFFSET", "LINE_FIRST_PIXEL", "SAMPLE_FIRST_PIXEL", "MAXIMUM_LATITUDE", "MINIMUM_LATITUDE",
    "COORDINATE_SYSTEM_TYPE", "COORDINATE_SYSTEM_NAME",
    "DATA_SET_ID", "PRODUCT_ID", "PRODUCT_SET_ID", "BANDS", "DUMMY_DATA",
    "INVALID_CONSTANT", "STRETCHED_FLAG", "MAP_RESOLUTION_LATITUDE",
    "MAP_RESOLUTION_LONGITUDE", "WESTERNMOST_LONGITUDE", "EASTERNMOST_LONGITUDE",
    "LINE_LAST_PIXEL", "SAMPLE_LAST_PIXEL", "BAND_STORAGE_TYPE", "COMPRESSION_TYPE", "SAMPLE_BIT_MASK",
    "DATA_TYPE", "PROJECTION_LATITUDE_TYPE", "MAP_PROJECTION_TYPE",
}
_ASSIGNMENT = re.compile(r"^\s*(\^?[A-Z][A-Z0-9_]*)\s*=\s*(.*?)\s*$")


class PdsLabelError(ValueError):
    """Raised when a source label is not a supported PDS3 text label."""


def parse_pds3_label(label_text: str, *, max_characters: int = 1_000_000) -> dict[str, str]:
    """Extract allowlisted scalar fields from a PDS3 label without unit conversion."""
    if not isinstance(label_text, str) or not label_text.strip():
        raise PdsLabelError("PDS3 label is empty")
    if len(label_text) > max_characters:
        raise PdsLabelError("PDS3 label exceeds the configured size limit")

    values: dict[str, str] = {}
    for line in label_text.splitlines():
        match = _ASSIGNMENT.match(line)
        if not match:
            continue
        key, raw_value = match.groups()
        if key not in _LABEL_FIELDS:
            continue
        value = raw_value.strip()
        if not value:
            continue
        if value.startswith(chr(34)) and value.endswith(chr(34)) and len(value) >= 2:
            value = value[1:-1]
        elif value.startswith(chr(39)) and value.endswith(chr(39)) and len(value) >= 2:
            value = value[1:-1]
        # A duplicate key may belong to another nested PDS3 object. Keep the
        # first scalar rather than silently overwriting it without object scope.
        if key in values:
            continue
        values[key] = value

    if values.get("PDS_VERSION_ID") != "PDS3":
        raise PdsLabelError("Label does not declare PDS_VERSION_ID = PDS3")
    if not values.get("FILE_NAME"):
        raise PdsLabelError("PDS3 label does not identify its data FILE_NAME")
    return values
