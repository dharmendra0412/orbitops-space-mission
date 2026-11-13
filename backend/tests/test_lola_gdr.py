import struct
from pathlib import Path

import pytest

from app.services.lola_gdr import (
    LOLA_MEAN_EARTH_REFERENCE_RADIUS_M,
    LolaRasterError,
    iter_lola_gdr_rows,
    lola_dn_to_height_m,
    lola_dn_to_planetary_radius_m,
    lola_polar_pixel_to_latlon,
    validate_lola_gdr_file,
)
from app.services.pds3_label import parse_pds3_label


FIXTURE = Path(__file__).parent / "fixtures" / "lola_ldem_85s_40m.lbl"


@pytest.fixture
def lola_metadata() -> dict[str, str]:
    return parse_pds3_label(FIXTURE.read_text(encoding="ascii"))


def test_lola_raster_reader_decodes_little_endian_signed_rows_without_scaling(lola_metadata):
    metadata = dict(lola_metadata)
    metadata.update({"LINES": "2", "LINE_SAMPLES": "2", "FILE_RECORDS": "2", "RECORD_BYTES": "4"})
    binary = struct.pack("<hhhh", -2, 0, 2, 32767)

    rows = list(iter_lola_gdr_rows(binary, metadata))

    assert rows == [(-2, 0), (2, 32767)]
    # Raw DN values are preserved; scaling and OFFSET are not applied here.


def test_lola_raster_reader_rejects_wrong_byte_count(lola_metadata):
    metadata = dict(lola_metadata)
    metadata.update({"LINES": "2", "LINE_SAMPLES": "2", "FILE_RECORDS": "2", "RECORD_BYTES": "4"})

    with pytest.raises(LolaRasterError, match="byte count mismatch"):
        list(iter_lola_gdr_rows(b"\x00\x01", metadata))


def test_lola_raster_reader_rejects_inconsistent_record_layout(lola_metadata):
    metadata = dict(lola_metadata)
    metadata["RECORD_BYTES"] = "15166"

    with pytest.raises(LolaRasterError, match="Record byte count"):
        list(iter_lola_gdr_rows(b"", metadata))


def test_lola_raster_reader_rejects_wrong_sample_encoding(lola_metadata):
    metadata = dict(lola_metadata)
    metadata["SAMPLE_TYPE"] = "MSB_INTEGER"

    with pytest.raises(LolaRasterError, match="little-endian"):
        list(iter_lola_gdr_rows(b"", metadata))


def test_lola_file_validator_checks_full_sample_count_and_source_label_extrema(lola_metadata, tmp_path):
    metadata = dict(lola_metadata)
    metadata.update({
        "LINES": "2",
        "LINE_SAMPLES": "2",
        "FILE_RECORDS": "2",
        "RECORD_BYTES": "4",
        "DERIVED_MINIMUM": "-2",
        "DERIVED_MAXIMUM": "32767",
    })
    raster_path = tmp_path / "sample.img"
    raster_path.write_bytes(struct.pack("<hhhh", -2, 0, 2, 32767))

    result = validate_lola_gdr_file(raster_path, metadata)

    assert result == {
        "bytes": 8,
        "samples": 4,
        "minimum_dn": -2,
        "maximum_dn": 32767,
        "label_extrema_match": True,
    }


def test_lola_file_validator_rejects_extrema_that_disagree_with_source_label(lola_metadata, tmp_path):
    metadata = dict(lola_metadata)
    metadata.update({
        "LINES": "2",
        "LINE_SAMPLES": "2",
        "FILE_RECORDS": "2",
        "RECORD_BYTES": "4",
        "DERIVED_MINIMUM": "-2",
        "DERIVED_MAXIMUM": "10",
    })
    raster_path = tmp_path / "sample.img"
    raster_path.write_bytes(struct.pack("<hhhh", -2, 0, 2, 32767))

    with pytest.raises(LolaRasterError, match="extrema do not match"):
        validate_lola_gdr_file(raster_path, metadata)


