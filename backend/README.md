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
- `GET /api/v1/pds/products/{identifier}/members?depth=1|2` — browse child collections/products or two hierarchy levels.
- `GET /api/v1/pds/products/{identifier}/members?depth=1|2`
- `GET /api/v1/pds/products/{identifier}`

The API returns the original upstream JSON under `response`, together with the actual request URL, query, and retrieval timestamp. It does not generate fallback records or transform observations.

The PDS Search API documentation warns that its servers are not fully populated with all PDS datasets. A zero-result or missing product response is not proof that a product does not exist. Cross-check against the relevant mission archive and PDS node index.

## Tests

```bash
pip install -r requirements.txt
pytest
```
