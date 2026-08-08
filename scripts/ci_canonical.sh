#!/usr/bin/env bash
set -euo pipefail

# CI Canonical — deterministic single-command validation.
#
# BLOCKING sections (LINT, STATIC SAFETY, T0): any failure sets the final exit
#   code to 1; a green script means the merge gates pass.
# ADVISORY section (development + quarantine): failures accumulate and print as
#   ADVISORY FAILURE but do NOT change the exit code unless --strict-advisory.
# INVENTORY section (--full flag, diagnostic): full pytest suite, reported but
#   NOT exit-blocking (mirrors the CI full-inventory diagnostic job).
# Exit codes: 0 = blocking green; 1 = blocking failure (or advisory/inventory
#   escalated via --strict-advisory); 2 = usage error.
#
# Usage: ./scripts/ci_canonical.sh [--full] [--strict-advisory]

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

FAILED=0
ADVISORY_FAILED=0
STRICT_ADVISORY=0
FULL=0
for arg in "$@"; do
  case "$arg" in
    --full) FULL=1 ;;
    --strict-advisory) STRICT_ADVISORY=1 ;;
    *) echo "ERROR: unknown argument: $arg" >&2; exit 2 ;;
  esac
done

step() { echo ""; echo "=== $1 ==="; }

# run_blocking LABEL CMD... — failure is exit-blocking.
run_blocking() {
  local label="$1"
  shift
  if "$@"; then
    echo "  OK [BLOCKING]: $label"
  else
    echo "  FAILED [BLOCKING]: $label"
    FAILED=1
  fi
}

# run_advisory LABEL CMD... — failure is reported, never exit-blocking.
run_advisory() {
  local label="$1"
  shift
  if "$@"; then
    echo "  OK [ADVISORY]: $label"
  else
    echo "  FAILED [ADVISORY]: $label"
    ADVISORY_FAILED=1
  fi
}

echo "=== CI Canonical ==="
echo "Python: $(python3 --version)"
echo "PWD: $(pwd)"

# ── LINT (blocking) ──
step "LINT"
run_blocking "ruff check" ruff check . --output-format concise
run_blocking "compileall" python -m compileall -q -x '.venv/|\.tmpl\.' .

# ── STATIC SAFETY (blocking) ──
step "STATIC SAFETY"
run_blocking "single authority gate" python scripts/check_single_authority.py
run_blocking "qml-only gate" python scripts/qml_only_gate.py
run_blocking "patch artifacts gate" python scripts/check_patch_artifacts.py

# ── T0 SAFETY GATE (blocking) ──
# Uses scripts/test_gate.sh from PR-B (feat/test-authority-infra). PR-C is
# dependency-clean: if the script is absent, LINT/STATIC SAFETY above are the
# static part of the gate, so the fallback is smoke + gate-marked tests.
step "T0 SAFETY GATE"
if [ -f scripts/test_gate.sh ]; then
  run_blocking "test_gate.sh" bash scripts/test_gate.sh
else
  echo "  NOTE: PR-B not merged - static gates ran above; T0 = smoke + gate tests"
  run_blocking "t0: composition smoke" bash -c 'QT_QPA_PLATFORM=offscreen python scripts/smoke_composition.py'
  if grep -q '"gate"' pyproject.toml; then
    run_blocking "t0: gate tests" bash -c 'QT_QPA_PLATFORM=offscreen python -m pytest -m gate -q --timeout=300'
  else
    echo "  NOTE: PR-B not merged - gate markers absent; pytest selection deferred to unit/CI"
  fi
fi

# ── ADVISORY (development + quarantine) — reported, not exit-blocking ──
step "ADVISORY: development + quarantine"
if [ -f scripts/test_development.sh ] && [ -f scripts/test_quarantine.sh ]; then
  run_advisory "development tests" bash scripts/test_development.sh
  run_advisory "quarantine tests" bash scripts/test_quarantine.sh
elif grep -q '"development"' pyproject.toml; then
  run_advisory "development or quarantine tests" bash -c 'QT_QPA_PLATFORM=offscreen python -m pytest -m "development or quarantine" -q --timeout=300'
else
  echo "  SKIPPED: PR-B not merged - development/quarantine markers absent"
fi

# ── INVENTORY (diagnostic, --full only) ──
if [ "$FULL" -eq 1 ]; then
  step "INVENTORY (diagnostic)"
  run_advisory "full inventory" bash -c 'QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300'
fi

echo ""
if [ "$ADVISORY_FAILED" -ne 0 ]; then
  echo "=== ADVISORY FAILURE (non-blocking) ==="
  if [ "$STRICT_ADVISORY" -eq 1 ]; then
    FAILED=1
    echo "  --strict-advisory: escalating advisory/inventory failures to BLOCKING"
  fi
fi
if [ "$FAILED" -ne 0 ]; then
  echo "=== CI Canonical complete: BLOCKING FAILURE ==="
  exit 1
fi
echo "=== CI Canonical complete (all blocking OK) ==="
