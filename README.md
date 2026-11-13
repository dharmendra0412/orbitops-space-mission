# ORBITOPS — Space Mission Planning Workspace

**Plan. Trace. Verify. Discover.**

ORBITOPS is an independent educational workspace for exploring space-mission requirements and authoritative science resources. It is being built without fabricated observations, synthetic mission outputs, or mission simulations.

## Non-negotiable product rules

- Do not display invented NASA observations, telemetry, spacecraft specifications, orbital states, costs, or performance values.
- Distinguish user-entered values, original source observations, derived values, and unavailable information.
- If an input has not been sourced and validated, show **Not sourced** or **Not available**. Never fill gaps with placeholder numbers.
- Every ingested value must retain its source, product identifier, retrieval metadata, units, coordinate reference, and limitations.
- Do not imply that an external resource has been downloaded or integrated merely because it appears in the source catalogue.
- No orbital propagation, mission simulation, simulated operations, or synthetic telemetry is in the product scope.

## Current implementation

The current feature branch includes:

- Responsive React/TypeScript mission-planning interface.
- Selectable research categories and non-numeric orbit architecture labels.
- Explicit unavailable states for mass, power, data volume, mission cost, and engineering verification.
- A curated catalogue linking directly to NASA, NASA PDS, JPL, and partner reference pages.
- A documented source-provenance and data-ingestion plan.
- A read-only FastAPI proxy for live PDS keyword search, product resolution, and archive hierarchy browsing.
- PDS metadata parsing for original label/data-file references, sizes, MIME types, and checksums when supplied by the source.
- A bounded live metadata endpoint for one verified LOLA PDS3 south-polar GDR label, with a conservative parser and source-derived test fixture.
- A source-backed pixel lookup that requests exactly two bytes from the fixed PDS Geosciences archive URL using HTTP Range, validates the PDS label, and returns the original signed DN plus documented height/radius conversions and PDS polar coordinates.
- A bounded LOLA row-profile lookup (up to 512 contiguous samples) and a source-derived elevation plot with the label's metres-per-pixel spacing; no interpolation or smoothing is applied.
- A fixed-source Kaguya LALT PDS3 label lookup with strict product-layout validation. The DARTS host did not return HTTP 206 for a bounded sample request, so the app intentionally exposes label metadata only instead of downloading the full 64.9 MB image for individual clicks.
- A controlled CI source-validation gate for the original Kaguya LALT calibrated range table `LALT_RD_20080105.TAB` (12,002 rows, 11 columns, fixed 162-byte records). It preserves the raw onboard TI clock tags and instrument range values; it does not convert them to UTC/ET or claim surface geolocation.
- A user-authored mission brief builder with browser-local autosave, JSON import/export, and a requirement traceability matrix. Source links remain unverified until separately checked.
- Automated frontend and backend tests, dependency audits, and production builds.

The selectable categories are research prompts only. They are not a verified flight-hardware catalogue or a spacecraft configuration. The source catalogue is not an ingestion pipeline. The source-validation workflow downloads and validates the fixed LOLA sample product, Kaguya LALT south-polar PDS3 grid, and one raw daily Kaguya LALT range table for repeatable engineering and cross-sensor consistency checks. Raw LALT range is not geolocated; the SCLK/CK/SPK/IK/FK/ME-frame reconstruction chain is documented but not yet executed. The live application does not bulk-download, cache, or synchronize observation files; pixel and row-profile endpoints request only bounded byte ranges from fixed PDS rasters. The Kaguya LALT product is a separately labelled interpolated cross-sensor dataset, not independent geodetic truth; no live pixel endpoint is exposed because the source host did not honor bounded Range requests.

## Mission brief workspace

Open **Mission brief** from the sidebar to record a team-authored concept. The fields start blank by design; the application does not invent a target, duration, orbit, payload, spacecraft bus, or operational assumption.

- Drafts autosave in the current browser's local storage. They are not uploaded to the API.
- Use **Export JSON** to keep a portable copy and **Import JSON** to restore a version-1 export (maximum file size 1 MB). Import sanitizes unknown fields and rejects unsupported schema versions.
- The requirement matrix records a statement, target/threshold with units, a source URL, and evidence notes.
- A typed source URL is shown as **not fetched or validated**. The app does not silently claim a source proves a requirement.
- The section count measures how many brief fields contain text; it is not a feasibility score, mission-readiness score, or pass/fail assessment.

No orbital propagation, performance simulation, spacecraft sizing, cost estimation, or automatic feasibility result is performed by this workspace.

## Read-only NASA PDS API

