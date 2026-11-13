# Data provenance and source integration plan

## Product rule

ORBITOPS must not fabricate measurements, mission telemetry, orbital states, spacecraft performance, or NASA observations. A value is displayed as a sourced observation only after the underlying product has been retrieved and its metadata parsed. If a value is unavailable, the interface must say **Not available from an integrated source**.

The source catalogue in `src/data/sources.ts` is a list of external references only. It does not mean the project has downloaded, cached, processed, or synchronized the linked datasets.

## Verified source entry points

| Resource | What it can support | Current integration status |
|---|---|---|
| [NASA PDS LRO archive index](https://pds-geosciences.wustl.edu/missions/lro/) | Discovery of LOLA, Diviner, LROC, SPICE and other LRO archives; release metadata | Linked reference only |
| [LOLA archive guide](https://pds-geosciences.wustl.edu/missions/lro/lola.htm) | Lunar topography and elevation product discovery | Linked reference only |
| [NASA LRO data products](https://science.nasa.gov/mission/lro/data-products/) | Official mission data-product entry point, LROC, PDS and QuickMap links | Linked reference only |
| [NASA south-pole shadows](https://science.nasa.gov/resource/shadows-near-the-moons-south-pole/) | Scientific context for polar shadow regions | Static reference only; not a live illumination feed |
| [NASA Mission Visualization](https://nasa.github.io/mission-viz/) | External visualization/learning reference | External link only; not embedded or executed |
| [NASA GMAT catalogue entry](https://software.nasa.gov/software/GSC-19468-1) | Reference to an external mission analysis tool | External link only; not executed by ORBITOPS |
| [JPL Concept Maturity Levels](https://dataverse.jpl.nasa.gov/dataset.xhtml?persistentId=hdl:2014/44299) | Concept maturity reference | External dataset page only |
| [NASA Webb telescope learning game](https://science.nasa.gov/mission/webb/game-build-it-yourself/) | Educational design reference | External link only |
| [Canadian Space Agency digital games](https://www.asc-csa.gc.ca/eng/youth-educators/digital-games-and-activities.asp) | External educational reference | External link only; its own terms apply |

The PDS Geosciences Node describes LOLA as a lunar topography instrument and directs users to the Lunar Orbital Data Explorer for the most recent holdings. It also lists LRO archives by instrument, including Diviner, LOLA, LROC, and SPICE. LROC PDS archive descriptions identify calibrated NAC/WAC data and associated pointing and housekeeping information.

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
2. Select a bounded lunar south-pole region and a specific LOLA product collection; parse its PDS labels before rendering any elevation value.
3. Add selected LROC products with their original pointing/geometry metadata and source citations.
4. Evaluate Diviner products for thermal-context views, keeping the instrument's observation time and processing level visible.
5. Add SPICE kernels only if a later, explicitly approved engineering requirement needs geometry or ephemeris calculations. No orbit propagation or mission simulation is part of the current product scope.
6. Add independent validation cases and compare derived outputs against published product documentation before exposing them as calculated engineering values.

## Data-use and endorsement

NASA does not endorse ORBITOPS and is not responsible for information on non-U.S. Government websites. External non-U.S. Government resources, including the Canadian Space Agency site, remain subject to their own data-use and reuse parameters. The project must review and comply with each source's terms before copying, transforming, or redistributing any content.
