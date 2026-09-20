#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
NODE="${NODE:-node}"
CHECK_ONLY=false
case "${1:-}" in
  --check) CHECK_ONLY=true; shift ;;
  --help|-h)
    echo 'Usage: bash start.sh [--check]'
    echo 'Checks dependencies, configuration, and ports before starting both services.'
    echo 'Use --check to validate without starting. Set NODE to override the Node executable.'
    exit 0 ;;
  "") ;;
  *) echo 'Usage: bash start.sh [--check]' >&2; exit 2 ;;
esac
if [[ $# -ne 0 ]]; then
  echo 'Usage: bash start.sh [--check]' >&2
  exit 2
fi

if [[ -f "$ROOT/backend/.venv/Scripts/python.exe" ]]; then
  VENV_PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
else
  VENV_PYTHON="$ROOT/backend/.venv/bin/python"
fi
if [[ ! -f "$VENV_PYTHON" || ! -f "$ROOT/frontend/node_modules/vite/bin/vite.js" ]]; then
  echo 'Dependencies are missing. Run: bash install.sh' >&2
  exit 1
fi
if ! command -v "$NODE" >/dev/null; then
  echo 'Node.js was not found. Install Node.js 24+ or set NODE to its executable.' >&2
  exit 1
fi
"$NODE" -e 'if (Number(process.versions.node.split(".")[0]) < 24) { console.error("Node.js 24 or newer is required."); process.exit(1); }'
(cd "$ROOT/backend" && "$VENV_PYTHON" -m app.startup)
if [[ "$CHECK_ONLY" == true ]]; then
  echo 'Startup checks passed. No services started.'
  exit 0
fi

pids=()
cleanup() {
  trap - EXIT INT TERM
  for pid in "${pids[@]}"; do
    kill "$pid" 2>/dev/null || true
  done
  for pid in "${pids[@]}"; do
    wait "$pid" 2>/dev/null || true
  done
}
trap cleanup EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

# exec keeps each recorded PID attached to the actual service.
(
  cd "$ROOT/backend"
  exec "$VENV_PYTHON" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
) &
pids+=("$!")
(
  cd "$ROOT/frontend"
  exec "$NODE" node_modules/vite/bin/vite.js --host 127.0.0.1 --port 5173 --strictPort
) &
pids+=("$!")

echo 'Starting services. Open http://localhost:5173 when Vite reports ready.'
echo 'Press Ctrl+C to stop both services.'
echo 'Save design / Load saved designs are available below the preview. Product URL intake is not connected yet.'
while true; do
  for pid in "${pids[@]}"; do
    if ! kill -0 "$pid" 2>/dev/null; then
      echo 'A service stopped. See its output above; stopping the other service.' >&2
      exit 1
    fi
  done
  sleep 1
done
