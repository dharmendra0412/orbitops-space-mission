# Preview engineering model and limitations

This document defines the visible calculation rules used by the initial website slice. These are transparent game-design assumptions for interface development. They are **not** flight hardware specifications, NASA mission data, a trajectory solution, or a flight-readiness assessment.

## Catalog assumptions

| Item | Mass (kg) | Power (W) | Data (GB/day) | Relative science points |
|---|---:|---:|---:|---:|
| Spacecraft platform baseline | 42.0 | 85 | 0.35 | — |
| Terrain imaging camera | 4.2 | 18 | 1.8 | 18 |
| Near-infrared spectrometer | 7.5 | 32 | 3.6 | 28 |
| Subsurface radar sounder | 11.8 | 48 | 5.2 | 30 |
| Thermal radiometer | 5.1 | 22 | 1.2 | 20 |

All values above are illustrative and exist only to make the first interactive trade-off interface responsive and explainable. They must be replaced or explicitly retained as labelled educational assumptions after a sourced engineering review.

## Current deterministic checks

- **Mass:** platform mass plus selected instrument masses is compared with the selected launch-class capacity (75, 100, or 140 kg). These are generic game capacities, not the performance of named launch vehicles or a guaranteed capacity to the Moon.
- **Power:** platform peak demand plus instrument power is compared with an assumed 180 W generation allowance. This is not a power-system sizing model: it omits solar incidence, eclipses, degradation, battery state of charge, conversion losses, duty cycles, thermal constraints, and transient loads.
- **Daily data:** platform and instrument daily data assumptions are compared with a 24 GB/day educational allowance multiplied by a conceptual orbit preset factor. This is not a communications link budget, ground-contact analysis, or onboard storage model.
- **Budget:** a simplified rule checks whether the selected budget meets a base planning allowance plus instrument-count and launch-class surcharges. It is not a parametric cost estimate or lifecycle cost model.
- **Science score:** selected instruments contribute relative game-design points. They are not measured science return or a peer-reviewed prioritization.

## Orbit presets

The three orbit options are conceptual choices used to demonstrate that mission architecture changes assumptions. The first slice does not propagate an orbit, compute a transfer, model lunar gravity harmonics, calculate illumination, or predict communications contact windows.

## Score

The current score is a relative learning indicator combining science points and the four visible pass/fail checks. It is not a NASA rating, probability of success, technology readiness level, or mission approval.

## Required future verification

Before these values can be represented as engineering estimates, each model needs:
1. Named sources or a documented derivation and uncertainty range.
2. Explicit units, reference frames, epochs, and applicability conditions where relevant.
3. Input validation and dimensional/unit tests.
4. Independent reference cases and regression tests.
5. Model version and assumptions surfaced in the user interface.
6. Clear distinction between measured data, derived values, scenario inputs, and synthetic teaching content.

## Safety and scope

ORBITOPS is an educational concept-design environment. It is not flight-qualified software and must not be used for spacecraft design approval, launch, navigation, operations, or safety-critical decisions.
