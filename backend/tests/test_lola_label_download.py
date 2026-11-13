from __future__ import annotations

import hashlib
import json
import struct
from pathlib import Path

import httpx
import pytest

from scripts.fetch_lola_gdr_label import LABEL_URLS, fetch_lola_gdr_label
from scripts.fetch_lola_gdr_sample import SOURCE_URL


FIXTURE = Path(__file__).parent / "fixtures" / "lola_ldem_85s_40m.lbl"


def prepare_download(tmp_path: Path) -> tuple[Path, Path, bytes, bytes]:
    image_path = tmp_path / "sample.img"
    payload = struct.pack("<hhhh", -2, 0, 2, 32767)
    image_path.write_bytes(payload)

    label = FIXTURE.read_text(encoding="ascii")
    replacements = {
        "FILE_RECORDS              = 7584": "FILE_RECORDS              = 2",
        "RECORD_BYTES              = 15168": "RECORD_BYTES              = 4",
        "LINES                 = 7584": "LINES                 = 2",
        "LINE_SAMPLES          = 7584": "LINE_SAMPLES          = 2",
        "DERIVED_MINIMUM       = -11002": "DERIVED_MINIMUM       = -2",
        "DERIVED_MAXIMUM       = 14054": "DERIVED_MAXIMUM       = 32767",
    }
    for old, new in replacements.items():
        assert old in label
        label = label.replace(old, new)
    label_bytes = label.encode("ascii")

    manifest_path = tmp_path / "sample.img.manifest.json"
    manifest_path.write_text(json.dumps({
        "source_url": SOURCE_URL,
        "file_name": image_path.name,
        "expected_bytes_from_archive_listing": len(payload),
        "actual_bytes_downloaded": len(payload),
        "sha256_local": hashlib.sha256(payload).hexdigest(),
        "upstream_checksum": None,
    }), encoding="utf-8")
    return image_path, manifest_path, payload, label_bytes


@pytest.mark.asyncio
async def test_fetches_companion_label_from_same_archive_and_updates_manifest(tmp_path: Path):
    image_path, manifest_path, payload, label_bytes = prepare_download(tmp_path)

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LABEL_URLS[SOURCE_URL]
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, content=label_bytes)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        result = await fetch_lola_gdr_label(manifest_path, client=client)

    label_path = tmp_path / "sample.lbl"
    assert image_path.read_bytes() == payload
    assert label_path.read_bytes() == label_bytes
    assert result["label_source_url"] == LABEL_URLS[SOURCE_URL]
    assert result["label_sha256_local"] == hashlib.sha256(label_bytes).hexdigest()
    assert result["image_sha256_rechecked"] == hashlib.sha256(payload).hexdigest()
    assert result["label_lines"] == 2
    assert result["label_samples_per_line"] == 2
    assert result["label_derived_minimum_dn"] == -2
    assert result["label_derived_maximum_dn"] == 32767
    saved_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert saved_manifest["label_verification_status"] == "ascii_pds3_parsed_product_and_raster_layout_match"


@pytest.mark.asyncio
async def test_refuses_label_fetch_when_image_digest_changed(tmp_path: Path):
    image_path, manifest_path, _, _ = prepare_download(tmp_path)
    image_path.write_bytes(b"tampered")

    async with httpx.AsyncClient(transport=httpx.MockTransport(lambda request: pytest.fail("network must not run"))) as client:
        with pytest.raises(RuntimeError, match="SHA-256"):
            await fetch_lola_gdr_label(manifest_path, client=client)

    assert not (tmp_path / "sample.lbl").exists()


@pytest.mark.asyncio
async def test_refuses_label_from_unknown_source_manifest(tmp_path: Path):
    _, manifest_path, _, _ = prepare_download(tmp_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_url"] = "https://example.com/fake.img"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="fixed LOLA IMG archives"):
        await fetch_lola_gdr_label(manifest_path)

    assert not (tmp_path / "sample.lbl").exists()


@pytest.mark.asyncio
async def test_refuses_companion_label_with_wrong_product_dimensions(tmp_path: Path):
    _, manifest_path, _, label_bytes = prepare_download(tmp_path)
    bad_label = label_bytes.replace(b"RECORD_BYTES              = 4", b"RECORD_BYTES              = 6")

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=bad_label)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(RuntimeError, match="layout validation"):
            await fetch_lola_gdr_label(manifest_path, client=client)

    assert not (tmp_path / "sample.lbl").exists()


@pytest.mark.asyncio
async def test_refuses_label_redirect(tmp_path: Path):
    _, manifest_path, _, _ = prepare_download(tmp_path)

    async def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/label"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(RuntimeError, match="redirected"):
            await fetch_lola_gdr_label(manifest_path, client=client)

    assert not (tmp_path / "sample.lbl").exists()
