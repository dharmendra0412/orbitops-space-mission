from __future__ import annotations

import argparse
import asyncio
import json
import struct
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


SOURCE_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img"
)
EXPECTED_IMAGE_BYTES = 115_034_112
DEFAULT_IMAGE = Path("data/raw/lola/ldem_85s_40m.img")
DEFAULT_REPORT = Path("data/raw/lola/ldem_85s_40m.range-validation.json")


def validate_range_response(
    *,
    status_code: int,
    headers: httpx.Headers,
    body: bytes,
    local_prefix: bytes,
    byte_start: int = 0,
) -> dict[str, Any]:
    """Require exact byte-range semantics and equality with the verified local IMG."""
    if not isinstance(byte_start, int) or isinstance(byte_start, bool) or byte_start < 0 or byte_start + 1 >= EXPECTED_IMAGE_BYTES:
        raise RuntimeError("LOLA byte offset is outside the fixed raster")
    if status_code != 206:
        raise RuntimeError(
            f"LOLA archive did not honor HTTP Range (expected 206, received {status_code})"
        )
    byte_end = byte_start + 1
    expected_content_range = f"bytes {byte_start}-{byte_end}/{EXPECTED_IMAGE_BYTES}"
    if headers.get("content-range") != expected_content_range:
        raise RuntimeError("LOLA archive returned an unexpected Content-Range")
    content_length = headers.get("content-length")
    if content_length is not None and content_length != "2":
        raise RuntimeError("LOLA archive returned an unexpected Content-Length")
    if len(body) != 2:
        raise RuntimeError("LOLA archive did not return exactly two bytes")
    if len(local_prefix) != 2:
        raise RuntimeError("Local validated IMG is shorter than two bytes")
    if body != local_prefix:
        raise RuntimeError("Remote range bytes do not match the previously validated local IMG")

    return {
        "source_url": SOURCE_URL,
        "http_status": status_code,
        "content_range": expected_content_range,
        "byte_range_inclusive": {"start": byte_start, "end": byte_end},
        "bytes_returned": len(body),
        "sample_dn": struct.unpack("<h", body)[0],
        "matches_validated_local_img": True,
    }


async def validate_source_range(
    image_path: Path,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    image_path = Path(image_path)
    if image_path.stat().st_size != EXPECTED_IMAGE_BYTES:
        raise RuntimeError("Local LOLA IMG does not have the expected validated product size")

    sample_points = (
        (0, 0),
        (3791, 3791),
        (3791, 3792),
        (3792, 3791),
        (3792, 3792),
        (0, 7583),
        (7583, 0),
        (7583, 7583),
    )
    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(30.0, connect=15.0),
            follow_redirects=False,
        )
    samples: list[dict[str, Any]] = []
    try:
        with image_path.open("rb") as image:
            for line_index, sample_index in sample_points:
                byte_start = line_index * 15_168 + sample_index * 2
                image.seek(byte_start)
                local_sample = image.read(2)
                if len(local_sample) != 2:
                    raise RuntimeError("Local validated IMG ended before a requested sample offset")
                async with client.stream(
                    "GET",
                    SOURCE_URL,
                    headers={
                        "Accept": "application/octet-stream",
                        "Accept-Encoding": "identity",
                        "Range": f"bytes={byte_start}-{byte_start + 1}",
                    },
                ) as response:
                    if response.is_redirect:
                        raise RuntimeError("LOLA range source redirected; refusing an unverified destination")
                    body = bytearray()
                    if response.status_code == 206:
                        async for chunk in response.aiter_bytes():
                            body.extend(chunk)
                            if len(body) > 2:
                                raise RuntimeError("LOLA archive returned more than two bytes for the range request")
                    sample = validate_range_response(
                        status_code=response.status_code,
                        headers=response.headers,
                        body=bytes(body),
                        local_prefix=local_sample,
                        byte_start=byte_start,
                    )
                sample.update({"line_index": line_index, "sample_index": sample_index})
                samples.append(sample)
    finally:
        if owns_client:
            await client.aclose()

    return {
        "source_url": SOURCE_URL,
        "samples_checked": len(samples),
        "samples": samples,
        "retrieved_at": datetime.now(timezone.utc).isoformat(),
        "scope": (
            "Confirms that the fixed PDS archive supports exact two-byte HTTP Range "
            "requests at center-adjacent, quadrant, and image-edge locations, and that "
            "each returned sample matches the fully downloaded and validated local IMG. "
            "It does not establish geodetic accuracy."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify that the fixed NASA PDS LOLA archive supports exact two-byte range reads."
    )
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    args = parser.parse_args()
    try:
        report = asyncio.run(validate_source_range(args.image))
    except (OSError, httpx.HTTPError, RuntimeError) as exc:
        parser.exit(1, f"LOLA HTTP Range validation failed: {exc}\n")
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
