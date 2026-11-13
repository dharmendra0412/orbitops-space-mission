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

## Tests

```bash
pip install -r requirements.txt
pytest
```

The PDS3 label parser is validated against `tests/fixtures/lola_ldem_85s_40m.lbl`, a source-derived fixture for the public `LDEM_85S_40M.IMG` sample. The parser preserves raw field strings and units; it performs no scaling or coordinate conversion.
