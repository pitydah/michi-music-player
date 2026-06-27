#!/usr/bin/env bash
# Local CI simulation — validates that pip install, lint, compile, and pytest
# all work in a clean venv with system-site-packages.
# Run this before pushing to verify basic CI compliance.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== CI Local Test ==="
echo

# 1. Create clean venv
echo "[1/6] Creating virtual environment (--system-site-packages)..."
python3 -m venv --system-site-packages "$TMPDIR/.venv"
source "$TMPDIR/.venv/bin/activate"
pip install --upgrade pip -q

# 2. Install package (editable with dev deps)
echo "[2/6] Installing michi-music-player..."
cd "$REPO_DIR"
pip install -e ".[dev]" 2>&1 | tail -3

# 3. Verify system deps are NOT installed by pip (they come from apt --system-site-packages)
echo "[3/6] Verifying no system deps via pip..."
python3 << 'PYEOF'
import subprocess, sys

result = subprocess.run([sys.executable, '-m', 'pip', 'show', 'PyGObject', 'pycairo', 'dbus-python'],
                       capture_output=True, text=True)
for line in result.stdout.splitlines():
    if line.startswith('Location:'):
        loc = line.split('Location:')[1].strip()
        if 'site-packages' in loc and 'dist-packages' not in loc:
            if 'PyGObject' in result.stdout or 'pycairo' in result.stdout or 'dbus-python' in result.stdout:
                print(f"  FAIL: system dep installed by pip at {loc}")
                exit(1)
for pkg in ['PyGObject', 'pycairo', 'dbus-python']:
    r = subprocess.run([sys.executable, '-m', 'pip', 'show', pkg], capture_output=True, text=True)
    if 'dist-packages' in r.stdout:
        continue
    if r.returncode == 0:
        loc_line = [l for l in r.stdout.splitlines() if l.startswith('Location:')]
        if loc_line and 'site-packages' in loc_line[0]:
            print(f"  FAIL: {pkg} installed by pip at {loc_line[0]}")
            exit(1)
print("  OK - system deps not installed by pip")
PYEOF

# 4. Verify metadata
echo "[4/6] Verifying metadata..."
python3 << 'PYEOF'
import importlib.metadata
v = importlib.metadata.version('michi-music-player')
print(f"  michi-music-player {v}")
assert v.startswith('0.1'), f"Unexpected version: {v}"
print("  OK")
PYEOF

# 5. Lint + compile
echo "[5/6] Running lint..."
python3 -m ruff check . --output-format concise || { echo "  LINT FAILED"; exit 1; }
echo "  OK"
python3 -m compileall -q . || { echo "  COMPILE FAILED"; exit 1; }
echo "  COMPILE OK"

# 6. Pytest
echo "[6/6] Running pytest..."
cd "$REPO_DIR"
QT_QPA_PLATFORM=offscreen \
PYTHONUNBUFFERED=1 \
MICHI_TEST_DATA_DIR="$TMPDIR/michi-test-data" \
MICHI_TEST_CACHE_DIR="$TMPDIR/michi-test-cache" \
MICHI_TEST_CONFIG_DIR="$TMPDIR/michi-test-config" \
python3 -m pytest -q || { echo "  TEST FAILED"; exit 1; }
echo "  OK"

echo
echo "=== All CI checks passed ==="
