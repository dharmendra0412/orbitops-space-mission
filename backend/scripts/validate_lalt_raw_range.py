from __future__ import annotations

import argparse
import hashlib
import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx

from app.services.pds3_label import PdsLabelError, parse_pds3_label


LALT_RANGE_BASE_URL = (
    "https://data.darts.isas.jaxa.jp/pub/pds3/"
    "sln-l-lalt-3-range-v1.0/0000/data/"
)
LALT_RANGE_DAY = "20080105"
LALT_RANGE_FILE = f"LALT_RD_{LALT_RANGE_DAY}"
LALT_RANGE_LABEL_URL = LALT_RANGE_BASE_URL + LALT_RANGE_FILE + ".lbl"
LALT_RANGE_TABLE_URL = LALT_RANGE_BASE_URL + LALT_RANGE_FILE + ".TAB"
LALT_RANGE_MAX_LABEL_BYTES = 64_000
LALT_RANGE_MAX_TABLE_BYTES = 16 * 1024 * 1024
LALT_RANGE_COLUMNS = (
    "TI",
    "ALTITUDE",
    "DETECT_PEAK",
    "OUTPUT_POWER",
    "HV_MON_APD",
    "TEMP_MON_4",
    "TEMP_MON_6",
    "TEMP_MON_8",
    "ALTERNATIVE_PPS",
    "START_MODE",
    "THRESHOLD_LEVEL",
)
LALT_RANGE_FORMAT_URL = (
    "https://darts.isas.jaxa.jp/app/pdap/selene/help/en/LALT_Format_en_V01.pdf"
)
LALT_RANGE_DATASET_URL = (
    "https://darts.isas.jaxa.jp/en/datasets/darts:sln-l-lalt-3-range-v1.0/"
)
LALT_SCLK_URL = (
    "https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-spice-6-v1.0/"
    "slnsp_1000/data/sclk/SEL_M_V01.TSC"
)
LALT_SPK_INFO_URL = (
    "https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-spice-6-v1.0/"
    "slnsp_1000/data/spk/spkinfo.txt"
)


class LaltRangeValidationError(RuntimeError):
    """Raised when a fixed JAXA LALT calibrated range product fails validation."""


def _download_fixed(url: str, *, maximum_bytes: int, transport: httpx.BaseTransport | None = None) -> bytes:
    try:
        with httpx.Client(
            timeout=30.0,
            transport=transport,
            follow_redirects=False,
        ) as client:
            with client.stream(
                "GET",
                url,
                headers={"Accept": "text/plain", "Accept-Encoding": "identity"},
            ) as response:
                if response.is_redirect:
                    raise LaltRangeValidationError("JAXA LALT range source redirected; refusing an unverified destination")
                if response.url.scheme != "https" or response.url.host != "data.darts.isas.jaxa.jp":
                    raise LaltRangeValidationError("JAXA LALT range response came from an unexpected source host")
                response.raise_for_status()
                body = bytearray()
                for chunk in response.iter_bytes():
                    body.extend(chunk)
                    if len(body) > maximum_bytes:
                        raise LaltRangeValidationError("JAXA LALT range source exceeded the configured download limit")
                return bytes(body)
    except LaltRangeValidationError:
        raise
    except httpx.TimeoutException as exc:
        raise LaltRangeValidationError("JAXA LALT range archive request timed out") from exc
    except httpx.HTTPError as exc:
        raise LaltRangeValidationError("Could not retrieve the fixed JAXA LALT range source") from exc


