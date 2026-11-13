from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import httpx
import numpy as np
import rasterio
from rasterio.windows import Window


JP2_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_85s_40m.jp2"
)
JP2_LABEL_URL = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_85s_40m_jp2.lbl"
)
EXPECTED_JP2_BYTES = 24_960_972
EXPECTED_SHAPE = (7_584, 7_584)


def _download(url: str, destination: Path, expected_bytes: int) -> dict[str, object]:
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_name(destination.name + ".part")
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite existing reference file: {destination}")
    digest = hashlib.sha256()
    received = 0
    try:
        with httpx.stream(
            "GET",
            url,
            headers={"Accept": "application/octet-stream", "Accept-Encoding": "identity"},
            timeout=httpx.Timeout(120.0, connect=20.0),
            follow_redirects=False,
        ) as response:
            if response.is_redirect:
                raise RuntimeError(f"Reference source redirected; refusing unverified destination: {url}")
            response.raise_for_status()
            declared = response.headers.get("content-length")
            if declared is not None and int(declared) != expected_bytes:
                raise RuntimeError(
                    f"Reference Content-Length mismatch: expected {expected_bytes}, received {declared}"
                )
            with temporary.open("xb") as output:
                for chunk in response.iter_bytes():
                    received += len(chunk)
                    if received > expected_bytes:
                        raise RuntimeError("Reference download exceeded expected byte count")
                    output.write(chunk)
                    digest.update(chunk)
                output.flush()
        if received != expected_bytes:
            raise RuntimeError(f"Reference byte count mismatch: expected {expected_bytes}, received {received}")
        temporary.replace(destination)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise
    return {
        "source_url": url,
        "file_name": destination.name,
        "expected_bytes_from_archive_listing": expected_bytes,
        "actual_bytes_downloaded": received,
        "sha256_local": digest.hexdigest(),
        "upstream_checksum": None,
        "verification_status": "byte_count_verified_local_sha256_computed_no_upstream_checksum_published",
    }


def validate_jp2_against_img(image_path: Path, jp2_path: Path) -> dict[str, object]:
    raw = np.memmap(image_path, dtype="<i2", mode="r", shape=EXPECTED_SHAPE)
    mismatch_count = 0
    max_absolute_difference = 0
    minimum_value: int | None = None
    maximum_value: int | None = None

    with rasterio.open(jp2_path) as reference:
        if reference.driver != "JP2OpenJPEG":
            raise RuntimeError(f"Expected independent JP2OpenJPEG decoder, received {reference.driver}")
        if reference.count != 1 or (reference.height, reference.width) != EXPECTED_SHAPE:
            raise RuntimeError(
                f"JP2 dimensions/bands mismatch: {reference.count} bands, "
                f"{reference.height}x{reference.width}"
            )
        if reference.dtypes[0] != "int16":
            raise RuntimeError(f"Expected signed 16-bit JP2 samples, received {reference.dtypes[0]}")

        for row_index in range(EXPECTED_SHAPE[0]):
            decoded = reference.read(
                1,
                window=Window(0, row_index, EXPECTED_SHAPE[1], 1),
            )[0]
            expected = np.asarray(raw[row_index], dtype=np.int16)
            difference = np.abs(decoded.astype(np.int32) - expected.astype(np.int32))
            row_mismatches = int(np.count_nonzero(difference))
            mismatch_count += row_mismatches
            if row_mismatches:
                max_absolute_difference = max(max_absolute_difference, int(difference.max()))
            row_min = int(decoded.min())
            row_max = int(decoded.max())
            minimum_value = row_min if minimum_value is None else min(minimum_value, row_min)
            maximum_value = row_max if maximum_value is None else max(maximum_value, row_max)

        driver = reference.driver
        transform = tuple(reference.transform)
        crs = reference.crs.to_string() if reference.crs else None

    if mismatch_count:
        raise RuntimeError(
            f"JP2OpenJPEG decoded {mismatch_count} samples differently from the raw IMG; "
            f"maximum absolute DN difference={max_absolute_difference}"
        )

    return {
        "reference_driver": driver,
        "dimensions": {"lines": EXPECTED_SHAPE[0], "samples_per_line": EXPECTED_SHAPE[1]},
        "decoded_samples": EXPECTED_SHAPE[0] * EXPECTED_SHAPE[1],
        "minimum_dn": minimum_value,
        "maximum_dn": maximum_value,
        "sample_mismatch_count": mismatch_count,
        "max_absolute_dn_difference": max_absolute_difference,
        "exact_sample_match": True,
        "geotransform": transform,
        "crs": crs,
        "scope": (
            "Every JP2OpenJPEG-decoded sample was compared with the corresponding raw "
            "signed little-endian IMG sample. This is an independent decoder/encoding "
            "cross-check of the archived product, not an independent measurement dataset."
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Cross-check the PDS LOLA IMG raster against its separately archived JPEG2000 counterpart."
    )
    parser.add_argument("--image", type=Path, default=Path("data/raw/lola/ldem_85s_40m.img"))
    parser.add_argument("--jp2", type=Path, default=Path("data/raw/lola/ldem_85s_40m.jp2"))
    parser.add_argument(
        "--jp2-label",
        type=Path,
        default=Path("data/raw/lola/ldem_85s_40m_jp2.lbl"),
    )
    args = parser.parse_args()

    if not args.image.is_file():
        parser.error(f"Validated IMG does not exist: {args.image}")

    jp2_manifest = _download(JP2_URL, args.jp2, EXPECTED_JP2_BYTES)
    label_manifest = _download(JP2_LABEL_URL, args.jp2_label, 6_354)
    label_text = args.jp2_label.read_text(encoding="ascii")
    required_label_values = (
        'PRODUCT_VERSION_ID        = "V2.1"',
        'PRODUCT_ID                = "LDEM_85S_40M"',
        'ENCODING_TYPE              = "JP2"',
        'UNCOMPRESSED_FILE_NAME  = "LDEM_85S_40M.IMG"',
        'REQUIRED_STORAGE_BYTES     = "24960972"',
        "DERIVED_MINIMUM       = -11002",
        "DERIVED_MAXIMUM       = 14054",
    )
    missing = [value for value in required_label_values if value not in label_text]
    if missing:
        parser.error(f"JP2 PDS label is missing required source fields: {missing}")

    result = validate_jp2_against_img(args.image, args.jp2)
    output = {
        "jp2_manifest": jp2_manifest,
        "jp2_label_manifest": label_manifest,
        "jp2_label_product_version": "V2.1",
        "raw_img_product_version": "V2.0",
        "validation": result,
    }
    manifest_path = args.jp2.with_name(args.jp2.name + ".manifest.json")
    manifest_path.write_text(json.dumps(output, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(output, indent=2))


if __name__ == "__main__":
    main()
