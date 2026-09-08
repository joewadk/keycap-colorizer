#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

PYTHON="${PYTHON:-python3}"
NPM="${NPM:-npm}"

if [[ ! -f backend/.venv/bin/python && ! -f backend/.venv/Scripts/python.exe ]]; then
  if [[ -e backend/.venv ]]; then
    echo 'backend/.venv exists but has no usable Python. Check it before reinstalling.' >&2
    exit 1
  fi
  echo 'Creating backend environment (Python 3.11+ required)...'
  "$PYTHON" -m venv backend/.venv
fi

if [[ -f backend/.venv/Scripts/python.exe ]]; then
  VENV_PYTHON="$ROOT/backend/.venv/Scripts/python.exe"
else
  VENV_PYTHON="$ROOT/backend/.venv/bin/python"
fi

echo 'Installing backend dependencies...'
"$VENV_PYTHON" -m pip install -e './backend[dev]'
echo 'Installing frontend dependencies from the lockfile...'
(cd frontend && "$NPM" ci)
echo 'Installation complete. Run: bash start.sh'
