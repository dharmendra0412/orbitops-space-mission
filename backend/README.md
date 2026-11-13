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

After retrieval, validate the complete IMG locally:

```bash
python -m scripts.validate_lola_gdr_sample --image data/raw/lola/ldem_85s_40m.img --label tests/fixtures/lola_ldem_85s_40m.lbl
```

The validator memory-maps the raster and checks the full byte count, decoded sample count, signed little-endian DN extrema, and agreement with the PDS label's `DERIVED_MINIMUM`/`DERIVED_MAXIMUM`. The default label is a source-derived repository fixture; pass the detached source `.LBL` path when available. This validation does not substitute for an upstream checksum or independent geodetic comparison.

## Tests

```bash
pip install -r requirements.txt
pytest
```

The PDS3 label parser is validated against `tests/fixtures/lola_ldem_85s_40m.lbl`, a source-derived fixture for the public `LDEM_85S_40M.IMG` sample. The `lola_gdr` module adds a strict fixed-length signed-16-bit little-endian row iterator, the GDR SIS height/radius conversion helpers, and the DSMAP_POLAR.CAT pixel-to-latitude/longitude transform. These functions validate the selected product's label fields and are unit-tested against small synthetic byte buffers and the published equations. A local validation command can inspect a complete downloaded IMG without loading a second full-size copy into memory and compares observed DN extrema with the label's declared extrema. They are not exposed as a public raster endpoint and are not connected to a terrain UI: the 115 MB IMG has not been retrieved, checksum-verified, decoded, or independently compared. The decoder returns raw DN rows and does not silently apply scaling.
