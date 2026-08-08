#!/usr/bin/env bash
set -euo pipefail
# Development tests [ADVISORY] — in-progress work, failures are non-blocking.
# Prints the pytest result and always exits 0.
# Usage: ./scripts/test_development.sh

PYTEST="python -m pytest"

echo "=== [ADVISORY] Development tests ==="

if QT_QPA_PLATFORM=offscreen $PYTEST -m "development" -q; then
    echo "=== [ADVISORY] Development tests: PASS ==="
else
    echo "=== [ADVISORY] Development tests: FAILURES ARE NON-BLOCKING ==="
fi

exit 0
