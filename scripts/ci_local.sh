#!/usr/bin/env bash
# Local CI simulation — deterministic fast blocking path mirroring
# scripts/ci_canonical.sh semantics inside a clean venv:
#   default:        LINT + STATIC SAFETY + T0 + unit selection (CI unit job)
#   --full:         + INVENTORY (full suite, diagnostic, non-blocking)
#   --strict-advisory: escalates advisory/inventory failures to exit 1
# Run this before pushing to verify basic CI compliance.
# Supports: Debian/Ubuntu, Arch/CachyOS, Fedora, openSUSE
set -euo pipefail

REPO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
TMPDIR=$(mktemp -d)
trap 'rm -rf "$TMPDIR"' EXIT

FULL=0
STRICT_ADVISORY=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --strict-advisory) STRICT_ADVISORY=1 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

FAILED=0
fail_blocking() {
  echo "  FAILED [BLOCKING]: $1"
  FAILED=1
}

# Safe-mode + test path isolation (kept from the original semantics).
export MICHI_SAFE_MODE=1
export MICHI_TEST_DATA_DIR="$TMPDIR/michi-test-data"
export MICHI_TEST_CACHE_DIR="$TMPDIR/michi-test-cache"
export MICHI_TEST_CONFIG_DIR="$TMPDIR/michi-test-config"

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

# [6/10] Blocking gate path (mirrors scripts/ci_canonical.sh semantics):
# LINT + STATIC SAFETY + T0 + unit selection (matches the CI unit job).
# Any failure accumulates in FAILED and the final exit code is 1.

# ── LINT (blocking) ──
echo "LINT: ruff + compileall..."
if ! python3 -m ruff check . --output-format concise; then fail_blocking "ruff check"; fi
if ! python3 -m compileall -q -x '.venv/|\.tmpl\.' .; then fail_blocking "compileall"; fi

# ── STATIC SAFETY (blocking) ──
echo "STATIC SAFETY: authority gates..."
if ! python3 scripts/check_single_authority.py; then fail_blocking "single authority gate"; fi
if ! python3 scripts/qml_only_gate.py; then fail_blocking "qml-only gate"; fi
if ! python3 scripts/check_patch_artifacts.py; then fail_blocking "patch artifacts gate"; fi

# ── T0 SAFETY GATE (blocking) ──
# Uses scripts/test_gate.sh from PR-B (feat/test-authority-infra); PR-C is
# dependency-clean: without PR-B the static gates ran above, so the inline T0
# is the composition smoke (the gate pytest selection == the unit selection
# below, which runs in the CI unit job).
echo "T0 SAFETY GATE..."
if [ -f scripts/test_gate.sh ]; then
  if ! bash scripts/test_gate.sh; then fail_blocking "T0 test_gate.sh"; fi
else
  echo "  PR-B not merged: static gates ran above; T0 = composition smoke"
  if ! QT_QPA_PLATFORM=offscreen \
      python3 scripts/smoke_composition.py; then fail_blocking "T0 composition smoke"; fi
fi

# ── UNIT SELECTION (blocking, matches CI unit job) ──
echo "UNIT TESTS (CI unit selection)..."
if ! QT_QPA_PLATFORM=offscreen \
    python3 -m pytest tests/ -q --timeout=300 \
    --ignore=tests/qml --ignore=tests/test_large_library.py \
    --ignore=tests/perf -k "not qt_widget and not QtWidget" \
    --deselect tests/test_context_semantic_audit.py::TestContextSemanticAudit::test_no_appevent_import_outside_context; then
  fail_blocking "unit tests"
fi

# ── INVENTORY (diagnostic, --full only) ──
if [ "$FULL" -eq 1 ]; then
  echo "INVENTORY (diagnostic full suite)..."
  if ! QT_QPA_PLATFORM=offscreen python3 -m pytest -q --timeout=300; then
    echo "  FAILED [DIAGNOSTIC]: full inventory (non-blocking; escalate with --strict-advisory)"
    if [ "$STRICT_ADVISORY" -eq 1 ]; then fail_blocking "full inventory"; fi
  fi
fi

echo
if [ "$FAILED" -ne 0 ]; then
  echo "=== CI Local complete: BLOCKING FAILURE ==="
  exit 1
fi
echo "=== CI Local complete (all blocking OK) ==="
