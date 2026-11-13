from __future__ import annotations

import argparse
import asyncio
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import httpx

from app.services.lola_gdr import LolaRasterError, validate_lola_gdr_label
from app.services.pds3_label import PdsLabelError, parse_pds3_label
from scripts.fetch_lola_gdr_sample import FALLBACK_SOURCE_URL, SOURCE_URL


LABEL_URLS = {
    SOURCE_URL: SOURCE_URL.rsplit(".", 1)[0] + ".lbl",
    FALLBACK_SOURCE_URL: FALLBACK_SOURCE_URL.rsplit(".", 1)[0] + ".LBL",
}
MAX_LABEL_BYTES = 1_000_000
DEFAULT_MANIFEST = Path("data/raw/lola/ldem_85s_40m.img.manifest.json")


async def fetch_lola_gdr_label(
    manifest_path: Path,
    *,
    client: httpx.AsyncClient | None = None,
) -> dict[str, Any]:
    """Fetch the exact IMG's companion label from the same archive host."""
    manifest_path = Path(manifest_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    image_source = manifest.get("source_url")
    label_url = LABEL_URLS.get(image_source)
    if label_url is None:
        raise ValueError("Manifest source_url is not one of the fixed LOLA IMG archives")

    image_path = manifest_path.name.removesuffix(".manifest.json")
    label_path = manifest_path.with_name(Path(image_path).stem + ".lbl")
    temporary_path = label_path.with_name(label_path.name + ".part")
    manifest_temporary_path = manifest_path.with_name(manifest_path.name + ".part")
    if label_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing LOLA label: {label_path}")

    owns_client = client is None
    if client is None:
        client = httpx.AsyncClient(timeout=httpx.Timeout(30.0, connect=15.0), follow_redirects=False)

    label_created = False
    try:
        response = await client.get(
            label_url,
            headers={"Accept": "text/plain", "Accept-Encoding": "identity"},
        )
        if response.is_redirect:
            raise RuntimeError("LOLA label source redirected; refusing an unverified destination")
        response.raise_for_status()
        if len(response.content) > MAX_LABEL_BYTES:
            raise RuntimeError("LOLA PDS3 label exceeds the configured 1 MB limit")
        try:
            label_text = response.content.decode("ascii")
        except UnicodeDecodeError as exc:
            raise RuntimeError("LOLA PDS3 label is not ASCII text") from exc

        try:
            metadata = parse_pds3_label(label_text)
            lines, samples, record_bytes = validate_lola_gdr_label(metadata)
        except (PdsLabelError, LolaRasterError) as exc:
            raise RuntimeError(f"Downloaded LOLA label failed product/layout validation: {exc}") from exc

        label_expected_bytes = lines * record_bytes
        if label_expected_bytes != manifest.get("expected_bytes_from_archive_listing"):
            raise RuntimeError(
                "Downloaded LOLA label dimensions disagree with the raster's archived expected byte count"
            )
        if manifest.get("actual_bytes_downloaded") != label_expected_bytes:
            raise RuntimeError("Downloaded LOLA raster byte count disagrees with its companion label")

        digest = hashlib.sha256(response.content).hexdigest()
        temporary_path.write_bytes(response.content)
        updated_manifest = {
            **manifest,
            "label_source_url": label_url,
            "label_file_name": label_path.name,
            "label_bytes": len(response.content),
            "label_sha256_local": digest,
            "label_verification_status": "ascii_pds3_parsed_product_and_raster_layout_match",
            "label_data_set_id": metadata.get("DATA_SET_ID"),
            "label_product_version_id": metadata.get("PRODUCT_VERSION_ID"),
            "label_lines": lines,
            "label_samples_per_line": samples,
            "label_record_bytes": record_bytes,
            "label_derived_minimum_dn": int(metadata["DERIVED_MINIMUM"]),
            "label_derived_maximum_dn": int(metadata["DERIVED_MAXIMUM"]),
        }
        manifest_temporary_path.write_text(
            json.dumps(updated_manifest, indent=2) + "\n",
            encoding="utf-8",
        )
        os.replace(temporary_path, label_path)
        label_created = True
        os.replace(manifest_temporary_path, manifest_path)
        return updated_manifest
    except Exception:
        temporary_path.unlink(missing_ok=True)
        manifest_temporary_path.unlink(missing_ok=True)
        if label_created:
            label_path.unlink(missing_ok=True)
        raise
    finally:
        if owns_client:
            await client.aclose()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch and validate the companion PDS3 label for the downloaded LOLA IMG."
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST, help="IMG provenance manifest")
    args = parser.parse_args()
    result = asyncio.run(fetch_lola_gdr_label(args.manifest))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
