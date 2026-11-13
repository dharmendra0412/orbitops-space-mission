# ORBITOPS implementation roadmap

## Product contract

ORBITOPS is being built as an evidence-first lunar mission-planning and science workspace. It must not present fabricated spacecraft specifications, telemetry, mission costs, orbital states, illumination predictions, communications windows, terrain values, or simulated mission outcomes as real.

Every numerical source-derived value must carry its source product, source URL, retrieval time, units, coordinate reference, and applicable uncertainty/validation scope. Missing or unverified inputs remain unavailable. User-entered design assumptions must be labelled as user-supplied and must never be silently promoted to verified facts.

## Completed engineering foundations

- React/TypeScript workspace and read-only FastAPI PDS discovery integration.
- NASA PDS search, product resolution, and bounded hierarchy browsing.
- Fixed LOLA GDR PDS3 label retrieval and conservative metadata parsing.
- Full-raster validation of the fixed 7,584 × 7,584 signed 16-bit little-endian LOLA product against the detached label.
- All 57,517,056 samples decoded; raster extrema match the PDS label.
- Complete IMG-versus-JPEG2000 comparison: maximum difference 1 DN, zero samples beyond the 1-DN gate.
- Eight-point PROJ transformation cross-check against the PDS DSMAP_POLAR pixel-center equations.
- Fixed-source HTTP Range pixel reads and bounded row-profile reads, both using the same PdsClient methods as the live API.
- Live UI for source-label-derived LOLA coordinates, actual raw DN/height/radius lookup, and un-interpolated row-profile plots.
- Fixed-source JAXA DARTS Kaguya LALT PDS3 label endpoint with strict product-layout validation and an explicit interpolated-grid caveat. A live pixel endpoint is blocked because DARTS did not honor HTTP Range for a four-byte sample request; the UI therefore exposes label metadata only.
- Fixed-day Kaguya LALT calibrated range ingestion for `LALT_RD_20080105`: exact PDS3 label/table byte and record layout, all 12,002 records, 11-column schema, finite numeric fields, strictly increasing onboard TI tags, and local SHA-256 provenance. TI-to-ET conversion and raw-range geolocation are not yet implemented.
- Identified the official Kaguya SPICE reconstruction chain (corrected SCLK N0067, January 2008 2-second CK V03, SELENE FK/IK, DE421 lunar ME frame/PCK, and SGMH two-way-tracking SPK candidate). This is provenance research only; no footprint or geolocation is yet claimed.
- Real-source Kaguya LALT south-polar grid download and 7.37 million-cell cross-product comparison against LOLA; this is a consistency check, not independent geodetic ground truth.
- A user-authored mission brief builder with browser-local autosave, JSON import/export, and a requirement matrix for statements, target/units, source URLs, and evidence notes. Source links are explicitly marked as not independently validated.
- API and web tests, Playwright browser tests for mission-brief persistence/import/export, LALT label-only metadata, LOLA label/pixel/profile inspection, NASA PDS search/product resolution, hierarchy browsing with deduplicated pagination, and explicit upstream-failure handling; dependency audits, typechecks, production builds, and data-provenance documentation.

The source-validation workflow passed in [run #43416474484](https://github.com/dharmendra0412/orbitops-space-mission/actions/runs/43416474484); retained evidence is in [artifact #14031861899](https://github.com/dharmendra0412/orbitops-space-mission/actions/runs/43416474484/artifacts/14031861899).

## Remaining milestones

### 1. Independent geodetic and cross-sensor validation

- Resolve the exact daily LALT_LGT_TS product and orbit file/version corresponding to the validated 2008-01-05 raw range day; do not assume the example SGM100g kernel is equivalent to the archived SGMH candidate.
- Find a source-supported bounded access path or a reviewed persistent-cache deployment design before exposing LALT grid pixels; do not download the 64.9 MB image for each user click.
- Convert the LALT `TI` clock tags to ET with the corrected SCLK kernel, verify SPK/CK coverage and frame IDs for every selected record, and reconstruct a bounded sample of raw LALT footprints using the SGMH two-way-tracking orbit candidate.
- Compare reconstructed footprints/ranges with the published LALT_LGT_TS product and the LOLA source while preserving orbit, attitude, instrument, and measurement uncertainty; do not treat the SGMH solution as independent absolute ground truth.
- Record coverage, datum, frame, spatial resolution, and uncertainty before comparing elevations.
- Treat LROC NAC and Kaguya Terrain Camera products tied to LOLA as cross-sensor morphology checks, not independent absolute geodetic control.
- Do not claim independent ground truth until the orbit/frame provenance is demonstrated.

### 2. Bounded raster windows and terrain products

- Design a strict window API with fixed source origin, maximum pixel dimensions, exact Content-Range validation, bounded response size, and provenance.
- Validate row/column registration, no-data handling, units, and projection metadata.
- Only expose a raster preview after the geodetic gate is satisfied; clearly distinguish raw source pixels from any resampling or derived visualization.
- Keep 3D terrain, slope, illumination, and hazard products disabled until their inputs and uncertainty are verified.

### 3. Mission-planning workspace

- Initial user-authored mission brief builder is implemented: objective, target, duration, orbit concept, payload needs, spacecraft constraints, operations concept, and evidence/assumptions.
- Drafts autosave in the current browser and can be exported as JSON; no mission data is silently pre-filled or uploaded.
- Add automated source resolution and verification for requirement evidence; the current matrix stores user-entered URLs but does not fetch or validate them.
- Add explicit distinction between verified inputs, user assumptions, and unresolved values throughout the mission brief.
- Do not calculate orbital trajectories, spacecraft performance, cost, power, or data volume without validated inputs and a reviewed method.
- Do not add fictional telemetry, spacecraft models, or mission results to make the interface appear complete.

### 4. Product hardening and release

- Extend browser-level end-to-end tests to cover empty archive responses, malformed upstream payloads, timeout/rate-limit handling, and retry behaviour. The current Playwright suite now covers mission-brief persistence/import/export, LALT label-only metadata, LOLA label/pixel/profile inspection, NASA PDS search/product resolution, hierarchy browsing, deduplicated pagination, and explicit 503 upstream failures.
- Test upstream timeouts, rate limits, malformed responses, redirects, range rejection, and source unavailability.
- Review accessibility, responsive layouts, API limits, observability, deployment configuration, and security controls.
- Complete human review and release checklist before merging the draft PR.

## Current release decision

**Not complete; do not merge.** The data-ingestion foundation and bounded LOLA inspection tools are validated, but independent geodetic characterization, broader mission-planning workflows, raster-window products, end-to-end coverage, and release hardening remain open.
