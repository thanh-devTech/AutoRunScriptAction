#!/bin/zsh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_BIN="$(command -v python3 || true)"
GIT_BIN="$(command -v git || true)"

if [[ -z "$PYTHON_BIN" ]]; then
  echo "python3 is not installed or not in PATH."
  exit 1
fi

if [[ -z "$GIT_BIN" ]]; then
  echo "git is not installed or not in PATH."
  exit 1
fi

echo "Checking Python standard libraries..."
"$PYTHON_BIN" -c "import argparse, datetime, pathlib, re, subprocess, sys; print('OK: standard libraries available')"

echo "Running changelog generator..."
"$PYTHON_BIN" "$SCRIPT_DIR/generate_changelog.py"

echo "Done. Output file: $(cd "$SCRIPT_DIR/.." && pwd)/log.txt"
