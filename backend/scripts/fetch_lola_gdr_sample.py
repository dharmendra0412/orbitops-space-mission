from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


SOURCE_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img"
)
FALLBACK_SOURCE_URL = (
    "https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/IMG/LDEM_85S_40M.IMG"
)
SOURCE_URLS = (SOURCE_URL, FALLBACK_SOURCE_URL)
EXPECTED_IMG_BYTES = 115_034_112
DEFAULT_OUTPUT = Path("data/raw/lola/ldem_85s_40m.img")


async def download_lola_gdr_img(
    destination: Path,
    *,
    client: httpx.AsyncClient | None = None,
    expected_bytes: int = EXPECTED_IMG_BYTES,
) -> dict[str, Any]:
    """Download the fixed LOLA IMG from PDS, with the LOLA Data Node as fallback.

    No URL can be supplied by the caller. The SHA-256 is a locally computed
    provenance fingerprint; this script does not claim an upstream checksum
    because the inspected archive listings do not publish one for this file.
    """
    if expected_bytes <= 0:
        raise ValueError("expected_bytes must be positive")
    destination = Path(destination)
    manifest_path = destination.with_name(destination.name + ".manifest.json")
    temporary_path = destination.with_name(destination.name + ".part")
    manifest_temporary_path = manifest_path.with_name(manifest_path.name + ".part")

    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists() or manifest_path.exists():
        raise FileExistsError("Refusing to overwrite an existing raster or provenance manifest")
    temporary_path.unlink(missing_ok=True)
    manifest_temporary_path.unlink(missing_ok=True)

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(
            timeout=httpx.Timeout(120.0, connect=20.0),
            follow_redirects=False,
        )

    received = 0
    output_created = False
    downloaded_source: str | None = None
    last_transport_error: httpx.RequestError | None = None
    try:
        for source_url in SOURCE_URLS:
            digest = hashlib.sha256()
            received = 0
            try:
                async with client.stream(
                    "GET",
                    source_url,
                    headers={"Accept": "application/octet-stream", "Accept-Encoding": "identity"},
                ) as response:
                    if response.is_redirect:
                        raise RuntimeError("LOLA raster source redirected; refusing an unverified destination")
                    response.raise_for_status()
                    content_length = response.headers.get("content-length")
                    if content_length is not None:
                        try:
                            declared_length = int(content_length)
                        except ValueError as exc:
                            raise RuntimeError("LOLA response supplied an invalid Content-Length") from exc
                        if declared_length != expected_bytes:
                            raise RuntimeError(
                                f"LOLA Content-Length mismatch: expected {expected_bytes}, received {declared_length}"
                            )

                    with temporary_path.open("xb") as output:
                        async for chunk in response.aiter_bytes():
                            received += len(chunk)
                            if received > expected_bytes:
                                raise RuntimeError("LOLA raster exceeded the expected product byte count")
                            output.write(chunk)
                            digest.update(chunk)
                        output.flush()
                        os.fsync(output.fileno())
                downloaded_source = source_url
                break
            except httpx.RequestError as exc:
                temporary_path.unlink(missing_ok=True)
                last_transport_error = exc
                continue
            except httpx.HTTPStatusError as exc:
                temporary_path.unlink(missing_ok=True)
                if exc.response.status_code < 500:
                    raise
                last_transport_error = exc
                continue

        if downloaded_source is None:
            raise RuntimeError("All fixed LOLA raster sources failed before a complete response was received") from last_transport_error

        if received != expected_bytes:
            raise RuntimeError(
                f"PDS raster byte count mismatch: expected {expected_bytes}, received {received}"
            )

        manifest = {
            "source_url": downloaded_source,
            "source_attempts": list(SOURCE_URLS),
            "file_name": destination.name,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
            "expected_bytes_from_archive_listing": expected_bytes,
            "actual_bytes_downloaded": received,
            "sha256_local": digest.hexdigest(),
            "upstream_checksum": None,
            "verification_status": "byte_count_verified_local_sha256_computed_no_upstream_checksum_published",
            "note": (
                "The SHA-256 is a local provenance fingerprint. It is not an "
                "independent checksum verification because no upstream checksum "
                "for this IMG was present in the inspected archive directory listings. "
                "source_url records the endpoint that actually supplied the complete file."
            ),
        }
        manifest_temporary_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary_path, destination)
        output_created = True
        os.replace(manifest_temporary_path, manifest_path)
        return manifest
    except Exception:
        temporary_path.unlink(missing_ok=True)
        manifest_temporary_path.unlink(missing_ok=True)
        if output_created:
            destination.unlink(missing_ok=True)
        raise
    finally:
        if owns_client:
            await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Download the fixed NASA PDS LOLA south-polar GDR IMG.")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Destination path for the IMG file")
    args = parser.parse_args()
    manifest = asyncio.run(download_lola_gdr_img(args.output))
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
