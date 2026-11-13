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

## Verified LOLA south-polar GDR sample

The PDS Geosciences Node's public LOLA GDR archive directory exposes an individual south-polar grid and its detached source label:

- Archive directory: [LOLA GDR polar IMG products](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/).
- Product file: [LDEM_85S_40M.IMG](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.img).
- Source label: [LDEM_85S_40M.LBL](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/img/ldem_85s_40m.lbl).
- LOLA Data Node directory: [MIT LOLA GDR polar IMG archive](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/IMG/), which is linked from the PDS Geosciences LOLA page as the separately maintained LOLA Data Node.
- Alternate product file: [LDEM_85S_40M.IMG at the LOLA Data Node](https://imbrium.mit.edu/DATA/LOLA_GDR/POLAR/IMG/LDEM_85S_40M.IMG). Its directory listing reports the same 115,034,112-byte file size as the PDS Geosciences archive listing. The filename and byte count are cross-source consistency checks, not proof that the downloaded bytes are identical; ORBITOPS must still validate the source label and raster content.
- Directory listing reports the IMG at 115,034,112 bytes and the detached LBL at 4,986 bytes. The source label independently declares 7,584 fixed-length records of 15,168 bytes each; this arithmetic also equals 7,584 × 7,584 × 2 bytes from its image dimensions and 16-bit sample width. This is an internal label-layout consistency check only, not verification of a downloaded raster. The XML label translation is also listed alongside the pair.
- The same archive also publishes [LDEM_85S_40M.JP2](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_85s_40m.jp2) at 24,960,972 bytes with a separate [JP2 label](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/data/lola_gdr/polar/jp2/ldem_85s_40m_jp2.lbl) declaring product version V2.1. Its label identifies it as the compressed counterpart of the uncompressed IMG (whose label declares V2.0). The [archive JP2 format note](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/jp2info.txt) states that LOLA JP2 products use lossless JPEG2000 compression, and documents different JP2 sample byte-order/signedness conventions (MSB ordered, unsigned) from the uncompressed IMG (LSB signed). These are two distinct file encodings: the current IMG row decoder must not be used on JP2 bytes. A future JP2 path must use a conforming JPEG2000 decoder and compare decoded pixels against the uncompressed IMG before being accepted.

The detached label identifies this particular product as **PDS3**, product version **V2.0**, data set **LRO-L-LOLA-4-GDR-V1.0**. It describes a 40 m/pixel polar stereographic grid covering 85°S to 90°S, with 7,584 lines by 7,584 samples, 16-bit little-endian signed integer samples, and a source-reported scaling factor of 0.5 and offset of 1,737,400 m. It names the coordinate system as **MEAN EARTH/POLAR AXIS OF DE421**. These are label metadata values, not measurements calculated by ORBITOPS. The label identifies the image object as `HEIGHT` and describes samples as height relative to a reference radius, while also supplying `SCALING_FACTOR` and `OFFSET`. The GDR-specific SIS example from the same `LRO-L-LOLA-4-GDR-V1.0` dataset family and the PDS Orbital Data Explorer's GDRDEM documentation both define HEIGHT as `DN * SCALING_FACTOR`, with OFFSET added only for PLANETARY_RADIUS. The general FAQ contains a conflicting formula; ORBITOPS documents that discrepancy and follows the GDR-specific definition. The selected image remains unprocessed until its binary raster is retrieved and validated.

**Format distinction:** the registry collection `urn:nasa:pds:lro_lola_rdr:data_gridded::1.0` is a PDS4 collection record, but this selected archive-volume sample's detached `.LBL` declares `PDS_VERSION_ID = "PDS3"`. The repository fixture `backend/tests/fixtures/lola_ldem_85s_40m.lbl` is a transcription of the retrieved source label used to validate the conservative PDS3 metadata parser. The parser preserves source strings and units; it does not decode the 115 MB image, convert pixel values, or claim that the IMG has been downloaded. Do not infer that the PDS4 collection API returns this PDS3 volume file as a PDS4 product.

This sample has now passed the first real-source ingestion gate in GitHub Actions run [43404107983](https://github.com/dharmendra0412/orbitops-space-mission/actions/runs/43404107983). The workflow retrieved the original 115,034,112-byte IMG from the PDS Geosciences archive and its 4,986-byte detached label from the same host. The complete raster validator decoded 57,517,056 signed little-endian samples and found DN extrema -11002 and 14054, exactly matching the downloaded label. The local IMG SHA-256 is `1609e9b860748e0b9952a7239c51b37d3b2a799d35e9fc3c258526711cc1e51d`; the label SHA-256 is `d8105776af7fb79b1862ffa3946d013ec34f4dc6a00b7f6bff22ef8f768a5d3d`. The archive directory did not publish an upstream checksum, so these local digests are provenance fingerprints, not independent source-checksum verification. The IMG, label, and manifest are preserved in the workflow artifact `lola-ldem-85s-40m-source-and-validation` (artifact ID `14026965484`, retained for 30 days). This establishes byte-count, PDS layout, full sample-count, and label-extrema consistency; independent pixel-by-pixel comparison against a separate reference implementation and geodetic validation remain outstanding. Do not expose terrain pixels until those independent checks pass.


### ### Resolved LOLA GDR height and polar-grid conventions

The selected product label declares `IMAGE.NAME = HEIGHT`, `SAMPLE_TYPE = LSB_INTEGER`, `SAMPLE_BITS = 16`, `SCALING_FACTOR = 0.5`, and `OFFSET = 1737400.`. The product-family interpretation is supported by two matching authoritative references:

- The [LOLA RDR/GDR Software Interface Specification, section 5.4](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/document/rdrsis.htm) gives a GDR example in the same `LRO-L-LOLA-4-GDR-V1.0` data set, product version V2.0, with the same `IMAGE.NAME = HEIGHT`, signed 16-bit little-endian samples, scaling factor 0.5, and offset 1737400 m. Its explicit conversion note defines `HEIGHT = DN * SCALING_FACTOR`; it separately defines `PLANETARY_RADIUS = DN * SCALING_FACTOR + OFFSET`. It also states that planetopotential topography requires subtracting a geoid radius.
- The [PDS Orbital Data Explorer GDRDEM reference](https://ode.rsl.wustl.edu/MArs/pagehelp/Content/Missions_Instruments/Lunar%20Reconnaissance%20Orbiter%20(LRO)/LOLA/GDR/GDRDEM.htm) independently repeats the same distinction for LOLA GDRDEM products.
- The [PDS Geosciences Node FAQ](https://pds-geosciences.wustl.edu/missions/lro/lola_faq.htm) gives a generic formula that adds OFFSET to HEIGHT. That statement conflicts with the GDR-specific SIS and GDRDEM documentation above; ORBITOPS records the discrepancy but follows the more specific GDR product definition. OFFSET is not added to HEIGHT.

Accordingly, the documented conversions for this GDR product family are:

- Height/elevation relative to the reference sphere: `HEIGHT_m = DN * 0.5`.
- Planetary radius: `RADIUS_m = DN * 0.5 + 1,737,400`.
- Planetopotential topography is not derivable from this raster alone; it additionally requires a matching geoid-radius model and reference.

The official [DSMAP_POLAR.CAT](https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/lrolol_1xxx/catalog/dsmap_polar.cat) supplies the authoritative polar stereographic equations and pixel-center convention for data set `LRO-L-LOLA-4-GDR-V1.0`. It explicitly defines `I = sample`, `J = line`, `NS = -1` in the southern hemisphere, `X = (I - N/2 - 0.5) * MAP_SCALE`, `Y = (J - N/2 - 0.5) * MAP_SCALE * NS`, `R = sqrt(X^2 + Y^2)`, `LON = atan2(X,Y) * 180/pi`, and `LAT = -90 + 2*atan(0.5*R/1737400) * 180/pi`. The implementation uses the sample displacement for X and the sign-reversed line displacement for Y. Regression tests assert all four quadrants, guarding against swapped axes and incorrect southern-hemisphere orientation. The catalog also records the expected visual convention: longitude 0 extends upward from the south-pole map center and longitude 90 east extends to the right.

The first real-source ingestion and raster-layout validation gate passes. A bounded CLI downloader retrieves the fixed PDS Geosciences IMG, checks the archive-listed byte count, writes atomically, and records the exact source endpoint plus a local SHA-256 fingerprint. The archive listing does not publish an upstream checksum, so the local digest is a provenance fingerprint rather than independent checksum verification. A companion-label fetch step rechecks the IMG's on-disk size and local SHA-256, retrieves the detached PDS3 label from the same archive host, and verifies its product/layout fields and dimensions. The GitHub-hosted retrieval workflow validated all 57,517,056 signed little-endian samples and confirmed the observed DN extrema match the source label. It also retrieved the archived JPEG2000 counterpart and decoded it independently with GDAL's JP2OpenJPEG driver. All 57,517,056 corresponding samples were compared: 28,759,313 differed, the maximum absolute difference was 1 DN, the mean absolute difference was 0.500013648 DN, the RMS difference was 0.707116432 DN, and zero samples exceeded the explicit 1-DN tolerance. The JP2 geotransform was also checked against the 40 m pixel-registered grid and its CRS identifies the 1737.4 km lunar polar stereographic frame. This is an independent decoder/encoding cross-check of the same archived product, not an independent measurement dataset or geodetic ground-truth comparison. A further bounded comparison now samples four 512×512 windows against NASA GSFC PGDA's separately adjusted `LDEM_80S_40MPP_ADJ.TIF` COG, using HTTP range reads and bilinear alignment to the source grid. It records bias, median residual, MAE, RMSE, and 95th/99th-percentile absolute residuals. PGDA describes this as an adjusted LOLA product in the MOON_ME / DE421 frame; because it is derived from LOLA too, this is a cross-product processing/geodetic consistency check, not an independent sensor or absolute ground truth. The comparison report is retained with the source artifact. The IMG, labels, JP2, and provenance manifests are retained in a GitHub Actions artifact, not committed to Git. No terrain pixels or derived topography are exposed by the public UI; independent measurement/reference validation and end-to-end geodetic checks remain required before terrain rendering.

## Live discovery endpoint

The FastAPI service exposes:

- `GET /api/v1/pds/search?keywords=LOLA&limit=10` — forwards a keyword query to the NASA PDS Search API.
- `GET /api/v1/pds/products/{identifier}` — resolves a PDS product LID/LIDVID.
- `GET /api/v1/pds/products/{identifier}/members?depth=1|2&limit=100&search_after=...` — browses a page of child collections/products and supports source-defined cursor pagination.
- `GET /api/v1/pds3/lola/gdr/ldem-85s-40m/label` — retrieves one fixed public PDS Geosciences Node label and parses allowlisted PDS3 metadata fields.

The search request asks for the `application/kvp+json` representation and the documented summary fields `lidvid` and `title`. Hierarchy pages are limited to 100 records per request and sorted by the PDS harvest timestamp; the next-page cursor is exposed only when the last returned source record supplies that field. The search endpoint returns the upstream JSON unchanged under `response`, plus the exact request URL, search parameters, and retrieval timestamp. Product resolution requests `application/vnd.nasa.pds.pds4+json` so the response can include the full PDS4 label translation and registry metadata (including file references and checksums when supplied by PDS). Hierarchy browsing uses `application/json` and preserves the returned child-product records. It does not download the linked product files, invent a result when the API returns none, or claim that all PDS archives are indexed. A successful metadata search is discovery only, not dataset ingestion.

The fixed LOLA label endpoint refuses redirects, limits the response to 1 MB, requires ASCII text, and uses a static archive URL rather than accepting a caller-supplied URL. It returns raw metadata strings and units; no pixel decoding, unit conversion, elevation calculation, or IMG download occurs.

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
