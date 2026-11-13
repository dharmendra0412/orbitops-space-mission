import hashlib
from pathlib import Path

import httpx
import pytest

from scripts.fetch_lola_gdr_sample import FALLBACK_SOURCE_URL, SOURCE_URL, download_lola_gdr_img


@pytest.mark.asyncio
async def test_lola_img_downloader_checks_size_and_writes_local_digest_manifest(tmp_path: Path):
    payload = b"LOLA"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == SOURCE_URL
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, content=payload)

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        manifest = await download_lola_gdr_img(destination, client=client, expected_bytes=len(payload))

    assert destination.read_bytes() == payload
    assert manifest["actual_bytes_downloaded"] == len(payload)
    assert manifest["sha256_local"] == hashlib.sha256(payload).hexdigest()
    assert manifest["upstream_checksum"] is None
    assert manifest["source_url"] == SOURCE_URL
    assert manifest["source_attempts"] == [SOURCE_URL]
    assert "no_upstream_checksum_published" in manifest["verification_status"]
    assert (tmp_path / "lola.img.manifest.json").exists()


@pytest.mark.asyncio
async def test_lola_img_downloader_uses_fixed_lola_node_fallback_after_transport_failure(tmp_path: Path):
    payload = b"LOLA"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == SOURCE_URL:
            raise httpx.ConnectError("simulated primary archive DNS failure", request=request)
        assert str(request.url) == FALLBACK_SOURCE_URL
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, content=payload)

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        manifest = await download_lola_gdr_img(destination, client=client, expected_bytes=len(payload))

    assert destination.read_bytes() == payload
    assert manifest["source_url"] == FALLBACK_SOURCE_URL
    assert manifest["source_attempts"] == [SOURCE_URL, FALLBACK_SOURCE_URL]
    assert manifest["actual_bytes_downloaded"] == len(payload)


@pytest.mark.asyncio
async def test_lola_img_downloader_uses_fallback_after_server_error(tmp_path: Path):
    payload = b"LOLA"

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == SOURCE_URL:
            return httpx.Response(503, request=request)
        assert str(request.url) == FALLBACK_SOURCE_URL
        return httpx.Response(200, content=payload)

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        manifest = await download_lola_gdr_img(destination, client=client, expected_bytes=len(payload))

    assert destination.read_bytes() == payload
    assert manifest["source_url"] == FALLBACK_SOURCE_URL
    assert manifest["source_attempts"] == [SOURCE_URL, FALLBACK_SOURCE_URL]


@pytest.mark.asyncio
async def test_lola_img_downloader_does_not_hide_client_errors_with_fallback(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == SOURCE_URL
        return httpx.Response(404, request=request)

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(httpx.HTTPStatusError):
            await download_lola_gdr_img(destination, client=client, expected_bytes=4)

    assert not destination.exists()
    assert not (tmp_path / "lola.img.part").exists()


@pytest.mark.asyncio
async def test_lola_img_downloader_rejects_content_length_mismatch(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"TOO-LONG")

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(RuntimeError, match="Content-Length mismatch"):
            await download_lola_gdr_img(destination, client=client, expected_bytes=4)

    assert not destination.exists()
    assert not (tmp_path / "lola.img.part").exists()


@pytest.mark.asyncio
async def test_lola_img_downloader_refuses_redirects(tmp_path: Path):
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"location": "https://example.com/raster"})

    destination = tmp_path / "lola.img"
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False) as client:
        with pytest.raises(RuntimeError, match="redirected"):
            await download_lola_gdr_img(destination, client=client, expected_bytes=4)

    assert not destination.exists()


@pytest.mark.asyncio
async def test_lola_img_downloader_refuses_overwrite(tmp_path: Path):
    destination = tmp_path / "lola.img"
    destination.write_bytes(b"existing")

    with pytest.raises(FileExistsError):
        await download_lola_gdr_img(destination, expected_bytes=8)

    assert destination.read_bytes() == b"existing"
