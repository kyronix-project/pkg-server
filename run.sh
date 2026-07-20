#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
VENV_DIR="$SCRIPT_DIR/.venv"
REQUIREMENTS="$SCRIPT_DIR/requirements.txt"
HOST="${HOST:-0.0.0.0}"
PORT="${PORT:-8000}"

rebuild_venv() {
    echo ":: Rebuilding venv..."
    rm -rf "$VENV_DIR"
    python3 -m venv "$VENV_DIR"
    "$VENV_DIR/bin/pip" install --upgrade pip -q
    "$VENV_DIR/bin/pip" install -r "$REQUIREMENTS" -q
    echo ":: Venv rebuilt successfully."
}

if [ ! -d "$VENV_DIR" ]; then
    rebuild_venv
elif ! "$VENV_DIR/bin/python" -c "import fastapi, uvicorn" 2>/dev/null; then
    echo ":: Venv is corrupted or missing dependencies."
    rebuild_venv
fi

echo ":: Starting server on $HOST:$PORT"
exec "$VENV_DIR/bin/uvicorn" main:app --loop uvloop --host "$HOST" --port "$PORT" --app-dir "$SCRIPT_DIR"
