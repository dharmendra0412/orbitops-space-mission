# ORBITOPS Data API

Read-only FastAPI service for discovering original planetary-science products through NASA's PDS Search API.

## Run locally

Use Python 3.11 or later.

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Endpoints:

- `GET /health`
- `GET /api/v1/pds/search?keywords=LOLA&limit=10`
- `GET /api/v1/pds/products/{identifier}/members?depth=1|2&limit=100&search_after=...` — browse paginated child collections/products or two hierarchy levels.
- `GET /api/v1/pds/products/{identifier}`
- `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/label` — fetch one fixed public PDS3 label from the PDS Geosciences Node and return allowlisted metadata fields.

The API returns the original upstream JSON under `response`, together with the actual request URL, query, and retrieval timestamp. The product-resolution endpoint requests the full PDS4 JSON representation, which can include label/data-file references, file sizes, and checksums. The hierarchy endpoint browses one or two levels of the PDS archive. It caps pages at 100 records and uses the PDS harvest-time sort/cursor documented for search-after pagination. It does not download the referenced files, generate fallback records, or transform observations. The LOLA sample-label route uses a fixed allowlisted HTTPS source URL, refuses redirects, caps the response at 1 MB, requires ASCII text, and parses only an allowlist of PDS3 scalar fields. It does not fetch or decode the associated IMG raster.

The PDS Search API documentation warns that its servers are not fully populated with all PDS datasets. A zero-result or missing product response is not proof that a product does not exist. Cross-check against the relevant mission archive and PDS node index.

## Bounded LOLA raster retrieval

From the `backend/` directory, run:

```bash
python scripts/fetch_lola_gdr_sample.py --output data/raw/lola/ldem_85s_40m.img
```

The downloader tries two fixed HTTPS sources in order: the PDS Geosciences archive, then the LOLA Data Node at MIT if the first source has a transport failure or a server-side 5xx response. The NASA PDS LOLA page directs users to that Data Node for the latest holdings, and its polar IMG directory lists the same `LDEM_85S_40M.IMG` filename and 115,034,112-byte size. The downloader refuses redirects, rejects unexpected response lengths, streams to a temporary file, and atomically writes the raster plus a JSON provenance manifest. The manifest records the endpoint that actually supplied the file and the fixed source attempts. It computes a local SHA-256 fingerprint but explicitly records that no upstream checksum was published in the inspected directory listings; byte-count verification must not be described as cryptographic source verification. Downloaded rasters under `data/raw/` are git-ignored. The downloader is not automatically run by the web application or CI.

Fetch the companion label from the same archive host that supplied the IMG, then validate the complete raster:

```bash
python -m scripts.fetch_lola_gdr_label
python -m scripts.validate_lola_gdr_sample
```

The label-fetch command reads the IMG provenance manifest, permits only the two fixed LOLA archive hosts, rechecks the IMG's on-disk byte count and SHA-256, retrieves the matching `.LBL` from that same host, parses its PDS3 product/layout fields, and verifies that its dimensions agree with the IMG download manifest. It then records the label URL, local SHA-256, data-set/version identifiers, dimensions, and declared DN extrema in the manifest. The validator defaults to this downloaded companion label, memory-maps the raster, and checks the full byte count, decoded sample count, signed little-endian DN extrema, and agreement with the source label's declared extrema. This does not substitute for an upstream checksum or independent geodetic comparison.

## Tests

```bash
pip install -r requirements.txt
pytest
```

The PDS3 label parser is validated against `tests/fixtures/lola_ldem_85s_40m.lbl`, a source-derived fixture for the public `LDEM_85S_40M.IMG` sample. The `lola_gdr` module adds a strict fixed-length signed-16-bit little-endian row iterator, the GDR SIS height/radius conversion helpers, and the DSMAP_POLAR.CAT pixel-to-latitude/longitude transform. The projection follows the primary PDS `DSMAP_POLAR.CAT` equations exactly: `I` is sample, `J` is line, the southern-hemisphere Y coordinate is sign-reversed, and longitude is `atan2(X,Y)`. Regression tests cover all four quadrants and the documented south-pole map orientation. The GitHub Actions workflow `LOLA Source Retrieval Gate` retrieved the original 115,034,112-byte IMG and its 4,986-byte companion PDS3 label from the PDS Geosciences archive. Full-file validation decoded 57,517,056 samples and confirmed the observed DN extrema (-11002, 14054) match the downloaded label. It also decoded the archive's JPEG2000 counterpart using GDAL JP2OpenJPEG and compared all 57,517,056 samples: maximum absolute difference 1 DN, mean absolute difference 0.500013648 DN, RMS difference 0.707116432 DN, and zero samples outside the 1-DN tolerance. The JP2 geotransform and lunar polar stereographic CRS were checked against the selected product's 40 m grid and 1737.4 km reference radius. The IMG, labels, JP2, and local provenance fingerprints are preserved in a GitHub Actions artifact, not committed to the repository; the archive does not publish an upstream IMG checksum. This is an independent decoder/encoding cross-check of the same archived product, not independent measurement ground truth. A further workflow step samples four bounded windows against NASA GSFC PGDA's separately adjusted `LDEM_80S_40MPP_ADJ.TIF` COG, aligns it to the PDS source grid, and records height residual statistics. The completed run compared 1,048,576 pairs (bias -0.0876 m, MAE 0.9414 m, RMSE 1.5300 m, P95 absolute residual 3.1355 m, P99 5.5357 m). The PGDA reference is another LOLA-derived product, not independent sensor ground truth. Its product page explicitly declares MOON_ME / DE421; the embedded GeoTIFF WKT describes the lunar body datum and projection but does not encode ephemeris identity, so it is not a conflicting declaration. The workflow now also compares up to four valid non-overlapping windows against NASA PGDA's 5 m/pixel Haworth regional DEM, with the product's published interpolation and uncertainty caveats retained. The scripts are not exposed as a public raster endpoint or terrain UI; geodetic ground-truth validation remains required before terrain rendering. The decoder returns raw DN rows and does not silently apply scaling.
