# Keycap Colorizer

The idea is simple: try out keycap color combinations before buying them.

It can be hard to picture how a set of keycaps will look on your keyboard from product photos alone. Maybe you want dark modifiers with lighter letter keys, a different color for the arrows, or just a few accents. This project lets you play with those combinations on a 3D keyboard and see what looks good together.

The goal is to experiment with different board types—like 65%, 75%, and TKL—and find a color scheme that suits your setup.

## What you can try today

The current prototype has a 65% keyboard and a small sample palette. You can color individual keys or whole groups, rotate the board to see it from different angles, and reset your colors whenever you want to start over.

Click a key to select it, or hold Shift to select several. Group buttons let you quickly select the letters, modifiers, arrows, and more. Pick a color to apply it, then click the active group again or use **Clear selection** to see the result without the highlight.

## Where it's headed

Eventually, you'll be able to paste links to a keyboard and a keycap set and preview combinations using those products. More board layouts, saved designs, and warnings about keycaps that don't fit are planned.

For now, it's a place to experiment with colors. Product links and saving aren't available yet.

## Run it locally

For Windows PowerShell, use:

```powershell
.\install.ps1
.\start.ps1
```

These require Node.js 24 and standard Windows Python 3.11+. If needed, use `install.ps1 -Python "C:\path\to\python.exe" -Npm "C:\path\to\npm.cmd"`; `start.ps1` accepts `-Node`.

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

Development progress is tracked in [PROGRESS.md](PROGRESS.md).

See [CONTRIBUTING.md](CONTRIBUTING.md) for commit conventions and automatic GitHub releases.

</details>
