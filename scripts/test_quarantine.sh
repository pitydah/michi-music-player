#!/usr/bin/env bash
set -euo pipefail
# Quarantine tests [ADVISORY] — PROPOSED classification of the known-failing
# vertical clusters from the FASE 0 baseline (qml/settings, qml/tagging,
# qml/queue). Visible, still executed by default, non-blocking.
# Usage: ./scripts/test_quarantine.sh

PYTEST="python -m pytest"

echo "=== [ADVISORY] Quarantine tests (known-failing baseline, visible) ==="

if QT_QPA_PLATFORM=offscreen $PYTEST -m "quarantine" -q; then
    echo "=== [ADVISORY] Quarantine tests: PASS ==="
else
    echo "=== [ADVISORY] Quarantine tests: FAILURES EXPECTED (baseline), NON-BLOCKING ==="
fi

exit 0
