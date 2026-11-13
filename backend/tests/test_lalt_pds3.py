from __future__ import annotations

import struct
from pathlib import Path

import pytest

from app.services.lalt_pds3 import (
    LALT_GT_SP_EASTERNMOST_LONGITUDE,
    LALT_GT_SP_IMAGE_BYTES,
    LALT_GT_SP_MAXIMUM_LATITUDE,
    LALT_GT_SP_MINIMUM_LATITUDE,
    LALT_GT_SP_SAMPLES,
    LALT_GT_SP_WESTERNMOST_LONGITUDE,
    LaltPdsError,
    decode_lalt_pc_real_sample,
    lalt_grid_node_to_lat_lon,
    parse_and_validate_lalt_gt_sp_label,
    validate_lalt_gt_sp_image_file,
)


FIXTURE = Path(__file__).parent / "fixtures" / "lalt_gt_sp_img.lbl"


def test_lalt_pds3_label_matches_documented_v2_image_layout():
    result = parse_and_validate_lalt_gt_sp_label(FIXTURE.read_text(encoding="ascii"))
    assert result["dataset_id"] == "SLN-L-LALT-5-TOPO-GT-SP-IMG-V2.0"
    assert result["lines"] == 1408
    assert result["line_samples"] == LALT_GT_SP_SAMPLES
    assert result["sample_type"] == "PC_REAL (little-endian IEEE 754 float32)"
    assert result["image_bytes"] == LALT_GT_SP_IMAGE_BYTES
    assert result["coordinate_system"] == "MEAN EARTH/POLAR AXIS OF DE421"
    assert result["map_projection_type"] == "N/A"


def test_lalt_grid_nodes_follow_label_latitude_and_longitude_axes():
    assert lalt_grid_node_to_lat_lon(0, 0) == (
        LALT_GT_SP_MAXIMUM_LATITUDE,
        LALT_GT_SP_WESTERNMOST_LONGITUDE,
    )
    assert lalt_grid_node_to_lat_lon(1407, 11519) == (
        LALT_GT_SP_MINIMUM_LATITUDE,
        LALT_GT_SP_EASTERNMOST_LONGITUDE,
    )


@pytest.mark.parametrize(
    ("line", "sample"),
    [(-1, 0), (0, -1), (1408, 0), (0, 11520), (1.5, 2)],
)
def test_lalt_grid_pixel_coordinates_reject_out_of_bounds_or_non_integer_indices(line, sample):
    with pytest.raises(LaltPdsError):
        lalt_grid_node_to_lat_lon(line, sample)


def test_lalt_pc_real_samples_decode_little_endian_and_honor_dummy_value():
    assert decode_lalt_pc_real_sample(struct.pack("<f", -1.234)) == pytest.approx(-1.234)
    assert decode_lalt_pc_real_sample(struct.pack("<f", 99.999)) is None


def test_lalt_pc_real_rejects_wrong_width_and_non_finite_samples():
    with pytest.raises(LaltPdsError, match="exactly four bytes"):
        decode_lalt_pc_real_sample(b"\x00\x00")
    with pytest.raises(LaltPdsError, match="not finite"):
        decode_lalt_pc_real_sample(struct.pack("<f", float("nan")))


def test_lalt_label_rejects_wrong_byte_order_and_grid_dimensions():
    label = FIXTURE.read_text(encoding="ascii")
    with pytest.raises(LaltPdsError, match="SAMPLE_TYPE"):
        parse_and_validate_lalt_gt_sp_label(label.replace("SAMPLE_TYPE                    = PC_REAL", "SAMPLE_TYPE                    = IEEE_REAL"))
    with pytest.raises(LaltPdsError, match="LINE_SAMPLES"):
        parse_and_validate_lalt_gt_sp_label(label.replace("LINE_SAMPLES                   = 11520", "LINE_SAMPLES                   = 11400"))


def test_lalt_image_file_size_is_checked(tmp_path):
    image = tmp_path / "wrong.img"
    image.write_bytes(bytes(16))
    with pytest.raises(LaltPdsError, match="byte size mismatch"):
        validate_lalt_gt_sp_image_file(image)
