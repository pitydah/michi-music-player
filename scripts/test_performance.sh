#!/usr/bin/env bash
set -euo pipefail
# Performance tests [ADVISORY] — manual or nightly only, non-blocking.
# Includes the tests/perf/ directory and legacy perf-marked files.
# Usage: ./scripts/test_performance.sh

PYTEST="python -m pytest"

echo "=== [ADVISORY] Performance tests (manual / nightly) ==="

if QT_QPA_PLATFORM=offscreen $PYTEST -m "performance" -q; then
    echo "=== [ADVISORY] Performance tests: PASS ==="
else
    echo "=== [ADVISORY] Performance tests: FAILURES ARE NON-BLOCKING ==="
fi

exit 0
