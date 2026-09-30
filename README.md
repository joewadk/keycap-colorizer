# Keycap Colorizer

The idea is simple: try out keycap color combinations before buying them.

It can be hard to picture how a set of keycaps will look on your keyboard from product photos alone. Maybe you want dark modifiers with lighter letter keys, a different color for the arrows, or just a few accents. This project lets you play with those combinations on a 3D keyboard and see what looks good together.

The goal is to experiment with different board types—like 65%, 75%, and TKL—and find a color scheme that suits your setup.

## What you can try today

Read a keyboard or keycap product link independently, or upload a product photo if a store blocks access. **Try demo keyboard** and **Try demo keycaps** exercise the photo workflow without network access or API credits. Confirm a generic ANSI **65%, 75%, or TKL** layout and preview it immediately—even if the other product fails.

For the case color, choose the right product photo, crop just the housing, sample it, and apply a reviewed color. For keycaps, choose a photo and click **Quick fit colors** to suggest a complete scheme for your active board, then **Apply suggested colors**. The default method uses dominant photo colors for letters, modifiers, and accents. **Match positions** instead samples each key region in a straight-on photo of the same layout; crop once to the outer key edges for this method. Neither method claims automatic key detection or exact color accuracy.

Prefer more control? Switch to **Manual · per-key colors**, or click any key in the suggested map to correct it without losing the other assignments. Select a destination, click its surface in the photo or drag a crop, sample, and assign. **Shared palette** also remains available for group painting. All extracted photo candidates remain selectable—there is no 30-image cutoff. Photos are downloaded only when selected; upload size and safe-decoding limits still apply.

Per-key assignments follow the active board and are saved with the design. Changing the board clears unfinished photo assignments to avoid applying them to the wrong layout. A different photo can be used for each key; choose photos matching the variant you want. Unassigned keys retain matching colors where possible, otherwise use the first reviewed color.

You can also choose a generic board directly, then change the **keyboard case color** using nine common finishes or a custom color picker. Independently, use the Botanical sample keycaps to color individual keys or groups. Rotate the board to see it from different angles, and reset keycap colors whenever you want to start over.

Use **Board size** and **Custom board color** above the preview without product links, an API key, or a running backend. Case-color changes leave keycaps and selection unchanged; the case color follows you between board sizes. Switching sizes clears selection and carries over matching keys to new layouts; returning restores that layout's keycap draft until reload. Save design stores both case color and keycap assignments. Function-row selection is available on 75% and TKL, not the 65% fixture.

These are generic layout previews, not replicas of particular products. Case colors are visual choices, not manufacturer finish specifications; lighting affects their appearance. Keycap fit remains unverified without kit inventory. Other sizes (such as 60% and full-size) are not available yet.

Click a key in the 3D preview, use the expandable individual-key list, or hold Shift to select several. Group buttons let you quickly select the letters, modifiers, arrows, and more. Pick a color to apply it, then click the active group again or use **Clear selection** to see the result without the highlight.

A fit panel can flag missing key sizes or quantities when a kit's inventory is available. The sample palette doesn't include that information yet, so it shows “Fit not verified.” You can still try every color combination.

With the backend running, give your combination a name and click **Save design** below the preview. Use **Load saved designs**, choose one, and click **Restore selected design** to bring its colors back—even after restarting the app. Restore replaces unsaved edits. Designs stay in your local SQLite database; there are no accounts.

## Product-link limits

Product pages vary widely. Playwright or explicitly selected Firecrawl extracts metadata and candidate photo URLs; local Pillow analysis samples colors and proposes a scheme or matches a top-down crop to the canonical layout. Quick fit conservatively excludes uniform connected border backgrounds, but case colors, shadows, and unrelated objects can still appear. It does not automatically detect individual keys or match photo variants. Stores can still block extraction; upload a photo to continue. Keyboards and keycaps are independent, so one failed URL no longer blocks the other. No paid provider is selected automatically. More board layouts are planned.

If the page reports that photo review is unavailable in the running backend, stop and restart the app, then reload. The interface checks backend support to catch stale server processes.

## Run it locally

For Windows PowerShell, use:

```powershell
.\install.ps1
.\start.ps1
```

These require Node.js 24 and standard Windows Python 3.11+. If needed, use `install.ps1 -Python "C:\path\to\python.exe" -Npm "C:\path\to\npm.cmd"`; `start.ps1` accepts `-Node`.

The startup scripts check backend dependencies (including Pillow and SQLite), configuration, Node version, and ports before launching. After pulling new dependencies, rerun the installer if prompted. Startup never installs packages automatically or stops an existing service occupying a port.

To check setup without launching either service, run `./start.ps1 -CheckOnly` in PowerShell or `bash start.sh --check` in Bash. Stop any existing app instance first: both checks require ports 8000 and 5173 to be available. Configuration checks do not create a database or verify AI credentials remotely.

With Node.js 24 and Python 3.11+ installed, run these from the project root in Bash (Linux, macOS, or Git Bash on Windows):

```bash
bash install.sh
bash start.sh
```

