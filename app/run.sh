#!/usr/bin/env bash
# Launch the NeuroState interface from the repository root: app/run.sh [--port 8765] [--no-browser]
set -euo pipefail
cd "$(dirname "$0")/.."
PY=experiments/.venv/bin/python
if [ ! -x "$PY" ]; then
  echo "Missing $PY. One-time setup: see app/README.md" >&2
  exit 1
fi
exec "$PY" -m app "$@"
