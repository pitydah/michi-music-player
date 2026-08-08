#!/usr/bin/env bash
set -euo pipefail
# Stable Gate [BLOCKING] — deterministic tests expected green on every commit.
# Marker is opt-in: zero tests are classified "stable" today, so this exits 0
# with "no tests ran" until curated stable markers exist.
# Usage: ./scripts/test_stable.sh

PYTEST="python -m pytest"

echo "=== [BLOCKING] Stable Gate ==="

QT_QPA_PLATFORM=offscreen $PYTEST -m "stable" -q || {
    code=$?
    if [ "$code" -eq 5 ]; then
        echo "no stable-marked tests yet — nothing to gate"
        exit 0
    fi
    exit "$code"
}

echo "=== [BLOCKING] Stable Gate PASSED ==="
