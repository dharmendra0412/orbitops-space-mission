from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.lalt_client import LaltClient
from app.services.lalt_pds3 import (
    LALT_GT_SP_IMAGE_BYTES,
    LALT_GT_SP_IMAGE_URL,
    LALT_GT_SP_LABEL_URL,
    LALT_GT_SP_SAMPLE_BYTES,
    LALT_GT_SP_SAMPLES,
    parse_and_validate_lalt_gt_sp_label,
    validate_lalt_gt_sp_image_file,
)


SAMPLE_POINTS = ((0, 0), (703, 5759), (1407, 11519), (1407, 0))


async def validate_lalt_source_ranges(
    *,
    image_path: Path,
    label_path: Path,
    client: LaltClient | None = None,
) -> dict[str, Any]:
    """Compare live API-client byte ranges with the complete downloaded DARTS IMG."""
    active_client = client or LaltClient()
    image_validation = validate_lalt_gt_sp_image_file(image_path)
    local_label = label_path.read_text(encoding="ascii")
    source_label_url, source_label = await active_client.fetch_gt_sp_label()
    if source_label_url != LALT_GT_SP_LABEL_URL:
        raise RuntimeError("LALT client returned an unexpected label source URL")
    if source_label != local_label:
        raise RuntimeError("Live LALT label differs from the detached label used for image validation")
    metadata = parse_and_validate_lalt_gt_sp_label(source_label)

    checked: list[dict[str, Any]] = []
    with image_path.open("rb") as image:
        for line_index, sample_index in SAMPLE_POINTS:
            source_url, raw_bytes, byte_range = await active_client.fetch_gt_sp_sample(
                line_index=line_index,
                sample_index=sample_index,
            )
            expected_start = (
                line_index * LALT_GT_SP_SAMPLES + sample_index
            ) * LALT_GT_SP_SAMPLE_BYTES
            expected_end = expected_start + LALT_GT_SP_SAMPLE_BYTES - 1
            if source_url != LALT_GT_SP_IMAGE_URL:
                raise RuntimeError("LALT client returned an unexpected image source URL")
            if byte_range != (expected_start, expected_end):
                raise RuntimeError("LALT client returned an unexpected image byte range")
            image.seek(expected_start)
            local_bytes = image.read(LALT_GT_SP_SAMPLE_BYTES)
            if len(local_bytes) != LALT_GT_SP_SAMPLE_BYTES:
                raise RuntimeError("Validated local LALT IMG ended before the selected sample")
            if raw_bytes != local_bytes:
                raise RuntimeError(
                    f"Live LALT range bytes differ from the validated local IMG at line={line_index}, sample={sample_index}"
                )
            checked.append({
                "line_index": line_index,
                "sample_index": sample_index,
                "byte_range_inclusive": {"start": expected_start, "end": expected_end},
                "raw_bytes_hex": raw_bytes.hex(),
                "matches_validated_local_img": True,
            })

    return {
        "source": "JAXA DARTS SELENE LALT PDS3",
        "label_source_url": source_label_url,
        "image_source_url": LALT_GT_SP_IMAGE_URL,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "label_matches_downloaded_validation_label": True,
        "image_validation": image_validation,
        "dataset_id": metadata["dataset_id"],
        "sample_bytes": LALT_GT_SP_SAMPLE_BYTES,
        "samples_checked": len(checked),
        "samples": checked,
        "scope": (
            "Four exact four-byte HTTP 206 Range responses using the same fixed-source LaltClient "
            "method used by the live API matched the corresponding bytes in the fully downloaded "
            "and byte-count-validated LALT IMG. This verifies bounded retrieval consistency, not "
            "geodetic accuracy or independent ground truth."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Verify live bounded Kaguya LALT sample ranges against the full source IMG.")
    parser.add_argument("--image", type=Path, required=True)
    parser.add_argument("--label", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    report = asyncio.run(validate_lalt_source_ranges(image_path=args.image, label_path=args.label))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