def validate_lalt_rd_day(label_bytes: bytes, table_bytes: bytes) -> dict[str, Any]:
    if not label_bytes or len(label_bytes) > LALT_RANGE_MAX_LABEL_BYTES:
        raise LaltRangeValidationError("LALT range label is empty or exceeds its size limit")
    if not table_bytes or len(table_bytes) > LALT_RANGE_MAX_TABLE_BYTES:
        raise LaltRangeValidationError("LALT range table is empty or exceeds its size limit")
    try:
        label_text = label_bytes.decode("ascii")
        table_text = table_bytes.decode("ascii")
    except UnicodeDecodeError as exc:
        raise LaltRangeValidationError("LALT range label/table must be ASCII text") from exc

    try:
        label = parse_pds3_label(label_text)
    except PdsLabelError as exc:
        raise LaltRangeValidationError(f"LALT range label failed PDS3 validation: {exc}") from exc

    expected_label = {
        "FILE_NAME": LALT_RANGE_FILE + ".TAB",
        "DATA_SET_ID": "SLN-L-LALT-3-RANGE-V1.0",
        "PRODUCT_ID": LALT_RANGE_FILE,
        "INSTRUMENT_ID": "LALT",
        "TARGET_NAME": "MOON",
        "RECORD_TYPE": "FIXED_LENGTH",
        "RECORD_BYTES": "162",
        "FILE_RECORDS": "12003",
        "PRODUCT_NAME": "LALT_RD",
        "ROWS": "12002",
        "COLUMNS": "11",
        "ROW_BYTES": "162",
        "INTERCHANGE_FORMAT": "ASCII",
    }
    for key, expected in expected_label.items():
        if label.get(key) != expected:
            raise LaltRangeValidationError(
                f"LALT range label field {key} expected {expected!r}, got {label.get(key)!r}"
            )

    physical_records = table_bytes.splitlines(keepends=True)
    if len(physical_records) != 12_003 or any(len(record) != 162 for record in physical_records):
        raise LaltRangeValidationError("LALT range table does not contain 12003 exact 162-byte physical records")
    lines = table_text.splitlines()
    if len(lines) != 12_003:
        raise LaltRangeValidationError(
            f"LALT range table expected 12003 physical records, received {len(lines)}"
        )
    if len(table_bytes) != 12_003 * 162:
        raise LaltRangeValidationError(
            f"LALT range table expected {12_003 * 162} bytes from its PDS record layout, received {len(table_bytes)}"
        )
    header = [part.strip() for part in lines[0].lstrip("#").split(",")]
    if tuple(header) != LALT_RANGE_COLUMNS:
        raise LaltRangeValidationError("LALT range table column header does not match the published 11-column layout")

    row_count = 0
    first_ti: int | None = None
    last_ti: int | None = None
    previous_ti: int | None = None
    ti_gaps = 0
    altitude_min = math.inf
    altitude_max = -math.inf
    for line_number, line in enumerate(lines[1:], start=2):
        values = line.split()
        if len(values) != len(LALT_RANGE_COLUMNS):
            raise LaltRangeValidationError(
                f"LALT range record {line_number} expected 11 whitespace-delimited fields, received {len(values)}"
            )
        try:
            ti = int(values[0])
            numeric = [float(value) for value in values[1:8]]
        except ValueError as exc:
            raise LaltRangeValidationError(
                f"LALT range record {line_number} contains an invalid numeric field"
            ) from exc
        if not all(math.isfinite(value) for value in numeric):
            raise LaltRangeValidationError(f"LALT range record {line_number} contains a non-finite numeric field")
        if previous_ti is not None:
            if ti <= previous_ti:
                raise LaltRangeValidationError(
                    f"LALT range TI values are not strictly increasing at record {line_number}"
                )
            ti_gaps += max(0, ti - previous_ti - 1)
        if first_ti is None:
            first_ti = ti
        last_ti = ti
        previous_ti = ti
        altitude_min = min(altitude_min, numeric[0])
        altitude_max = max(altitude_max, numeric[0])
        row_count += 1

    if row_count != 12_002 or first_ti is None or last_ti is None:
        raise LaltRangeValidationError("LALT range table row count or TI coverage is incomplete")

    return {
        "dataset_id": label["DATA_SET_ID"],
        "product_id": label["PRODUCT_ID"],
        "product_file": label["FILE_NAME"],
        "observation_day_utc": LALT_RANGE_DAY,
        "label_bytes": len(label_bytes),
        "table_bytes": len(table_bytes),
        "record_bytes": 162,
        "file_records_including_header": 12_003,
        "data_rows": row_count,
        "column_names": list(LALT_RANGE_COLUMNS),
        "range_label_column_name": "LALT_ALTITUDE",
        "ti_first": first_ti,
        "ti_last": last_ti,
        "ti_missing_integer_ticks_between_rows": ti_gaps,
        "altitude_min_m": altitude_min,
        "altitude_max_m": altitude_max,
        "label_start_time": label.get("START_TIME"),
        "label_stop_time": label.get("STOP_TIME"),
        "time_tag_interpretation": (
            "TI is the SELENE main-orbiter internal clock count. It has not been converted to UTC/ET; "
            "the matching SCLK correlation kernel and validated kernel coverage are required."
        ),
        "geolocation_status": (
            "The LALT_RD table contains range and instrument telemetry, not latitude/longitude. "
            "Geolocation requires a separately validated spacecraft SPK, CK attitude, FK/IK, SCLK, "
            "LSK, and lunar PCK/frame chain."
        ),
        "documented_range_precision_m": 5.0,
        "range_precision_source": LALT_RANGE_DATASET_URL,
        "format_source": LALT_RANGE_FORMAT_URL,
    }


def retrieve_and_validate(
    output_dir: Path,
    *,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    label_bytes = _download_fixed(
        LALT_RANGE_LABEL_URL,
        maximum_bytes=LALT_RANGE_MAX_LABEL_BYTES,
        transport=transport,
    )
    table_bytes = _download_fixed(
        LALT_RANGE_TABLE_URL,
        maximum_bytes=LALT_RANGE_MAX_TABLE_BYTES,
        transport=transport,
    )
    report = validate_lalt_rd_day(label_bytes, table_bytes)
    output_dir.mkdir(parents=True, exist_ok=True)
    label_path = output_dir / (LALT_RANGE_FILE + ".lbl")
    table_path = output_dir / (LALT_RANGE_FILE + ".TAB")
    label_path.write_bytes(label_bytes)
    table_path.write_bytes(table_bytes)
    report.update({
        "source": "JAXA / DARTS SELENE Data Archive",
        "label_source_url": LALT_RANGE_LABEL_URL,
        "table_source_url": LALT_RANGE_TABLE_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "label_sha256": hashlib.sha256(label_bytes).hexdigest(),
        "table_sha256": hashlib.sha256(table_bytes).hexdigest(),
        "sclk_kernel_reference": LALT_SCLK_URL,
        "spk_information_reference": LALT_SPK_INFO_URL,
        "validation_scope": (
            "The fixed daily LALT_RD PDS3 label and complete fixed-length table were downloaded and "
            "checked against the label's byte/record counts, published 11-column layout, ASCII numeric "
            "fields, finite values, and strictly increasing onboard TI tags. Local SHA-256 values are "
            "provenance fingerprints; no upstream checksum is claimed. No time conversion or surface "
            "geolocation has been performed."
        ),
    })
    report_path = output_dir / (LALT_RANGE_FILE + ".validation.json")
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve and validate one fixed JAXA SELENE LALT calibrated range day.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("data/raw/kaguya_lalt_range"),
    )
    args = parser.parse_args()
    report = retrieve_and_validate(args.output_dir)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
