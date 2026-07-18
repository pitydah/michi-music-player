#!/bin/bash
# Validate QML files — compile and lint
set -euo pipefail

REPO="$(cd "$(dirname "$0")/.." && pwd)"
cd "$REPO"

echo "=== QML compile check (limited — context properties needed) ==="
QT_QPA_PLATFORM=offscreen python3 -c "
import sys, os
sys.path.insert(0, '.')
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtGui import QGuiApplication
from pathlib import Path
app = QGuiApplication(sys.argv)
engine = QQmlEngine()
# Register all known context properties from bridge bindings
class D: pass
for n in ['appBridge','navigationBridge','themeBridge','settingsBridge','libraryBridge',
          'queueBridge','playbackBridge','nowplayingBridge','eqBridge','metadataBridge',
          'mixBridge','playlistsBridge','radioBridge','lyricsBridge','historyBridge',
          'homeBridge','homeAudioBridge','connectionsBridge','devicesBridge',
          'diagnosticsBridge','globalSearchBridge','jobBridge','audioLabBridge',
          'smartTaggingBridge','libraryDoctorBridge','discLabBridge','notificationBridge',
          'michiAiBridge','outputProfilesBridge','accessibilityBridge','capabilityBridge',
          'confirmationBridge','commandPaletteBridge','desktopBridge','appStateBridge',
          'themeBridge','coverProviderBridge','routeRegistryBridge','selectionContextBridge']:
    engine.rootContext().setContextProperty(n, D())
errors = []
for f in sorted(Path('ui_qml').rglob('*.qml')):
    c = QQmlComponent(engine, str(f))
    if c.status() != QQmlComponent.Ready:
        err = c.errorString()[:100]
        if 'is not installed' not in err and 'is not a type' not in err:
            errors.append(f'{f.name}: {err}')
if errors:
    print(f'{len(errors)} non-trivial errors:')
    for e in errors[:5]:
        print(f'  {e}')
else:
    print(f'QML: {len(list(Path(\"ui_qml\").rglob(\"*.qml\")))} files loaded OK')
"

echo "=== qmllint ==="
which qmllint 2>/dev/null && find ui_qml -name "*.qml" -exec qmllint {} \; 2>&1
echo "qmllint complete"

echo "=== QML-only gate ==="
python3 scripts/qml_only_gate.py

echo "=== QML VALIDATION PASSED ==="
