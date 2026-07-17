#!/usr/bin/env bash
# Execute the productive UX capture audit under Xvfb.
set -euo pipefail

OUTPUT_DIR="${1:-artifacts/ux-screenshots}"
REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT_DIR="$(mkdir -p "$OUTPUT_DIR" && cd "$OUTPUT_DIR" && pwd)"

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
export MICHI_UX_OUTPUT_DIR="$OUTPUT_DIR"

cd "$REPO_ROOT"

# Keep route navigation, settling delays, hash validation and failure handling in
# one Python implementation so the shell and CI workflows cannot diverge.
python3 tests/ux_captures_baseline.py

echo "UX screenshots verified in: $OUTPUT_DIR"
