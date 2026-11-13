from __future__ import annotations

import httpx
import pytest
from pathlib import Path

from scripts.validate_lalt_http_range import SAMPLE_POINTS, validate_lalt_source_ranges

from app.services.lalt_client import LaltApiError, LaltClient
from app.services.lalt_pds3 import (
    LALT_GT_SP_IMAGE_BYTES,
    LALT_GT_SP_IMAGE_URL,
    LALT_GT_SP_LABEL_URL,
    LALT_GT_SP_SAMPLE_BYTES,
    LALT_GT_SP_SAMPLES,
)


@pytest.mark.asyncio
async def test_fetch_gt_sp_label_uses_fixed_https_source_and_bounded_ascii():
    label = b'PDS_VERSION_ID = "PDS3"\nEND\n'

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LALT_GT_SP_LABEL_URL
        assert request.headers["accept"] == "text/plain"
        return httpx.Response(200, content=label)

    client = LaltClient(transport=httpx.MockTransport(handler))
    url, text = await client.fetch_gt_sp_label()
    assert url == LALT_GT_SP_LABEL_URL
    assert text == label.decode("ascii")


@pytest.mark.asyncio
async def test_fetch_gt_sp_sample_requests_exact_four_byte_range():
    line_index, sample_index = 1407, 11519
    start = (line_index * LALT_GT_SP_SAMPLES + sample_index) * LALT_GT_SP_SAMPLE_BYTES
    end = start + 3
    body = b"\x00\x00\x80\xbf"

    def handler(request: httpx.Request) -> httpx.Response:
        assert str(request.url) == LALT_GT_SP_IMAGE_URL
        assert request.headers["range"] == f"bytes={start}-{end}"
        return httpx.Response(
            206,
            content=body,
            headers={
                "Content-Range": f"bytes {start}-{end}/{LALT_GT_SP_IMAGE_BYTES}",
                "Content-Length": "4",
            },
        )

    client = LaltClient(transport=httpx.MockTransport(handler))
    url, raw, byte_range = await client.fetch_gt_sp_sample(
        line_index=line_index,
        sample_index=sample_index,
    )
    assert url == LALT_GT_SP_IMAGE_URL
    assert raw == body
    assert byte_range == (start, end)


@pytest.mark.asyncio
async def test_fetch_gt_sp_sample_rejects_ignored_range_redirect_and_wrong_content_range():
    ignored = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, content=bytes(4))
    ))
    with pytest.raises(LaltApiError, match="did not honor"):
        await ignored.fetch_gt_sp_sample(line_index=0, sample_index=0)

    redirected = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"Location": "https://example.com/image"})
    ))
    with pytest.raises(LaltApiError, match="redirected"):
        await redirected.fetch_gt_sp_sample(line_index=0, sample_index=0)

    wrong_range = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(
            206,
            content=bytes(4),
            headers={"Content-Range": f"bytes 4-7/{LALT_GT_SP_IMAGE_BYTES}"},
        )
    ))
    with pytest.raises(LaltApiError, match="unexpected Content-Range"):
        await wrong_range.fetch_gt_sp_sample(line_index=0, sample_index=0)


@pytest.mark.asyncio
async def test_fetch_gt_sp_sample_rejects_truncated_and_oversized_responses():
    truncated = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(
            206,
            content=bytes(3),
            headers={
                "Content-Range": f"bytes 0-3/{LALT_GT_SP_IMAGE_BYTES}",
                "Content-Length": "4",
            },
        )
    ))
    with pytest.raises(LaltApiError, match="incomplete"):
        await truncated.fetch_gt_sp_sample(line_index=0, sample_index=0)

    oversized = LaltClient(transport=httpx.MockTransport(
        lambda request: httpx.Response(
            206,
            content=bytes(5),
            headers={
                "Content-Range": f"bytes 0-3/{LALT_GT_SP_IMAGE_BYTES}",
                "Content-Length": "4",
            },
        )
    ))
    with pytest.raises(LaltApiError, match="more than four"):
        await oversized.fetch_gt_sp_sample(line_index=0, sample_index=0)


@pytest.mark.parametrize(
    ("line", "sample"),
    [(-1, 0), (0, -1), (1408, 0), (0, 11520), (True, 0), (0, 1.5)],
)
@pytest.mark.asyncio
async def test_fetch_gt_sp_sample_rejects_invalid_indices(line, sample):
    client = LaltClient(transport=httpx.MockTransport(
        lambda request: pytest.fail("No HTTP request should be made for invalid indices")
    ))
    with pytest.raises(LaltApiError, match="index"):
        await client.fetch_gt_sp_sample(line_index=line, sample_index=sample)


@pytest.mark.asyncio
async def test_source_range_validation_compares_live_client_bytes_with_full_image(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "lalt_gt_sp_img.lbl"
    label_bytes = fixture.read_bytes()
    image_path = tmp_path / "LALT_GT_SP_IMG.IMG"
    image_path.touch()
    with image_path.open("r+b") as image:
        image.truncate(LALT_GT_SP_IMAGE_BYTES)
        expected_by_offset = {}
        for index, (line, sample) in enumerate(SAMPLE_POINTS):
            offset = (line * LALT_GT_SP_SAMPLES + sample) * LALT_GT_SP_SAMPLE_BYTES
            raw = bytes([index + 1, index + 2, index + 3, index + 4])
            image.seek(offset)
            image.write(raw)
            expected_by_offset[offset] = raw

    def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == LALT_GT_SP_LABEL_URL:
            return httpx.Response(200, content=label_bytes)
        assert str(request.url) == LALT_GT_SP_IMAGE_URL
        start, end = map(int, request.headers["range"].removeprefix("bytes=").split("-"))
        assert end - start + 1 == LALT_GT_SP_SAMPLE_BYTES
        return httpx.Response(
            206,
            content=expected_by_offset[start],
            headers={
                "Content-Range": f"bytes {start}-{end}/{LALT_GT_SP_IMAGE_BYTES}",
                "Content-Length": "4",
            },
        )

    client = LaltClient(transport=httpx.MockTransport(handler))
    report = await validate_lalt_source_ranges(
        image_path=image_path,
        label_path=fixture,
        client=client,
    )
    assert report["label_matches_downloaded_validation_label"] is True
    assert report["samples_checked"] == len(SAMPLE_POINTS)
    assert all(sample["matches_validated_local_img"] for sample in report["samples"])
