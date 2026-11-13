from __future__ import annotations

import argparse
import json
from pathlib import Path

from app.services.lola_gdr import LolaRasterError, validate_lola_gdr_file
from app.services.pds3_label import PdsLabelError, parse_pds3_label


DEFAULT_IMAGE = Path("data/raw/lola/ldem_85s_40m.img")
DEFAULT_LABEL = Path("tests/fixtures/lola_ldem_85s_40m.lbl")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Validate a downloaded LOLA GDR IMG against its PDS3 label layout and sample extrema."
    )
    parser.add_argument("--image", type=Path, default=DEFAULT_IMAGE, help="Downloaded IMG raster path")
    parser.add_argument(
        "--label",
        type=Path,
        default=DEFAULT_LABEL,
        help="PDS3 label path (defaults to the repository's source-derived label fixture)",
    )
    args = parser.parse_args()

    try:
        metadata = parse_pds3_label(args.label.read_text(encoding="ascii"))
        result = validate_lola_gdr_file(args.image, metadata)
    except (OSError, PdsLabelError, LolaRasterError) as exc:
        parser.exit(1, f"LOLA raster validation failed: {exc}\n")

    print(json.dumps({
        "image_path": str(args.image),
        "label_path": str(args.label),
        "data_set_id": metadata.get("DATA_SET_ID"),
        "product_version_id": metadata.get("PRODUCT_VERSION_ID"),
        "validation": result,
        "scope": (
            "Checks file byte count, signed little-endian sample decoding, sample count, "
            "and observed DN extrema against the selected PDS3 label. It does not verify "
            "an upstream checksum or independently establish geodetic accuracy."
        ),
    }, indent=2))


if __name__ == "__main__":
    main()