A FastAPI backend now exposes a read-only proxy for the official NASA PDS Search API. It preserves the upstream JSON response and records the exact request URL and retrieval timestamp; it does not synthesize fallback records.

Start the backend in one terminal:

```bash
cd backend
python -m venv .venv
# Activate the environment, then:
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Start the frontend in a second terminal from the repository root:

```bash
npm install
npm run dev
```

The frontend proxies `/api` requests to the local FastAPI service. The PDS Search API is not a complete mirror of all archive holdings, so missing search results must be cross-checked against the mission-specific archive index. Available endpoints are `GET /api/v1/pds/search`, `GET /api/v1/pds/products/{identifier}`, `GET /api/v1/pds/products/{identifier}/members?depth=1|2`, `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/label`, `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/pixel?line_index=...&sample_index=...`, `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/profile?line_index=...&start_sample_index=...&sample_count=...`, and `GET /api/v1/pds3/kaguya/lalt/gt-sp/label`. The pixel route validates the live fixed PDS3 label, then requires an exact HTTP 206 response with the expected `Content-Range` and exactly two bytes from the fixed IMG URL. It refuses a server that ignores Range rather than downloading 115 MB for one pixel. Returned height and planetary radius are derived from the original DN using the label's scaling factor and offset. The profile route reads at most 512 contiguous samples from one source row, returns label-derived metres-per-pixel spacing, and plots the un-interpolated GDR heights. Neither endpoint is a terrain tile or a substitute for complete-raster validation.

## Data resources and provenance

See [docs/data-provenance.md](docs/data-provenance.md) for the source list, archive descriptions, and required provenance fields, and [docs/implementation-roadmap.md](docs/implementation-roadmap.md) for the completion gates and current release decision. The initial science-data candidates are LRO products such as LOLA topography, LROC imagery, and Diviner thermal observations, with Kaguya LALT listed as a separately qualified cross-sensor source.

## Planned architecture

- **Web client:** React, TypeScript, Vite.
- **API:** Python and FastAPI read-only PDS discovery proxy; bulk ingestion and server-backed mission workflows remain future work. The current mission brief is saved locally in the user's browser.
- **Persistence:** PostgreSQL after data contracts, authorization, and audit requirements are defined.
- **Data pipeline:** source-specific ingestion, immutable raw products, metadata validation, and traceable derived products.
- **Engineering:** only deterministic, documented calculations using sourced inputs and independent verification cases. Mission simulation is excluded.

## Quality gates

- Unit tests for source catalogues and parsing/derivation logic, plus Playwright browser end-to-end tests for mission brief, NASA PDS search/product resolution, and source-inspection workflows.
- Typecheck and production build.
- Dependency security audit.
- Source attribution, product identifiers, units, reference frames, and retrieval timestamps.
- No secrets committed to the repository.
- No merge to the default branch without maintainer approval.

## Run locally

Requirements: Node.js 22 or later and npm.

```bash
npm install
npm run dev
```

Checks:

```bash
npm test
npx playwright install chromium
npm run test:e2e
npm run build
npm audit --audit-level=high

cd backend
pip install -r requirements.txt
pip-audit -r requirements.txt
pytest -q
```

## Self-hosted website deployment

A Docker Compose deployment is provided in [deploy/README.md](deploy/README.md). It serves the website and private FastAPI service on one origin, with Nginx routing `/api/` requests internally. Review the TLS and network exposure notes before public hosting.

## Separate-host deployment configuration

The web client can call a separately hosted FastAPI service without changing source code:

1. Set `VITE_API_BASE_URL` to the API's HTTPS origin when building the frontend (for example, `https://api.example.com`). Leave it empty for local development; Vite proxies `/api` to `127.0.0.1:8000`.
2. Set backend `ORBITOPS_CORS_ORIGINS` to a comma-separated list of exact frontend origins (for example, `https://orbitops.example.com`). Do not use a wildcard for a public deployment.
3. Configure these values in the hosting provider's environment settings. Do not commit deployment secrets or real credentials.
4. Verify the frontend build, API `/health` endpoint, and live read-only PDS requests on the deployed domains before announcing a public release.

CORS is disabled unless explicit origins are configured. The API currently exposes read-only GET endpoints; this configuration does not add authentication, persistent user accounts, or server-side mission storage.

## Disclaimer

ORBITOPS is an independent educational project, not NASA software and not flight-qualified mission-design software. NASA does not endorse this project. It must not be used for operational spacecraft design, navigation, launch decisions, or flight safety. Non-U.S. Government resources are subject to their own data-use and reuse terms.
