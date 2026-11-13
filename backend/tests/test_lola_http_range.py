import struct
from pathlib import Path

import pytest

from app.services.pds_client import (
    PDS_LOLA_GDR_IMAGE_BYTES,
    PDS_LOLA_GDR_RECORD_BYTES,
    PDS_LOLA_GDR_SAMPLE_IMG_URL,
)
from scripts.validate_lola_http_range import SAMPLE_POINTS, validate_source_range


class StubPixelClient:
    def __init__(self, samples: dict[tuple[int, int], int], *, mismatch: bool = False):
        self.samples = samples
        self.mismatch = mismatch
        self.calls: list[tuple[int, int]] = []

    async def fetch_lola_gdr_sample_dn(self, *, line_index: int, sample_index: int):
        self.calls.append((line_index, sample_index))
        byte_start = line_index * PDS_LOLA_GDR_RECORD_BYTES + sample_index * 2
        dn = self.samples[(line_index, sample_index)]
        if self.mismatch and self.calls[-1] == SAMPLE_POINTS[0]:
            dn += 1
        return PDS_LOLA_GDR_SAMPLE_IMG_URL, dn, (byte_start, byte_start + 1)


def make_sparse_lola_image(path: Path) -> dict[tuple[int, int], int]:
    samples = {
        point: -1295 - index
        for index, point in enumerate(SAMPLE_POINTS)
    }
    with path.open("wb") as image:
        image.truncate(PDS_LOLA_GDR_IMAGE_BYTES)
        for (line_index, sample_index), dn in samples.items():
            image.seek(line_index * PDS_LOLA_GDR_RECORD_BYTES + sample_index * 2)
            image.write(struct.pack("<h", dn))
    return samples


@pytest.mark.asyncio
async def test_range_validation_exercises_eight_live_api_offsets_and_matches_local_img(tmp_path):
    image_path = tmp_path / "ldem_85s_40m.img"
    samples = make_sparse_lola_image(image_path)
    client = StubPixelClient(samples)

    report = await validate_source_range(image_path, client=client)

    assert report["samples_checked"] == 8
    assert [ (sample["line_index"], sample["sample_index"]) for sample in report["samples"] ] == list(SAMPLE_POINTS)
    assert all(sample["matches_validated_local_img"] for sample in report["samples"])
    assert client.calls == list(SAMPLE_POINTS)


@pytest.mark.asyncio
async def test_range_validation_rejects_api_dn_that_differs_from_local_img(tmp_path):
    image_path = tmp_path / "ldem_85s_40m.img"
    samples = make_sparse_lola_image(image_path)
    client = StubPixelClient(samples, mismatch=True)

    with pytest.raises(RuntimeError, match="does not match the validated IMG"):
        await validate_source_range(image_path, client=client)


@pytest.mark.asyncio
async def test_range_validation_rejects_unexpected_source_url_or_offset(tmp_path):
    image_path = tmp_path / "ldem_85s_40m.img"
    samples = make_sparse_lola_image(image_path)

    class WrongSourceClient(StubPixelClient):
        async def fetch_lola_gdr_sample_dn(self, *, line_index: int, sample_index: int):
            url, dn, byte_range = await super().fetch_lola_gdr_sample_dn(
                line_index=line_index,
                sample_index=sample_index,
            )
            return "https://example.com/not-the-pds-source.img", dn, byte_range

    with pytest.raises(RuntimeError, match="unexpected source URL"):
        await validate_source_range(image_path, client=WrongSourceClient(samples))


@pytest.mark.asyncio
async def test_range_validation_rejects_wrong_local_image_size(tmp_path):
    image_path = tmp_path / "truncated.img"
    image_path.write_bytes(b"too short")
    with pytest.raises(RuntimeError, match="expected validated product size"):
        await validate_source_range(image_path, client=StubPixelClient({}))