def test_lola_file_validator_rejects_wrong_on_disk_size(lola_metadata, tmp_path):
    metadata = dict(lola_metadata)
    metadata.update({
        "LINES": "2",
        "LINE_SAMPLES": "2",
        "FILE_RECORDS": "2",
        "RECORD_BYTES": "4",
    })
    raster_path = tmp_path / "sample.img"
    raster_path.write_bytes(b"short")

    with pytest.raises(LolaRasterError, match="byte count mismatch"):
        validate_lola_gdr_file(raster_path, metadata)


def test_lola_polar_projection_matches_catalog_center_pixel_geometry(lola_metadata):
    latitude, longitude = lola_polar_pixel_to_latlon(
        lola_metadata, line_index=3791, sample_index=3791
    )

    assert -90.0 < latitude < -89.999
    assert longitude == pytest.approx(315.0)
    assert LOLA_MEAN_EARTH_REFERENCE_RADIUS_M == 1_737_400.0


def test_lola_polar_projection_uses_south_pole_y_sign(lola_metadata):
    latitude, longitude = lola_polar_pixel_to_latlon(
        lola_metadata, line_index=3792, sample_index=3792
    )

    assert -90.0 < latitude < -89.999
    assert longitude == pytest.approx(135.0)


def test_lola_polar_projection_uses_catalog_axis_orientation(lola_metadata):
    # PDS catalog: I=sample, J=line, and Y is reversed in the south.
    # A sample east of center with a line north of center is 45 degrees;
    # a sample west with a line south is 225 degrees.
    _, north_east = lola_polar_pixel_to_latlon(
        lola_metadata, line_index=3791, sample_index=3792
    )
    _, south_west = lola_polar_pixel_to_latlon(
        lola_metadata, line_index=3792, sample_index=3791
    )

    assert north_east == pytest.approx(45.0)
    assert south_west == pytest.approx(225.0)


def test_lola_polar_projection_distinguishes_all_four_quadrants(lola_metadata):
    cases = [
        ((3792, 3791), 225.0),
        ((3792, 3792), 135.0),
        ((3791, 3792), 45.0),
        ((3791, 3791), 315.0),
    ]
    for (line_index, sample_index), expected_longitude in cases:
        _, longitude = lola_polar_pixel_to_latlon(
            lola_metadata, line_index=line_index, sample_index=sample_index
        )
        assert longitude == pytest.approx(expected_longitude)


def test_lola_polar_projection_rejects_out_of_bounds_pixels(lola_metadata):
    with pytest.raises(LolaRasterError, match="outside the image bounds"):
        lola_polar_pixel_to_latlon(lola_metadata, line_index=7584, sample_index=0)


def test_lola_polar_projection_rejects_unknown_reference_frame(lola_metadata):
    metadata = dict(lola_metadata)
    metadata["COORDINATE_SYSTEM_NAME"] = "UNKNOWN"

    with pytest.raises(LolaRasterError, match="coordinate reference frame"):
        lola_polar_pixel_to_latlon(metadata, line_index=3791, sample_index=3791)



def test_lola_gdr_height_conversion_uses_scale_without_offset(lola_metadata):
    assert lola_dn_to_height_m(-2, lola_metadata) == -1.0
    assert lola_dn_to_height_m(10, lola_metadata) == 5.0


def test_lola_gdr_planetary_radius_conversion_adds_reference_radius(lola_metadata):
    assert lola_dn_to_planetary_radius_m(-2, lola_metadata) == 1_737_399.0
    assert lola_dn_to_planetary_radius_m(10, lola_metadata) == 1_737_405.0


def test_lola_gdr_conversion_rejects_non_integer_dn(lola_metadata):
    with pytest.raises(LolaRasterError, match="integer sample"):
        lola_dn_to_height_m(1.5, lola_metadata)
