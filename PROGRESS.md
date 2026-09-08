# Implementation Progress

## Current phase

Phase 5 — Keycap Palettes (complete; playable offline prototype)

## Completed functionality

- Created the frontend, backend, test, and local data directory structure.
- Added a typed FastAPI `GET /api/health` endpoint and configurable CORS origin.
- Added a React/Vite shell with local API connection status.
- Added environment examples and ignores for secrets, builds, dependencies, and local data.
- Documented setup, architecture, tests, planned behavior, and initial limitations.
- Added strict Pydantic models for keyboards, keys, cases, features, keycap sets, colors, supported keys, and saved configurations.
- Added matching frontend TypeScript contracts and camelCase API serialization.
- Added validation for URLs, dimensions, quantities, color values, confidence ranges, unique IDs, and timezone-aware timestamps.
- Added canonical ANSI 65% (68-key), ANSI 75% (84-key), and ANSI TKL (87-key) generators.
- Added stable key IDs, legends, keyboard-unit coordinates, standard key widths, stabilizer flags, and logical groups.
- Added typed layout overrides for right Shift width and optional knob, screen, and badge features.
- Added pure frontend geometry functions that convert keyboard units to millimeter scene transforms.
- Added a React Three Fiber keyboard scene with procedural keycaps, case geometry, lighting, shadows, and orbit/zoom controls.
- Added individual click selection, Shift-click multi-selection, and logical group selection.
- Added a five-color fixture keycap palette with immediate local per-key painting.
- Added hovered/selected key feedback plus reset-selected and reset-board controls.

## Tests added

- Backend health response-contract test.
- Frontend connected and offline state smoke tests.
- Backend domain schema and validation tests.
- Backend canonical layout count, spacing, grouping, sizing, and override tests.
- Frontend deterministic geometry transform tests.
- Frontend selection, multi-selection, group selection, painting, reset, fixture, palette, and workbench behavior tests.

## Tests currently passing

- Backend: 27 tests passing.
- Frontend: 24 tests passing.

## Prototype feedback fixes

- Release dependency consolidation is pending `npm install` in frontend: online installation was declined and the offline cache was incomplete. Until the frontend lockfile is regenerated, CI `npm ci` cannot pass with the new release dependencies.

- Configured semantic-release for main pushes after tests/build pass, with Conventional Commit analysis and GitHub tags/release notes. Release tooling shares frontend dependencies and lockfile. Added contributor guidance and release-rule tests. Live release verification requires a GitHub remote.

- Added root install/start helpers for Bash and PowerShell, with dependency checks, service shutdown handling, and README instructions.

- Fixed CI YAML tab indentation, updated Node to 24 for locked Vitest compatibility, and added the frontend build check. Local backend/frontend tests and build pass; hosted CI and actionlint remain unverified (actionlint download declined).

- Added Function row group selection using normalized group metadata; absent groups are disabled in the current prototype.

- Active group buttons toggle selection off; Clear selection also removes individual or multiple selections while preserving painted colors.

- Selected keys now show synchronized yellow pulsing overlays and yellow outlines; the stored palette assignments remain unchanged.

- Removed green emissive selection tint and lighting-driven keycap brightening; keycaps now use unlit palette colors with tone mapping disabled.
- Added independent selection outlines, active group buttons, persistent selection counts, and current color/hex feedback.
- Added a regression test for switching from Alphas to Modifiers and painting only the replacement selection.
- Frontend production build: passing.

## Known limitations

- Product inputs are disabled until ingestion is implemented.
- No compatibility analysis, scraping, AI, image sampling, or persistence yet.
- The production Three.js bundle is functional but currently emits a size warning; code splitting is a later optimization.
- Key legends are represented in data but not drawn on the initial 3D keycaps; hover feedback shows stable key IDs.

## Next implementation target

Implement Phase 6 size-based keycap compatibility checks and display non-blocking warnings.
