from __future__ import annotations

import httpx
import pytest

from app.services.lalt_client import LALT_LABEL_MAX_BYTES, LaltApiError, LaltClient
from app.services.lalt_pds3 import LALT_GT_SP_LABEL_URL


@pytest.mark.asyncio
async def test_fetch_gt_sp_label_uses_fixed_https_source_and_preserves_ascii():
    label = b'PDS_VERSION_ID = "PDS3"\r\nEND\r\n'

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LALT_GT_SP_LABEL_URL
        assert request.headers["accept"] == "text/plain"
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, content=label)

    client = LaltClient(transport=httpx.MockTransport(handler))
    url, text = await client.fetch_gt_sp_label()
    assert url == LALT_GT_SP_LABEL_URL
    assert text.encode("ascii") == label


@pytest.mark.asyncio
async def test_fetch_gt_sp_label_rejects_redirects_and_non_ascii():
    redirected = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"Location": "https://example.com/label"})
    ))
    with pytest.raises(LaltApiError, match="redirected"):
        await redirected.fetch_gt_sp_label()

    non_ascii = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=b"\xff")
    ))
    with pytest.raises(LaltApiError, match="not valid ASCII"):
        await non_ascii.fetch_gt_sp_label()


@pytest.mark.asyncio
async def test_fetch_gt_sp_label_rejects_oversized_body_and_unexpected_host():
    oversized = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=bytes(LALT_LABEL_MAX_BYTES + 1))
    ))
    with pytest.raises(LaltApiError, match="size limit"):
        await oversized.fetch_gt_sp_label()



@pytest.mark.asyncio
async def test_fetch_gt_sp_label_maps_upstream_http_errors():
    missing = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(404)
    ))
    with pytest.raises(LaltApiError, match="HTTP 404") as error:
        await missing.fetch_gt_sp_label()
    assert error.value.status_code == 404
