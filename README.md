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
- Automated checks for source catalogue integrity and a production build.

The selectable categories are research prompts only. They are not a verified flight-hardware catalogue or a spacecraft configuration. The source catalogue is not an ingestion pipeline; no external datasets are currently downloaded, processed, cached, or synchronized.

## Data resources and provenance

See [docs/data-provenance.md](docs/data-provenance.md) for the source list, archive descriptions, and required provenance fields. The initial science-data candidates are LRO products such as LOLA topography, LROC imagery, and Diviner thermal observations, discovered through NASA's Planetary Data System.

## Planned architecture

- **Web client:** React, TypeScript, Vite.
- **API:** Python and FastAPI, introduced when source ingestion and user workflows are specified.
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
```

## Disclaimer

ORBITOPS is an independent educational project, not NASA software and not flight-qualified mission-design software. NASA does not endorse this project. It must not be used for operational spacecraft design, navigation, launch decisions, or flight safety. Non-U.S. Government resources are subject to their own data-use and reuse terms.
