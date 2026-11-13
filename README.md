# ORBITOPS — Space Mission Engineering Simulator

**Design. Engineer. Launch. Operate. Discover.**

ORBITOPS is a browser-based educational space-mission design game. Players work individually or in teams of up to four to turn a scientific objective into an engineering-constrained mission concept, validate the design, simulate mission operations, and review the results.

## Product principles

- Engineering decisions must have explicit, traceable consequences.
- Calculations must be deterministic, unit-aware, and testable.
- NASA and partner data must retain source attribution, retrieval metadata, units, coordinate reference, and limitations.
- Synthetic scenarios, if used for teaching, must be clearly labelled as synthetic and never presented as real NASA observations.
- A visual animation is not evidence of a physical simulation. Every displayed result must identify its model and fidelity.
- A failed or infeasible design must explain the violated requirement and the calculation behind it.

## Initial vertical slice

The first release focuses on a lunar polar exploration mission and should deliver one complete browser journey:

1. Review the mission briefing and scientific objectives.
2. Configure a spacecraft and payload.
3. Select a launch and orbit option.
4. Evaluate mass, power, data, communications, and budget constraints.
5. Run a deterministic, explicitly scoped mission scenario.
6. Review requirement verification, performance, and a technical debrief.

## Planned architecture

- **Web client:** React, TypeScript, Vite.
- **3D/geospatial presentation:** Three.js / React Three Fiber, with a geospatial globe only where it adds scientific value.
- **API:** Python and FastAPI.
- **Persistence and collaboration:** PostgreSQL / Supabase, introduced behind explicit authorization and server-side validation.
- **Science and engineering:** isolated, versioned calculation modules with unit-aware inputs and automated verification.
- **Data sources:** NASA/JPL datasets and tools such as SPICE and GMAT where appropriate; each integration must document its actual scope and limitations.

## Engineering quality gates

- Unit and integration tests for calculations and API contracts.
- Frontend lint, typecheck, and production build.
- Reproducible scenario inputs and outputs.
- Data provenance and model-fidelity labels.
- No secrets committed to the repository.
- No merge to the default branch without maintainer approval.

## Run the web preview locally

Requirements: Node.js 20 or later and npm.

```bash
npm install
npm run dev
```

Create a production build with:

```bash
npm run build
npm run preview
```

## Current implementation status

The first web foundation includes a responsive mission workspace, interactive payload selection, conceptual orbit and launch-class presets, a live resource estimate, visible constraint checks, and a preview mission score. The current calculation assumptions and limitations are documented in [docs/preview-model.md](docs/preview-model.md).

This is an initial frontend vertical slice. It does not yet include a backend API, user authentication, persistent mission storage, multiplayer synchronization, NASA data ingestion, validated trajectory propagation, or detailed subsystem simulation.

Changes are developed on feature branches and reviewed through pull requests. Features are not considered complete until their acceptance criteria and tests pass.

## Disclaimer

ORBITOPS is an educational engineering simulator, not NASA software and not flight-qualified mission-design software. It must not be used for operational spacecraft design, navigation, launch decisions, or flight safety.