Install once, then use `bash start.sh` whenever you want to launch both services. Open [localhost:5173](http://localhost:5173); press Ctrl+C in the terminal to stop them.

The installer defaults to `python3` and `npm`. Override these with environment variables if needed, for example `PYTHON=python bash install.sh`. You can also set `NPM` for installation or `NODE` for startup to an executable path. On Windows, use standard Windows Python rather than MSYS Python.

For the color preview, open a terminal in the project folder and run:

```powershell
cd frontend
npm install
npm run dev
```

Open [localhost:5173](http://localhost:5173) in your browser. The sample keyboard and colors work without an API key or a running backend.

<details>
<summary>Backend setup and development checks</summary>

To start the local backend, open another terminal in the project folder. Use a standard Windows Python installation:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
python -m uvicorn app.main:app --reload
```

The backend runs at [localhost:8000](http://localhost:8000). The page will show when it is connected.

Optional settings are listed in `.env.example`. Keep any API keys in your local `.env` file and never commit them.

Run backend tests from `backend` with the virtual environment active:

```powershell
python -m pytest
```

Run frontend tests and check the production build from `frontend`:

```powershell
npm test
npm run build
```

To try the product-page reader, activate the backend environment and run these from `backend`:

```powershell
python -m playwright install chromium
python -m app.ingestion "https://example.com/product"
```

Replace the example URL with a public keyboard or keycap product page. This prints the page details it can find and caches them under the project's `data/cache/pages` folder. Add `--refresh` to fetch it again or `--images 3` to save up to three candidate images under `data/images`.

The same reader powers the product-link form. Some stores block automated browsers or need extraction rules of their own. Normal unit tests use local HTML fixtures and mocked browser/network calls, so they need no internet, API keys, or Chromium installation. The separate browser acceptance test uses the offline fixtures with Chromium.

You can also try Firecrawl for pages that Playwright struggles with. Add your Firecrawl API key to `.env` in the project root:

```dotenv
FIRECRAWL_API_KEY=your-key-here
SCRAPER_PROVIDER=playwright
```

Then choose it for a scrape:

```powershell
python -m app.ingestion "https://example.com/product" --provider firecrawl
```

Use `--provider playwright` to compare the local scraper, or set `SCRAPER_PROVIDER=firecrawl` to make Firecrawl the default. Each provider has its own local page cache; `--refresh` fetches new data. Firecrawl uses its hosted service and account credits, while Playwright runs locally. There is no automatic paid fallback. Both feed the same product-detail parser, and neither requires an AI key.

The app uses the [Firecrawl scrape API](https://docs.firecrawl.dev/api-reference/endpoint/scrape). The Firecrawl MCP login in Codex is separate; the app needs `FIRECRAWL_API_KEY`. The key stays in backend settings and is not saved in product caches.

Development progress is tracked in [PROGRESS.md](PROGRESS.md).

To sample colors from a downloaded product photo without internet or AI, update backend dependencies (`python -m pip install -e ".[dev]"`) and run from `backend`:

```powershell
python -m app.colors "../data/images/product.png" --crop 0.1 0.2 0.9 0.8 --max-colors 6
```

The crop is left/top/right/bottom as fractions of the oriented image (0–1). Crop around keycap surfaces to exclude the case and background. Without a crop, the whole image is sampled. This is not automatic keycap detection: it filters sharp edges and small details, clusters similar colors, and reports median RGB samples. Confidence is a heuristic, not calibrated accuracy. Small accents may be omitted; dark and light keycaps are retained. Manufacturer codes take priority when supplied; model estimates are only an explicit fallback. The standalone command prints a palette; product intake can use the same sampler when a page does not provide explicit color codes.

The sampler uses [Pillow](https://pillow.readthedocs.io/en/stable/reference/Image.html), checks compressed and decoded size limits, and rejects animations and invalid images. Tests generate deterministic synthetic image fixtures locally.

Local storage defaults to `data/products.db` at the repository root. Set `DATABASE_PATH` to change it; relative paths always resolve from the repository root. Back up the database while the backend is stopped. Reviewed products create immutable revisions, so older designs keep their original products and colors. Ordinary manual imports still reject conflicting IDs/URLs. Schema 1 databases migrate transactionally to schema 2 while preserving saved references. Photos, scraped caches, and databases are local data ignored by Git. Unapplied photo reviews are temporary and expire when the backend restarts.

For manually normalized products, use the typed API at [localhost:8000/docs](http://localhost:8000/docs): `POST /api/products/manual` takes `{ "kind": "keyboard" | "keycaps", "product": ... }`. Product reads are available at `/api/products/{id}`, `/api/keyboards/{id}`, and `/api/keycaps/{id}`. `POST /api/configurations` takes `keyboardId`, `keycapSetId`, `keyColorMap`, and optional `name`; it generates the ID/date and returns the configuration, products, and compatibility result. List with `GET /api/configurations?limit=50&offset=0`; restore with `GET /api/configurations/{id}`. Unknown fit never blocks saving.

Optional product understanding (Phase 8) can classify scraped evidence and identify a supported layout. To enable it, set `AI_PROVIDER=openai`, `OPENAI_API_KEY`, and `OPENAI_MODEL` in your local `.env`. Choose a model that supports [structured outputs](https://developers.openai.com/api/docs/guides/structured-outputs). Then run:

```powershell
python -m app.ingestion "https://example.com/product" --understand
```

This explicitly sends extracted page text and metadata to OpenAI and may incur API charges. Without `--understand`, scraping makes no AI calls. The adapter uses strict structured outputs with local validation, following the official OpenAI documentation. Invalid output is retried once; ambiguous products return `needs_review` with the original evidence. No model-generated coordinates reach the renderer. The browser workflow uses deterministic classification and canonical layout normalization; the optional `--understand` CLI is still separate and repeated invocations currently request a new analysis even when HTML is cached. The offline demo and generic preview remain usable without any provider configured.

To run the fixture-backed browser acceptance test, start the app and then run from the project root:

```powershell
backend\.venv\Scripts\python.exe e2e\offline_workflow.py
```

It verifies photo intake, case-color sampling, per-key photo assignments on a 75% board, arrow painting, save, reload, and restore without contacting a vendor or paid service. Set `E2E_BASE_URL` and the frontend's `KEYCAP_API_TARGET` for isolated test ports.

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions and automatic GitHub releases.

</details>
