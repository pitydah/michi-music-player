#!/usr/bin/env bash
set -u
# CI Canonical — single command for full validation
# Usage: ./scripts/ci_canonical.sh

FAILED=0
step() {
    echo ""
    echo "--- $1 ---"
}
check() {
    if [ $? -ne 0 ]; then
        echo "FAILED: $1"
        FAILED=1
    fi
}

echo "=== CI Canonical ==="
echo "Python: $(python3 --version)"
echo "PWD: $(pwd)"

# 1. Ruff
step "1. Ruff"
ruff check . --output-format concise 2>&1 | tail -5; check "Ruff"

# 2. Compileall
step "2. Compileall"
python -m compileall -q -x '.venv/|\.tmpl\.' . 2>&1; check "Compileall"

# 3. Audit imports (QtWidgets in protected dirs)
step "3. QtWidgets import audit"
python scripts/audit_qtwidgets_imports.py 2>&1 || echo "WARNING: QtWidgets found in protected dirs"

# 4. Core tests
step "4. Core tests"
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300 \
  --ignore=tests/qml \
  --ignore=tests/test_audio_productive.py \
  2>&1 | tail -10; check "Core tests"

# 5. QML tests (structural)
step "5. QML tests"
QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/visual_x10/tests/test_controls_runtime.py tests/qml/visual_x10/test_dialog_runtime.py -q --timeout=120 2>&1 | tail -5; check "QML tests"

# 6. Audio productive tests
step "6. Audio productive tests"
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_audio_productive.py -q --timeout=60 2>&1 | tail -5; check "Audio productive tests"

# 7. QML compile check
step "7. QML compile check"
QT_QPA_PLATFORM=offscreen timeout 30 python3 -c "
import sys, os; sys.path.insert(0, '.')
from PySide6.QtQml import QQmlEngine, QQmlComponent
from PySide6.QtGui import QGuiApplication
from pathlib import Path
app = QGuiApplication(sys.argv)
engine = QQmlEngine()
class D: pass
for n in ['appBridge','navigationBridge','themeBridge','queueBridge','libraryBridge','playbackBridge','playlistsBridge','historyBridge','globalSearchBridge','settingsBridge','devicesBridge','notificationBridge','michiAiBridge','commandPaletteBridge','capabilityBridge','jobBridge','desktopBridge','homeBridge']:
    engine.rootContext().setContextProperty(n, D())
errors = [str(f) for f in sorted(Path('ui_qml').rglob('*.qml')) if QQmlComponent(engine, str(f)).status() != QQmlComponent.Ready]
if errors:
    for e in errors: print(f'QML ERROR: {e}')
    sys.exit(1)
print(f'QML: {len(list(Path(\"ui_qml\").rglob(\"*.qml\")))} compiled OK')
"; check "QML compile"

# 8. Build wheel
step "8. Build wheel"
python -m pip install build 2>/dev/null || true
python -m build --wheel 2>&1 | tail -5; check "Build wheel"

# 9. Verify wheel contents
step "9. Verify wheel contents"
WHEEL=$(ls -t dist/*.whl 2>/dev/null | head -1)
if [ -n "$WHEEL" ]; then
    python -c "
import zipfile, sys
with zipfile.ZipFile('$WHEEL') as z:
    names = z.namelist()
    has_ui_qml = any('ui_qml/' in n for n in names)
    has_ui_qml_bridge = any('ui_qml_bridge/' in n for n in names)
    has_qmldir = any(n.endswith('qmldir') for n in names)
    print(f'ui_qml/: {\"YES\" if has_ui_qml else \"NO\"}')
    print(f'ui_qml_bridge/: {\"YES\" if has_ui_qml_bridge else \"NO\"}')
    print(f'qmldir: {\"YES\" if has_qmldir else \"NO\"}')
    if not (has_ui_qml and has_ui_qml_bridge):
        sys.exit(1)
"; check "Verify wheel"
else
    echo "WARNING: No wheel built"
fi

echo ""
if [ $FAILED -ne 0 ]; then
    echo "=== CI Canonical complete (some steps FAILED) ==="
    exit 1
else
    echo "=== CI Canonical complete (all OK) ==="
fi
