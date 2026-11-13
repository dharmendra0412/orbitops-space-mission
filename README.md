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
- A fixed-source Kaguya LALT PDS3 label and single-grid-node lookup. Each node request reads exactly four bytes, validates the source label and HTTP Range response, and marks the product as a spherical-interpolation grid rather than raw laser shots.
- A user-authored mission brief builder with browser-local autosave, JSON import/export, and a requirement traceability matrix. Source links remain unverified until separately checked.
- Automated frontend and backend tests, dependency audits, and production builds.

The selectable categories are research prompts only. They are not a verified flight-hardware catalogue or a spacecraft configuration. The source catalogue is not an ingestion pipeline. The source-validation workflow downloads and validates the fixed LOLA sample product and the Kaguya LALT south-polar PDS3 grid for repeatable engineering and cross-sensor consistency checks. The live application does not bulk-download, cache, or synchronize observation files; pixel and row-profile endpoints request only bounded byte ranges from fixed PDS rasters. The Kaguya LALT grid sample endpoint is separately labelled as interpolated cross-sensor evidence, not independent geodetic truth.

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

The frontend proxies `/api` requests to the local FastAPI service. The PDS Search API is not a complete mirror of all archive holdings, so missing search results must be cross-checked against the mission-specific archive index. Available endpoints are `GET /api/v1/pds/search`, `GET /api/v1/pds/products/{identifier}`, `GET /api/v1/pds/products/{identifier}/members?depth=1|2`, `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/label`, and `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/pixel?line_index=...&sample_index=...`, and `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/profile?line_index=...&start_sample_index=...&sample_count=...`. The pixel route validates the live fixed PDS3 label, then requires an exact HTTP 206 response with the expected `Content-Range` and exactly two bytes from the fixed IMG URL. It refuses a server that ignores Range rather than downloading 115 MB for one pixel. Returned height and planetary radius are derived from the original DN using the label's scaling factor and offset. The profile route reads at most 512 contiguous samples from one source row, returns label-derived metres-per-pixel spacing, and plots the un-interpolated GDR heights. Neither endpoint is a terrain tile or a substitute for complete-raster validation.

## Data resources and provenance

See [docs/data-provenance.md](docs/data-provenance.md) for the source list, archive descriptions, and required provenance fields, and [docs/implementation-roadmap.md](docs/implementation-roadmap.md) for the completion gates and current release decision. The initial science-data candidates are LRO products such as LOLA topography, LROC imagery, and Diviner thermal observations, with Kaguya LALT listed as a separately qualified cross-sensor source.

## Planned architecture

- **Web client:** React, TypeScript, Vite.
- **API:** Python and FastAPI read-only PDS discovery proxy; bulk ingestion and server-backed mission workflows remain future work. The current mission brief is saved locally in the user's browser.
- **Persistence:** PostgreSQL after data contracts, authorization, and audit requirements are defined.
- **Data pipeline:** source-specific ingestion, immutable raw products, metadata validation, and traceable derived products.
- **Engineering:** only deterministic, documented calculations using sourced inputs and independent verification cases. Mission simulation is excluded.

## Quality gates

- Unit tests for source catalogues and any future parsing/derivation logic.
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
npm run build
npm audit --audit-level=high

cd backend
pip install -r requirements.txt
pip-audit -r requirements.txt
pytest -q
```

## Disclaimer

ORBITOPS is an independent educational project, not NASA software and not flight-qualified mission-design software. NASA does not endorse this project. It must not be used for operational spacecraft design, navigation, launch decisions, or flight safety. Non-U.S. Government resources are subject to their own data-use and reuse terms.
