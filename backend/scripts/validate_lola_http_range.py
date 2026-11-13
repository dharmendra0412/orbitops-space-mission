from __future__ import annotations

import argparse
import asyncio
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.pds_client import (
    PDS_LOLA_GDR_IMAGE_BYTES,
    PDS_LOLA_GDR_RECORD_BYTES,
    PDS_LOLA_GDR_SAMPLE_IMG_URL,
    PdsApiError,
    PdsClient,
)


DEFAULT_IMAGE = Path("data/raw/lola/ldem_85s_40m.img")
DEFAULT_REPORT = Path("data/raw/lola/ldem_85s_40m.range-validation.json")
SAMPLE_POINTS = (
    (0, 0),
    (3791, 3791),
    (3791, 3792),
    (3792, 3791),
    (3792, 3792),
    (0, 7583),
    (7583, 0),
    (7583, 7583),
)


async def validate_source_range(
    image_path: Path,
    *,
    client: PdsClient | None = None,
) -> dict[str, Any]:
    """Exercise the API's exact range client against the archive and local IMG."""
    image_path = Path(image_path)
    if image_path.stat().st_size != PDS_LOLA_GDR_IMAGE_BYTES:
        raise RuntimeError("Local LOLA IMG does not have the expected validated product size")

    if client is None:
        client = PdsClient(timeout_seconds=30.0)
    samples: list[dict[str, Any]] = []
    with image_path.open("rb") as image:
        for line_index, sample_index in SAMPLE_POINTS:
            byte_start = line_index * PDS_LOLA_GDR_RECORD_BYTES + sample_index * 2
            byte_end = byte_start + 1
            image.seek(byte_start)
            local_bytes = image.read(2)
            if len(local_bytes) != 2:
                raise RuntimeError("Local validated IMG ended before a requested sample offset")

            source_url, dn, byte_range = await client.fetch_lola_gdr_sample_dn(
                line_index=line_index,
                sample_index=sample_index,
            )
            if source_url != PDS_LOLA_GDR_SAMPLE_IMG_URL:
                raise RuntimeError("LOLA API client returned an unexpected source URL")
            if byte_range != (byte_start, byte_end):
                raise RuntimeError("LOLA API client returned an unexpected byte range")
            remote_bytes = struct.pack("<h", dn)
            if remote_bytes != local_bytes:
                raise RuntimeError(
                    f"Remote LOLA sample does not match the validated IMG at "
                    f"line={line_index}, sample={sample_index}"
                )
            samples.append({
                "line_index": line_index,
                "sample_index": sample_index,
                "byte_range_inclusive": {"start": byte_start, "end": byte_end},
                "raw_dn": dn,
                "matches_validated_local_img": True,
            })

    return {
        "source_url": PDS_LOLA_GDR_SAMPLE_IMG_URL,
        "samples_checked": len(samples),
        "samples": samples,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Exercises the same fixed-source PDSClient range method used by the live API. "
            "Eight two-byte reads at center-adjacent, quadrant, and image-edge locations "
            "matched the fully downloaded and validated local IMG. This does not establish "
            "geodetic accuracy."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify the live API's bounded LOLA byte-range client against the validated IMG."
    )
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        report = asyncio.run(validate_source_range(args.image))
    except (OSError, PdsApiError, RuntimeError) as exc:
        parser.exit(1, f"LOLA HTTP Range validation failed: {exc}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
