from __future__ import annotations

import httpx
import pytest

from scripts.validate_lalt_raw_range import (
    LALT_RANGE_COLUMNS,
    LALT_RANGE_LABEL_URL,
    LALT_RANGE_MAX_LABEL_BYTES,
    LaltRangeValidationError,
    _download_fixed,
    _validate_response_origin,
    validate_lalt_rd_day,
)


def make_label(*, rows: int = 2, records: int = 3) -> bytes:
    return (
        'PDS_VERSION_ID = "PDS3"\n'
        'FILE_NAME = "LALT_RD_20080105.TAB"\n'
        'DATA_SET_ID = "SLN-L-LALT-3-RANGE-V1.0"\n'
        'PRODUCT_ID = "LALT_RD_20080105"\n'
        'PRODUCT_NAME = "LALT_RD"\n'
        'INSTRUMENT_ID = "LALT"\n'
        'TARGET_NAME = "MOON"\n'
        'RECORD_TYPE = FIXED_LENGTH\n'
        'RECORD_BYTES = 162\n'
        f'FILE_RECORDS = {records}\n'
        f'ROWS = {rows}\n'
        'COLUMNS = 11\n'
        'ROW_BYTES = 162\n'
        'INTERCHANGE_FORMAT = ASCII\n'
        'END\n'
    ).encode("ascii")


def make_record(value: str) -> bytes:
    raw = value.encode("ascii")
    assert len(raw) <= 160
    return raw + (b" " * (160 - len(raw))) + b"\r\n"


def make_table(*rows: str) -> bytes:
    header = "#" + ", ".join(LALT_RANGE_COLUMNS)
    return b"".join(make_record(line) for line in (header, *rows))


def test_validate_lalt_rd_day_checks_pds_layout_rows_and_time_tags():
    table = make_table(
        "0883526397 109414.2 21.0 67.3 206.4 -16.8 -8.7 -10.2 NON NML LO",
        "0883526399 109568.0 21.0 68.5 208.9 -16.8 -8.7 -10.2 NON NML LO",
    )
    report = validate_lalt_rd_day(make_label(), table, require_full_archive_day=False)

    assert report["dataset_id"] == "SLN-L-LALT-3-RANGE-V1.0"
    assert report["product_id"] == "LALT_RD_20080105"
    assert report["data_rows"] == 2
    assert report["ti_first"] == 883526397
    assert report["ti_last"] == 883526399
    assert report["ti_missing_integer_ticks_between_rows"] == 1
    assert report["altitude_min_m"] == 109414.2
    assert report["altitude_max_m"] == 109568.0
    assert "not been converted to UTC/ET" in report["time_tag_interpretation"]
    assert "not latitude/longitude" in report["geolocation_status"]


@pytest.mark.parametrize(
    ("label", "table", "message"),
    [
        (make_label(rows=3, records=4), make_table(
            "0883526397 109414.2 21.0 67.3 206.4 -16.8 -8.7 -10.2 NON NML LO",
            "0883526399 109568.0 21.0 68.5 208.9 -16.8 -8.7 -10.2 NON NML LO",
        ), "physical records"),
        (make_label(), make_table(
            "0883526397 109414.2 21.0 67.3 206.4 -16.8 -8.7 -10.2 NON NML LO",
            "0883526397 109568.0 21.0 68.5 208.9 -16.8 -8.7 -10.2 NON NML LO",
        ), "strictly increasing"),
        (make_label(), make_table(
            "0883526397 nan 21.0 67.3 206.4 -16.8 -8.7 -10.2 NON NML LO",
            "0883526399 109568.0 21.0 68.5 208.9 -16.8 -8.7 -10.2 NON NML LO",
        ), "non-finite"),
    ],
)
def test_validate_lalt_rd_day_rejects_invalid_source_structure(label, table, message):
    with pytest.raises(LaltRangeValidationError, match=message):
        validate_lalt_rd_day(label, table, require_full_archive_day=False)


def test_download_fixed_rejects_redirects_and_wrong_hosts():
    redirect = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"Location": "https://example.com/file"})
    )
    with pytest.raises(LaltRangeValidationError, match="redirected"):
        _download_fixed(LALT_RANGE_LABEL_URL, maximum_bytes=LALT_RANGE_MAX_LABEL_BYTES, transport=redirect)

    wrong_host_response = httpx.Response(
        200,
        content=b"not source data",
        request=httpx.Request("GET", "https://example.com/file"),
    )
    with pytest.raises(LaltRangeValidationError, match="unexpected source host"):
        _validate_response_origin(wrong_host_response)
