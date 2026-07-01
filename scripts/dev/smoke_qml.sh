#!/usr/bin/env bash
set -euo pipefail

echo "=== Michi QML Smoke Test ==="

export QT_QPA_PLATFORM=offscreen
TIMEOUT=10

echo "Launching QML in offscreen mode (timeout: ${TIMEOUT}s)..."
timeout "$TIMEOUT" python -m ui_qml_bridge.qml_main 2>&1 && EXIT_CODE=$? || EXIT_CODE=$?

if [ "$EXIT_CODE" -eq 124 ]; then
    echo "OK: QML started and ran for ${TIMEOUT}s without crash"
    exit 0
elif [ "$EXIT_CODE" -eq 0 ]; then
    echo "OK: QML exited cleanly"
    exit 0
else
    echo "FAIL: QML crashed with exit code $EXIT_CODE"
    exit 1
fi
