#!/usr/bin/env bash
# Execute the productive UX capture audit under Xvfb.
set -euo pipefail

OUTPUT_DIR="${1:-artifacts/ux-screenshots}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"

if ! command -v Xvfb >/dev/null 2>&1; then
    echo "ERROR: Xvfb no está instalado. Instala el paquete xvfb." >&2
    exit 1
fi

DISPLAY_NUM="$(shuf -i 100-999 -n 1)"
Xvfb ":${DISPLAY_NUM}" -screen 0 1440x900x24 >"${TMPDIR:-/tmp}/michi-xvfb.log" 2>&1 &
XVFB_PID=$!

cleanup() {
    kill "$XVFB_PID" 2>/dev/null || true
    wait "$XVFB_PID" 2>/dev/null || true
}
trap cleanup EXIT

sleep 1
export DISPLAY=":${DISPLAY_NUM}"
export QT_QPA_PLATFORM=xcb
export MICHI_SAFE_MODE=1
export MICHI_CAPTURE_MODE=1

cd "$REPO_ROOT"

# The Python audit owns route navigation, settling delays, capture hashes and
# failure reporting. Keep one implementation of this workflow instead of two
# scripts that can diverge.
python3 - <<'PY' "$OUTPUT_DIR"
from __future__ import annotations

import sys
from pathlib import Path

import tests.ux_captures_baseline as audit

requested_output = Path(sys.argv[1]).resolve()
audit.OUTPUT_DIR = requested_output
raise SystemExit(audit.run())
PY

echo "UX screenshots verified in: $(realpath "$OUTPUT_DIR")"
