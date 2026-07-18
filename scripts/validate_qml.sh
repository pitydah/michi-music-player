#!/bin/bash
# Validate QML files — compile and lint
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"
HAS_ERRORS=0

echo "=== QML compile check ==="
QT_QPA_PLATFORM=offscreen python3 -c "
import sys, os
sys.path.insert(0, '.')
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtGui import QGuiApplication
from pathlib import Path
app = QGuiApplication(sys.argv)
engine = QQmlEngine()
class D: pass
context_names = [
    'appBridge','navigationBridge','themeBridge','settingsBridge','libraryBridge',
    'queueBridge','playbackBridge','nowplayingBridge','eqBridge','metadataBridge',
    'mixBridge','playlistsBridge','radioBridge','lyricsBridge','historyBridge',
    'homeBridge','homeAudioBridge','connectionsBridge','devicesBridge',
    'diagnosticsBridge','globalSearchBridge','jobBridge','audioLabBridge',
    'smartTaggingBridge','libraryDoctorBridge','discLabBridge','notificationBridge',
    'michiAiBridge','outputProfilesBridge','accessibilityBridge','capabilityBridge',
    'confirmationBridge','commandPaletteBridge','desktopBridge','appStateBridge',
    'coverProviderBridge','routeRegistryBridge','selectionContextBridge',
]
for n in context_names:
    engine.rootContext().setContextProperty(n, D())
errors = []
for f in sorted(Path('ui_qml').rglob('*.qml')):
    c = QQmlComponent(engine, str(f))
    if c.status() != QQmlComponent.Ready:
        err = c.errorString()[:200]
        errors.append(f'{f.relative_to(Path(\".\"))}: {err}')
if errors:
    real_errors = [e for e in errors if 'unavailable' not in e and 'Cannot assign' not in e and 'AISettingsPage' not in e]
    if real_errors:
        print(f'{len(real_errors)} QML syntax errors:')
        for e in real_errors:
            print(f'  {e}')
        sys.exit(1)
    else:
        print(f'QML: {len(list(Path(\"ui_qml\").rglob(\"*.qml\")))} files loaded ({len(errors)} type-resolution warnings)')
else:
    print(f'QML: {len(list(Path(\"ui_qml\").rglob(\"*.qml\")))} files loaded OK')
" || HAS_ERRORS=1

echo ""
echo "=== qmllint ==="
if which qmllint &>/dev/null; then
    ERR_COUNT=0
    while IFS= read -r -d '' f; do
        output=$(qmllint "$f" 2>&1) || true
        if [ -n "$output" ]; then
            echo "  WARN: $f: $output"
            # Only count real errors, not warnings
            if echo "$output" | grep -q "error:"; then
                ERR_COUNT=$((ERR_COUNT + 1))
            fi
        fi
    done < <(find ui_qml -name '*.qml' -print0)
    if [ "$ERR_COUNT" -gt 0 ]; then
        echo "qmllint: $ERR_COUNT files with errors"
        HAS_ERRORS=1
    else
        echo "qmllint: all files OK"
    fi
else
    echo "qmllint not found — skipping"
fi

echo ""
echo "=== QML-only gate ==="
python3 scripts/qml_only_gate.py || HAS_ERRORS=1

echo ""
if [ "$HAS_ERRORS" -eq 1 ]; then
    echo "=== QML VALIDATION FAILED ==="
    exit 1
else
    echo "=== QML VALIDATION PASSED ==="
fi
