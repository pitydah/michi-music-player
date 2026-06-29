#!/usr/bin/env bash
# Local CI simulation — validates that pip install, lint, compile, and pytest
# all work in a clean venv with system-site-packages.
# Run this before pushing to verify basic CI compliance.
# Supports: Debian/Ubuntu, Arch/CachyOS, Fedora, openSUSE
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

echo "=== CI Local Test ==="
echo

# [1/10] Create clean venv
echo "[1/10] Creating virtual environment (--system-site-packages)..."
python3 -m venv --system-site-packages "$TMPDIR/.venv"
source "$TMPDIR/.venv/bin/activate"
pip install --upgrade pip -q

# [2/10] Install package (editable with dev deps)
echo "[2/10] Installing michi-music-player..."
cd "$REPO_DIR"
pip install -e ".[dev]" 2>&1 | tail -3

# [3/10] Verify system deps are NOT installed inside the venv
echo "[3/10] Verifying no system deps via pip..."
python3 << 'PYEOF'
import os
import subprocess
import sys
from pathlib import Path

venv = Path(os.environ.get("VIRTUAL_ENV", "")).resolve()
pkgs = ["PyGObject", "pycairo", "dbus-python"]
failed = False


def classify_location(loc: str) -> str:
    """Classify where a package is installed."""
    if not loc:
        return "unknown"
    p = Path(loc).resolve()
    s = str(p)

    # inside the test venv -> installed by pip
    if venv and s.startswith(str(venv)):
        return "venv-pip"

    # system paths (apt, pacman, dnf, zypper)
    if any(s.startswith(prefix) for prefix in ("/usr/lib", "/usr/local/lib", "/lib", "/opt")):
        return "system"

    # Debian/Ubuntu dist-packages
    if "dist-packages" in s:
        return "system"

    # user-site (pip install --user)
    if "/.local/lib/" in s:
        return "user-site-warning"

    # unknown location
    return "unknown"


for pkg in pkgs:
    r = subprocess.run(
        [sys.executable, "-m", "pip", "show", pkg],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        print(f"  OK: {pkg} not visible to pip")
        continue

    loc = ""
    for line in r.stdout.splitlines():
        if line.startswith("Location:"):
            loc = line.split("Location:", 1)[1].strip()
            break

    cls = classify_location(loc)
    if cls == "venv-pip":
        print(f"  FAIL: {pkg} appears installed inside venv: {loc}")
        failed = True
    elif cls == "system":
        print(f"  OK: {pkg} from system path: {loc}")
    elif cls == "user-site-warning":
        print(f"  WARN: {pkg} from user site (not venv): {loc}")
    else:
        print(f"  WARN: {pkg} location could not be classified: {loc}")

if failed:
    sys.exit(1)

print("  OK - system-only deps are not installed inside the venv")
PYEOF

# [4/10] Verify metadata
echo "[4/10] Verifying metadata..."
python3 << 'PYEOF'
import importlib.metadata
v = importlib.metadata.version('michi-music-player')
print(f"  michi-music-player {v}")
assert v.startswith('0.1'), f"Unexpected version: {v}"
print("  OK")
PYEOF

# [5/10] Verify PyGObject / GStreamer runtime
echo "[5/10] Verifying PyGObject / GStreamer runtime..."
python3 << 'PYEOF'
import sys
print(f"  Python: {sys.executable}")
try:
    import gi
    gi.require_version("Gst", "1.0")
    gi.require_version("GstPbutils", "1.0")
    from gi.repository import Gst, GstPbutils
    Gst.init(None)
    print(f"  OK: {Gst.version_string()}")
    print(f"  OK: GstPbutils available ({GstPbutils})")
except Exception as e:
    print(f"  FAIL: PyGObject / GStreamer unavailable: {e!r}")
    raise
PYEOF

# [6/10] Smoke startup
echo "[6/10] Running smoke startup..."
cd "$REPO_DIR"
QT_QPA_PLATFORM=offscreen \
PYTHONUNBUFFERED=1 \
MICHI_SAFE_MODE=1 \
MICHI_TEST_DATA_DIR="$TMPDIR/michi-smoke-data" \
MICHI_TEST_CACHE_DIR="$TMPDIR/michi-smoke-cache" \
MICHI_TEST_CONFIG_DIR="$TMPDIR/michi-smoke-config" \
python3 scripts/smoke_startup.py || { echo "  SMOKE STARTUP FAILED"; exit 1; }
echo "  OK"

# [7/10] Smoke UI routes
echo "[7/10] Running UI route smoke..."
cd "$REPO_DIR"
QT_QPA_PLATFORM=offscreen \
PYTHONUNBUFFERED=1 \
MICHI_SAFE_MODE=1 \
MICHI_TEST_DATA_DIR="$TMPDIR/michi-smoke-data" \
MICHI_TEST_CACHE_DIR="$TMPDIR/michi-smoke-cache" \
MICHI_TEST_CONFIG_DIR="$TMPDIR/michi-smoke-config" \
python3 scripts/smoke_ui_routes.py || { echo "  UI ROUTE SMOKE FAILED"; exit 1; }
echo "  OK"

# [8/10] Lint
echo "[8/10] Running lint..."
python3 -m ruff check . --output-format concise || { echo "  LINT FAILED"; exit 1; }
echo "  OK"

# [9/10] Compile
echo "[9/10] Running compileall..."
python3 -m compileall -q -x '.venv/|\.tmpl\.' . || { echo "  COMPILE FAILED"; exit 1; }
echo "  COMPILE OK"

# [10/10] Pytest
echo "[10/10] Running pytest..."
cd "$REPO_DIR"
QT_QPA_PLATFORM=offscreen \
PYTHONUNBUFFERED=1 \
MICHI_SAFE_MODE=1 \
MICHI_TEST_DATA_DIR="$TMPDIR/michi-test-data" \
MICHI_TEST_CACHE_DIR="$TMPDIR/michi-test-cache" \
MICHI_TEST_CONFIG_DIR="$TMPDIR/michi-test-config" \
python3 -m pytest -q || { echo "  TEST FAILED"; exit 1; }
echo "  OK"

echo
echo "=== All CI checks passed ==="
