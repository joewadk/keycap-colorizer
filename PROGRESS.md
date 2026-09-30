# Implementation Progress

## Current phase

Phase 12 — Photo review and layout-aware per-key picking (implemented; live-vendor reliability remains best-effort)

## Completed functionality

- Quick select is now the default photo mode: dominant-color scheme fitting for any photo, or position matching for a top-down same-layout crop. Both produce a full per-key draft, preserve image provenance, and allow manual corrections before applying. Uniform connected border backgrounds are conservatively excluded; this is not automatic key detection or calibrated color measurement.
- Removed the 30-candidate parser cap and 40-photo upload cap. Every extracted unique candidate remains selectable with lazy bounded downloads. Older truncated evidence is expanded from locally retained HTML without a paid re-fetch.
- Independent keyboard/keycap photo reviews replace the all-or-nothing intake UI. Users can preview a layout immediately, choose candidate photos, upload local photos, crop case/keycap surfaces, and confirm sampled colors. Backend version checks identify stale servers.
- Per-key photo mode uses the active 65%/75%/TKL geometry, including the 75% function row. Click or crop a surface, sample, assign to a destination key, and apply the reviewed map. Separate crops/photos per key, clear controls, board-change invalidation, and server-side layout/sample validation protect assignments. Shared-palette/group painting remains available.
- Reviewed products now create immutable revisions. Schema 1→2 migration retains saved configurations and foreign keys. Case colors and per-key maps survive save/reload/restore; sources and crops are retained as evidence.
- Intake troubleshooting: reader choice now survives reloads in the same tab; loading progress and failures identify the reader, product kind, and host. Verified the cached Keychron Q1 evidence classifies as a keyboard and normalizes to 75%/84 keys. The reported subsequent failure used Playwright and stopped before Amazon; live Amazon intake remains unverified. Targeted checks: 12 workflow tests and 4 intake UI tests passed.
- Phase 11 connects the two URL fields to an asynchronous ingestion workflow with ordered progress events and explicit complete, needs-review, and failed states. Playwright and explicitly selected Firecrawl pages feed the same evidence parser.
- Normalized products are looked up by canonical URL before scraping. Keyboard facts are restricted to canonical ANSI 65%/75%/TKL templates; ambiguous or unsupported layouts retain evidence for review rather than accepting generated geometry.
- Keycap intake prefers explicit manufacturer hex codes and otherwise uses the bounded local image sampler. Both normalized products and raw evidence are stored locally, followed by compatibility checking and direct loading into the existing workbench.
- Added a zero-network fixture catalog and enabled the full intake UI, including provider choice, progress history, review evidence, retry-safe failures, and cache feedback. Existing workbench state is preserved unless an intake completes successfully.
- Added an accessible individual-key selector and a fixture-backed Chromium acceptance test covering ingestion, Escape painting, arrow painting, save, reload, restore, and assignment verification. GitHub Actions now gates releases on this browser workflow.
- Phase 10.5 corrected to user intent: offline 65%/75%/TKL board selection plus nine common keyboard housing colors and a custom color picker. Removed the common-keycap-palette selector. Existing keycap painting remains independent.
- Board-size switching clears selection and preserves per-board keycap drafts; case-color changes preserve paint and selection. Optional validated `caseColor` is saved on the configuration, not the immutable keyboard product. Older configurations fall back to the product case color. Old fixture IDs/data remain unchanged.
- Added named swatches, function-row availability tests, frontend/backend canonical snapshot parity tests, preset save/restore tests, and corrected the 75%/TKL function-row right-edge alignment. Existing saved layouts are not rewritten.
- Phase 10: added SQLite repositories with schema versioning, immutable normalized products/palettes/URLs/evidence, normalized-URL lookup, saved configurations, and stored compatibility results. Connections are scoped per operation and writes are transactional.
- Added typed manual product import/read and configuration save/list/restore APIs, key/color/product-type validation, and clean missing/conflict/database-error responses.
- Added Save design, Load saved designs, and Restore controls to the preview. Snapshots survive restarts; offline failures preserve painting and current unsaved colors. Imported product conflicts cannot silently alter saved designs.
- Phase 9 gate passed before beginning persistence: 153 backend tests, 34 frontend tests, and production build.
- Added a bounded Pillow decoder, explicit fractional crops, deterministic flat-surface filtering/clustering/median colors, and a local `python -m app.colors` CLI.
- Added approximate-color warnings, heuristic confidence, stable sample IDs, and manufacturer/image/model-fallback provenance precedence. Synthetic image tests cover dark/light colors, narrow legends, backgrounds, transparency, corruption, limits, repeatability, and CLI behavior.
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

- Backend: 215 tests, including quick fitting, photo catalogs beyond 30/40, cache recovery, per-key validation, and schema migration preservation.
- Frontend: 59 tests, including quick fit with manual corrections, independent reviews, layout-aware per-key picking, stale-backend feedback, and save/restore.
- Release: 5 tests passing.

## Prototype feedback fixes

- Fixed Windows PowerShell job monitoring treating Uvicorn's normal stderr INFO logs as terminating errors. Job output is displayed as text; stopped/failed job state still stops the launcher. A real native-process regression test covers healthy stderr followed by exit code 7.
- Updated both startup scripts with read-only dependency/configuration/port checks, Node 24 validation, actionable reinstall messages, and check-only modes. Verified preflight in Windows PowerShell 5, PowerShell 7, and Git Bash; no services launched during those checks.
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

- Board presets cover only generic ANSI 65%, 75%, and TKL. Case colors are visual choices, not manufacturer finish specifications. In-session drafts are not persisted unless explicitly saved.
- Live vendor extraction remains best-effort. Stores may block automation or omit supported layout/color evidence; those cases fail or require review. Optional AI understanding remains a separate CLI and never supplies geometry.
- Normalized URL caching is active in the browser workflow, while standalone scraping/AI CLIs retain their own page-cache behavior. Photo confirmations create immutable product revisions; forced live-page refresh is not exposed. The UI shows at most the latest 50 designs (the API supports pagination).
- Image sampling is a crop/flat-pixel heuristic, not keycap detection or color calibration; backgrounds can be included and accents below 2% of retained pixels can be omitted. The palette selector accepts explicit manufacturer/model colors but does not infer these from names or make AI calls.
- Live AI integration has not been exercised; tests mock all provider calls. Set a structured-output-capable OPENAI_MODEL explicitly. Each `--understand` invocation currently requests analysis again; normalized-product/analysis caching is deferred to persistence/workflow integration.
- Live browser scraping requires `python -m playwright install chromium`. Browser lifecycle and downloads are mocked in the normal tests; no live vendor website verification has been performed.
- Generic extraction may include unrelated image/variant candidates and misses stylesheet-controlled visibility. Blocked pages, logins, and CAPTCHAs surface failures; no bypass is attempted.
- Sample palette inventory is unspecified, so its fit is unknown. Checks assess supplied inventory only; stem fit and row profile are not verified. Vertical keys need height evidence absent from the initial SupportedKey model.
- The production Three.js bundle is functional but currently emits a size warning; code splitting is a later optimization.
- Key legends are represented in data but not drawn on the initial 3D keycaps; hover feedback shows stable key IDs.

## Next implementation target

Continue Phase 12 with live-vendor reliability and deliberate canonical layout expansion. Photo review and immutable revisions are implemented; automatic photo-key detection, perspective alignment, variant binding, calibrated colors, and forced page refresh are not. Keep paid/AI providers opt-in and retain the offline photo acceptance workflow.
