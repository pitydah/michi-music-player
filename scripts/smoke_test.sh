#!/usr/bin/env bash
set -euo pipefail

echo "=== Smoke test ==="
echo "Python: $(python3 --version)"
echo ""

# 1. Import core modules
echo "--- 1. Import core modules ---"
python3 -c "
import audio
import core
import library
import integrations
print('All core modules imported OK')
" 2>&1

# 2. Import QML bridges
echo "--- 2. Import QML bridges ---"
python3 -c "
import ui_qml_bridge.action_registry
r = ui_qml_bridge.action_registry.ActionRegistry()
print(f'ActionRegistry created OK: {r}')
" 2>&1

# 3. Import service container
echo "--- 3. Import service container ---"
python3 -c "
from core.service_container import ObservableServiceContainer
c = ObservableServiceContainer()
print(f'ObservableServiceContainer created OK')
" 2>&1

# 4. Check backend contract
echo "--- 4. Backend contract ---"
python3 -c "
from audio.backends.base import AudioBackend
from audio.backends.gstreamer_backend import GStreamerAudioBackend
b = GStreamerAudioBackend()
for method in ['play','pause','resume','toggle','stop','seek','set_volume',
               'get_snapshot','get_diagnostics','shutdown']:
    assert hasattr(b, method), f'Missing: {method}'
print('GStreamerAudioBackend contract OK')
" 2>&1

echo ""
echo "=== Smoke test complete ==="
