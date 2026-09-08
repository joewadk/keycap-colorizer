# Implementation Progress

## Current phase

Phase 8 — Agentic Product Understanding (complete; mocked-provider tested)

## Completed functionality

- Added a provider-independent structured-model interface and optional OpenAI Responses adapter; keys stay server-side and AI is opt-in through `--understand`.
- Added strictly validated product classification, supported layout identification, confidence, nullable features, and color names. Models cannot provide geometry or claim RGB color accuracy.
- Added one corrected retry for malformed model data, bounded input/output, timeout/refusal handling, and evidence-preserving disabled/failed/manual-review results.
- Added `/api/capabilities` and an AI configuration status in the intake panel. The offline sample remains usable without an AI provider.
- Corrected Firecrawl's stale 5 MB error message to match its existing 20 MB HTML limit.
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
- Added deterministic size/legend matching with quantity allocation and explicit compatible, incompatible, and unknown results.
- Added typed POST /api/compatibility/check and a workbench fit panel with missing-key details, incomplete-data warnings, and retry on backend errors. Painting remains available.
- Added generic extraction of title, description, nested Product JSON-LD, variants, specifications, and deduplicated image candidates.
- Added bounded Playwright loading, public URL checks, polite sequential intake, local HTML/evidence caching, and optional bounded raster image downloads.
- Added CLI intake with refresh support, one-day page-cache expiry, corrupt-cache recovery, and concurrency deduplication.

## Tests added

- Backend health response-contract test.
- Frontend connected and offline state smoke tests.
- Backend domain schema and validation tests.
- Backend canonical layout count, spacing, grouping, sizing, and override tests.
- Frontend deterministic geometry transform tests.
- Frontend selection, multi-selection, group selection, painting, reset, fixture, palette, and workbench behavior tests.
- Backend compatibility tests for all templates, critical key sizes, quantities, unknown inventory, vertical numpad keys, and API contracts.
- Frontend fit-panel tests for success, warnings, unknown data, retry, cancellation, and painting despite missing keys.

## Tests currently passing

- Backend: 127 tests passing (34 new Phase 8 cases, including strict parsing, retries, review states, provider HTTP contracts, and secret-free capabilities).
- Frontend: 34 tests passing (including AI configuration and offline status).
- Release: 5 tests passing.

## Prototype feedback fixes

- Added optional Firecrawl v2 raw-HTML loading alongside Playwright, CLI/environment provider selection, per-provider caches, validated responses, bounded downloads, and masked backend credentials. Project-root .env is loaded consistently. No automatic paid fallback or live paid request was made; provider tests use mocked HTTP.

- Corrected compact-layout Right Alt to 1u so the bottom arrow row aligns with the navigation column; added frontend and backend alignment regression tests.

- Expanded generated release notes with feature/fix sections, commit-body descriptions, and commit links; release rendering tests cover feature details and breaking-change notes.

- Fixed release-note generation by using Conventional Commits preset 9 with the release-notes generator's writer 8 dependency. All 5 release tests pass, including rendering first-release notes with features, fixes, and breaking changes.

- Release dependency consolidation is complete; frontend manifest and lockfile are synchronized.

- Configured semantic-release for master pushes after tests/build pass, with Conventional Commit analysis and GitHub tags/release notes. Release tooling shares frontend dependencies and lockfile. Added contributor guidance and release-rule tests.

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
- Optional AI understanding is available through the CLI, but image sampling, SQLite persistence, and the full URL-to-preview workflow are not implemented yet. Understanding returns validated facts, not normalized geometry.
- Live AI integration has not been exercised; tests mock all provider calls. Set a structured-output-capable OPENAI_MODEL explicitly. Each `--understand` invocation currently requests analysis again; normalized-product/analysis caching is deferred to persistence/workflow integration.
- Live browser scraping requires `python -m playwright install chromium`. Browser lifecycle and downloads are mocked in the normal tests; no live vendor website verification has been performed.
- Generic extraction may include unrelated image/variant candidates and misses stylesheet-controlled visibility. Blocked pages, logins, and CAPTCHAs surface failures; no bypass is attempted.
- Sample palette inventory is unspecified, so its fit is unknown. Checks assess supplied inventory only; stem fit and row profile are not verified. Vertical keys need height evidence absent from the initial SupportedKey model.
- The production Three.js bundle is functional but currently emits a size warning; code splitting is a later optimization.
- Key legends are represented in data but not drawn on the initial 3D keycaps; hover feedback shows stable key IDs.

## Next implementation target

Phase 9: deterministic image-based palette sampling with image fixtures, confidence, and explicit approximate-color labeling. Then Phase 10 persistence and Phase 11 URL-to-preview/save/restore integration.
