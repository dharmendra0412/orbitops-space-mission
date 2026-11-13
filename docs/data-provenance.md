# Data provenance and source integration plan

## Product rule

ORBITOPS must not fabricate measurements, mission telemetry, orbital states, spacecraft performance, or NASA observations. A value is displayed as a sourced observation only after the underlying product has been retrieved and its metadata parsed. If a value is unavailable, the interface must say **Not available from an integrated source**.

The source catalogue in `src/data/sources.ts` is a list of external references only. The FastAPI backend now provides read-only PDS metadata search, product resolution, and hierarchy browsing. This does not mean the project has downloaded, cached, processed, or synchronized any observation data files. The PDS API documentation warns that its servers are not fully populated with all PDS datasets, so API search results must be cross-checked against the mission-specific archive index and direct archive holdings.

## Verified source entry points

| Resource | What it can support | Current integration status |
|---|---|---|
| [NASA PDS LRO archive index](https://pds-geosciences.wustl.edu/missions/lro/) | Discovery of LOLA, Diviner, LROC, SPICE and other LRO archives; release metadata | Linked reference only |
| [LOLA archive guide](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Lunar topography and elevation product discovery | Linked reference only |
| [LRO Release 67 summary](https://pds.nasa.gov/datasearch/subscription-service/SS-20260915.shtml) | Release note listing LOLA and Diviner deliveries | Release reference only |
| [LOLA RDR bundle](https://doi.org/10.17189/tnyt-7007) | Calibrated and derived LOLA archive bundle | Archive link only |
| [LOLA RDR Gridded collection](https://pds.nasa.gov/ds-view/pds/viewCollection.jsp?identifier=urn%3Anasa%3Apds%3Alro_lola_rdr%3Adata_gridded&version=1.0) | Specific PDS4 collection for gridded LOLA data | Collection link only |
| [NASA LRO data products](https://science.nasa.gov/mission/lro/data-products/) | Official mission data-product entry point, LROC, PDS and QuickMap links | Linked reference only |
| [NASA PDS Search API](https://nasa-pds.github.io/pds-api/) | Programmatic discovery of PDS4 products | Documentation link only |
| [LOLA product FAQ](https://pds-geosciences.wustl.edu/missions/lro/lola_faq.htm) | EDR/RDR/GDR product selection and data format guidance | Documentation link only |
| [LROC calibrated archive](https://doi.org/10.17189/bx7p-0d06) | Calibrated NAC/WAC data with pointing and housekeeping information | Archive link only |
| [Diviner archive documentation](https://pds-geosciences.wustl.edu/lro/urn-nasa-pds-lro_diviner_derived1/document/) | Diviner derived-product documentation and SIS | Documentation link only |
| [NASA south-pole shadows](https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/) | Scientific context for polar shadow regions | Static reference only; not a live illumination feed |
| [NASA Mission Visualization](https://nasa.github.io/mission-viz/) | External visualization/learning reference | External link only; not embedded or executed |
| [NASA GMAT catalogue entry](https://software.nasa.gov/software/GSC-19468-1) | Reference to an external mission analysis tool | External link only; not executed by ORBITOPS |
| [JPL Concept Maturity Levels](https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299) | Concept maturity reference | External dataset page only |
| [NASA Webb telescope learning game](https://science.nasa.gov/mission/webb/game-build-it-yourself/) | Educational design reference | External link only |
| [Canadian Space Agency digital games](https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp) | External educational reference | External link only; its own terms apply |

The PDS Geosciences Node describes LOLA as a lunar topography instrument and directs users to the Lunar Orbital Data Explorer for the most recent holdings. It also lists LRO archives by instrument, including Diviner, LOLA, LROC, and SPICE. LOLA documentation distinguishes gridded GDR maps from individual RDR altimetry tracks. For scaled GDR image products, the scaling factor and offset are specified in each PDS label and must be read from that label rather than copied as global constants. LROC PDS archive descriptions identify calibrated NAC/WAC data and associated pointing and housekeeping information.

## Selected LOLA collection scope

The NASA PDS catalogue currently exposes two useful but different LOLA RDR collections:

- **Gridded collection** — LIDVID `urn:nasa:pds:lro_lola_rdr:data_gridded::1.0`. The PDS collection page describes it as a derived gridded-data collection. A PDS catalogue search snapshot indexed 16 October 2026 reported 561 collection members.
- **Calibrated collection** — LIDVID `urn:nasa:pds:lro_lola_rdr:data_calibrated::17.0`. The PDS catalogue snapshot indexed 16 October 2026 reported version 17.0, updated for LRO Release 67, and 75,626 collection members.

These counts and versions are catalogue snapshots, not live counters embedded in ORBITOPS. The gridded collection is the bounded starting point for understanding map-oriented products; the much larger calibrated collection should be sampled by a documented query rather than bulk-downloaded. Always resolve the current product label and collection membership from PDS before ingesting.

## Live discovery endpoint

The FastAPI service exposes:

- `GET /api/v1/pds/search?keywords=LOLA&limit=10` — forwards a keyword query to the NASA PDS Search API.
- `GET /api/v1/pds/products/{identifier}` — resolves a PDS product LID/LIDVID.
- `GET /api/v1/pds/products/{identifier}/members?depth=1|2&limit=100&search_after=...` — browses a page of child collections/products and supports source-defined cursor pagination.

The search request asks for the `application/kvp+json` representation and the documented summary fields `lidvid` and `title`. Hierarchy pages are limited to 100 records per request and sorted by the PDS harvest timestamp; the next-page cursor is exposed only when the last returned source record supplies that field. The search endpoint returns the upstream JSON unchanged under `response`, plus the exact request URL, search parameters, and retrieval timestamp. Product resolution requests `application/vnd.nasa.pds.pds4+json` so the response can include the full PDS4 label translation and registry metadata (including file references and checksums when supplied by PDS). Hierarchy browsing uses `application/json` and preserves the returned child-product records. It does not download the linked product files, invent a result when the API returns none, or claim that all PDS archives are indexed. A successful metadata search is discovery only, not dataset ingestion.

## Integration requirements

Every imported product must preserve:

- Source agency, archive/node, dataset and collection identifier.
- Original product URL and persistent identifier/DOI where provided.
- Product version, release number, processing level, and retrieval timestamp.
- Observation/acquisition time and coverage interval.
- Original units, coordinate system/reference frame, datum, and time system.
- Instrument, target, geometry and quality flags where supplied.
- Original label/metadata files and checksum for downloaded files.
- Citation and applicable license/data-use statement.
- Transformation history: software/version, parameters, and output checksum.

Raw source files must remain distinguishable from derived products. Derived values must link back to their input product identifiers and transformation record.

## Planned data integration sequence

1. Implement an archive metadata catalogue and ingestion manifest; do not download bulk data before selecting specific product collections and coverage.
2. Start with the published LOLA RDR bundle (LIDVID `urn:nasa:pds:lro_lola_rdr::1.0`) and its gridded collection (LIDVID `urn:nasa:pds:lro_lola_rdr:data_gridded::1.0`). The PDS catalogue snapshot reports 561 gridded collection members; use that collection for a small, bounded sample. Keep the Release 67 calibrated collection (LIDVID `urn:nasa:pds:lro_lola_rdr:data_calibrated::17.0`, snapshot count 75,626) as a separate, larger source. Use the PDS Search API to resolve/search metadata, then cross-check against the direct LRO/LOLA archive because the Search API may not contain every holding. Parse the selected product's PDS label before rendering any elevation value.
3. Add selected LROC products with their original pointing/geometry metadata and source citations.
4. Evaluate Diviner products for thermal-context views, keeping the instrument's observation time and processing level visible.
5. Add SPICE kernels only if a later, explicitly approved engineering requirement needs geometry or ephemeris calculations. No orbit propagation or mission simulation is part of the current product scope.
6. Add independent validation cases and compare derived outputs against published product documentation before exposing them as calculated engineering values.

## Data-use and endorsement

NASA does not endorse ORBITOPS and is not responsible for information on non-U.S. Government websites. External non-U.S. Government resources, including the Canadian Space Agency site, remain subject to their own data-use and reuse parameters. The project must review and comply with each source's terms before copying, transforming, or redistributing any content.
