# Kaguya LALT / SELENE SPICE source audit

**Audit date:** 2026-11-13  
**Scope:** Public JAXA/DARTS SELENE SPICE archive metadata relevant to the validated `LALT_RD_20080105` daily range product.

## Authoritative archive

- Dataset: [DARTS SELENE SPICE kernels](https://darts.isas.jaxa.jp/en/datasets/darts:sln-l-spice-6-v1.0/)
- Distribution root: [JAXA/DARTS PDS3 archive](https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-spice-6-v1.0/)
- Archive overview: [slnsp_1000/aareadme.htm](https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-spice-6-v1.0/slnsp_1000/aareadme.htm)
- SPK-specific source notes: [data/spk/spkinfo.txt](https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-spice-6-v1.0/slnsp_1000/data/spk/spkinfo.txt)

The DARTS dataset describes SPICE as the source of spacecraft/planet ephemerides, instrument alignments, spacecraft orientation, event timing, and time conversion information. The archive distributes CK, FK, IK, LSK, PCK, SCLK, and SPK kernel families. A valid reconstruction must load a mutually compatible set and prove coverage at each selected observation epoch; the existence of the dataset or a broad mission-level time span is not proof of coverage for an individual record.

## Orbit-kernel selection for 2008-01-05

The archive's `spkinfo.txt` distinguishes the two RISE orbit solutions:

| Kernel | Archive description | LALT crossover involvement | Relevance |
|---|---|---|---|
| `SEL_M_071020_081226_SGMI_05.BSP` | SGM100i orbit; 2007-10-20 00:00 UTC to 2008-12-26 04:30 UTC | The orbit determination explicitly includes LALT laser-altimeter crossovers for January and March 2008 | Do not use as independent LALT validation for the 2008-01-05 observations |
| `SEL_M_071020_090610_SGMH_02.BSP` | SGM100h orbit; 2007-10-20 02:30 UTC to 2009-06-10 19:30 UTC | Archive says the orbit solution used two-way tracking data only | Preferred candidate for a first LALT footprint reconstruction that avoids direct LALT crossover fitting |

The 2008-01-05 day lies within the stated coverage interval of both kernels. This is only a metadata-level coverage check. It does **not** prove SPICE segment coverage at every TI-converted epoch, frame connectivity, attitude availability, or valid instrument pointing.

The SGMH source notes also report orbit-arc boundary jumps and radial overlap errors of at least 3 m, with larger outliers possible. Its orbit solution is therefore not absolute truth and must carry its documented limitations into any comparison.

## Kernel-chain items to resolve before geolocation

The DARTS dataset catalogue lists these relevant kernel families/files:

- SCLK: `SEL_M_V01.TSC` and its detached PDS label.
- CK: monthly/all-mission `SEL_M_{YYYYMM}_[D|S]_V03.BC` files and labels.
- FK: `SEL_V01.TF`, lunar frame association kernels.
- IK: `SEL_LALT_V01.TI`.
- LSK: `naif0009.tls`.
- PCK: `moon_pa_de421_1900-2050.bpc` and `pck00010.tpc`.
- SPK: SGMH candidate above and `de421.bsp`.
- Meta-kernels: `SEL_V01.TM` and `SEL_V02.TM`.

**Version discrepancy requiring resolution:** existing project notes refer to a corrected SCLK N0067, while the published PDS3 SELENE SPICE dataset catalogue names `SEL_M_V01.TSC`. Do not silently substitute one for the other or assume the filename encodes the same version. Inspect the actual detached label, SCLK kernel comments/identity, correlation coefficients, clock ID, and archive checksum/index before selecting the kernel. If N0067 is from a different official source/release, document that provenance and its compatibility explicitly.

The January 2008 CK file must be selected from the official CK information/labels, not inferred solely from the filename pattern. Determine whether the applicable CK is the reconstructed (D) or smoothed (S) attitude solution, inspect its CK object/frame/instrument IDs, and query actual segment coverage at the converted observation epochs. The LALT IK and FK must establish the instrument frame and boresight definition. The PCK/FK/DE421 chain must resolve the intended lunar body-fixed frame and its frame ID.

## Required executable acceptance gates

1. Retrieve the exact source labels and selected kernels from the fixed DARTS archive host; reject redirects and unexpected hosts.
2. Verify each downloaded kernel against the archive's published checksum table where an entry exists. Record algorithm, expected digest, observed digest, byte count, source URL, and retrieval time. Do not call a locally generated digest an upstream checksum.
3. Read kernel metadata/comments and record kernel IDs, frame IDs, instrument IDs, SCLK ID, time system, and coverage.
4. Convert the daily table's TI values using the verified SCLK kernel and LSK; test first, last, and selected interior records. Reject epochs outside SCLK correlation coverage.
5. Query SGMH SPK and candidate January CK coverage at every selected epoch. Reject gaps; do not interpolate across unsupported CK/SPK gaps or orbit-arc discontinuities.
6. Resolve the complete spacecraft-to-LALT-instrument frame transform through FK/IK and CK, and the spacecraft/lunar state through SGMH and DE421/PCK.
7. Reconstruct a small, predeclared sample of LALT range footprints with explicit sign, units, aberration, and reference-frame conventions. Preserve range, orbit, attitude, timing, and instrument uncertainties.
8. Compare against the corresponding daily `LALT_LGT_TS` product and LOLA only as cross-product consistency checks. The SGMH orbit's two-way-only provenance reduces direct LALT crossover circularity but does not create independent absolute geodetic control.
9. Keep terrain visualization disabled until the geodetic review approves the transform, uncertainty budget, source registration, and independent-control strategy.

## Current decision

**No raw LALT footprint or terrain claim is approved by this audit.** The archive metadata narrows the orbit choice and identifies a version discrepancy to investigate. Executable SCLK conversion, exact CK/SPK coverage, frame-chain resolution, and footprint comparison remain open.
