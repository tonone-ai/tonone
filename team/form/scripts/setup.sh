#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

UIUX_LIB="$SCRIPT_DIR/../../../lib/uiux"
if [ ! -d "$UIUX_LIB/uiux" ]; then
	echo "uiux lib not found at $UIUX_LIB — skipping design intelligence"
fi

if command -v uv &>/dev/null; then
	uv venv "$SCRIPT_DIR/.venv"
	uv pip install -e "$SCRIPT_DIR" --python "$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 &>/dev/null; then
	python3 -m venv "$SCRIPT_DIR/.venv"
	"$SCRIPT_DIR/.venv/bin/pip" install -e "$SCRIPT_DIR"
else
	echo "ERROR: Python 3 is required. Install python3 or uv."
	exit 1
fi

echo "Form ready."
