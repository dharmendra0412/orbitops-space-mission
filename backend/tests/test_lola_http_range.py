import httpx
import pytest

from scripts.validate_lola_http_range import (
    EXPECTED_IMAGE_BYTES,
    SOURCE_URL,
    validate_range_response,
)


def test_range_probe_requires_exact_206_and_matches_verified_img_prefix():
    result = validate_range_response(
        status_code=206,
        headers=httpx.Headers({
            "Content-Range": f"bytes 0-1/{EXPECTED_IMAGE_BYTES}",
            "Content-Length": "2",
        }),
        body=bytes([1, 128]),
        local_prefix=bytes([1, 128]),
    )
    assert result["source_url"] == SOURCE_URL
    assert result["bytes_returned"] == 2
    assert result["sample_dn"] == -32767
    assert result["matches_validated_local_img"] is True


@pytest.mark.parametrize("status_code", [200, 301, 416])
def test_range_probe_rejects_status_without_partial_content(status_code):
    with pytest.raises(RuntimeError, match="did not honor HTTP Range"):
        validate_range_response(
            status_code=status_code,
            headers=httpx.Headers({"Content-Range": f"bytes 0-1/{EXPECTED_IMAGE_BYTES}"}),
            body=bytes([0, 0]),
            local_prefix=bytes([0, 0]),
        )


def test_range_probe_validates_nonzero_pixel_byte_offset():
    byte_start = 57_509_470
    result = validate_range_response(
        status_code=206,
        headers=httpx.Headers({
            "Content-Range": f"bytes {byte_start}-{byte_start + 1}/{EXPECTED_IMAGE_BYTES}",
            "Content-Length": "2",
        }),
        body=bytes([0x06, 0xD5]),
        local_prefix=bytes([0x06, 0xD5]),
        byte_start=byte_start,
    )
    assert result["byte_range_inclusive"] == {"start": byte_start, "end": byte_start + 1}
    assert result["sample_dn"] == -11002


def test_range_probe_rejects_incorrect_content_range():
    with pytest.raises(RuntimeError, match="unexpected Content-Range"):
        validate_range_response(
            status_code=206,
            headers=httpx.Headers({"Content-Range": f"bytes 2-3/{EXPECTED_IMAGE_BYTES}"}),
            body=bytes([0, 0]),
            local_prefix=bytes([0, 0]),
        )


def test_range_probe_rejects_nonmatching_source_bytes():
    with pytest.raises(RuntimeError, match="do not match"):
        validate_range_response(
            status_code=206,
            headers=httpx.Headers({"Content-Range": f"bytes 0-1/{EXPECTED_IMAGE_BYTES}"}),
            body=bytes([1, 0]),
            local_prefix=bytes([2, 0]),
        )
