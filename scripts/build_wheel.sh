#!/usr/bin/env bash
set -euo pipefail

echo "=== Building wheel ==="
python -m build --wheel 2>&1 | tail -3

WHEEL=$(ls -t dist/*.whl 2>/dev/null | head -1)
if [ -z "$WHEEL" ]; then
    echo "ERROR: No wheel built"
    exit 1
fi
echo "Wheel: $WHEEL"

echo "=== Verifying wheel contents ==="
python -c "
import zipfile
with zipfile.ZipFile('$WHEEL') as z:
    names = z.namelist()
    for pkg in ['michi/', 'audio/', 'core/', 'library/', 'ui_qml/', 'ui_qml_bridge/']:
        ok = any(n.startswith(pkg) for n in names)
        print(f'  {pkg}: {\"OK\" if ok else \"MISSING\"}')" 2>&1

echo "=== Installing wheel in clean env ==="
python -m venv /tmp/wheel-test-env
source /tmp/wheel-test-env/bin/activate
pip install "$WHEEL" 2>&1 | tail -3
python -c "from michi import app_launcher; print('App imported OK')"
deactivate
rm -rf /tmp/wheel-test-env
echo "=== Wheel verification complete ==="
