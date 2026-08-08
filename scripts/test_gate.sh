#!/usr/bin/env bash
set -euo pipefail
# Safety Gate [BLOCKING] — lint, compile, authority gates, composition smoke
# and the T0 curated gate marker set. Any step failure exits 1.
# Usage: ./scripts/test_gate.sh

PYTEST="python -m pytest"

# System-installed Python bindings (e.g. python3-gi, dbus) live in the
# dist-packages of the system interpreter. Under actions/setup-python the
# virtual environment Python does not see them unless the path is preserved.
# Keep it in one place so every step that needs bindings shares the same env.
SYSTEM_DIST_PACKAGES="/usr/lib/python3/dist-packages"
SYSTEM_PYTHONPATH="${SYSTEM_DIST_PACKAGES}${PYTHONPATH:+:${PYTHONPATH}}"

echo "=== [BLOCKING] Test Authority Safety Gate ==="

echo "-- ruff --"
ruff check . --output-format concise

echo "-- compileall --"
python -m compileall -q -x '.venv/|\.tmpl\.' .

echo "-- single authority --"
python scripts/check_single_authority.py

echo "-- qml-only gate --"
python scripts/qml_only_gate.py

echo "-- patch artifacts --"
python scripts/check_patch_artifacts.py

echo "-- composition smoke --"
QT_QPA_PLATFORM=offscreen PYTHONPATH="$SYSTEM_PYTHONPATH" python scripts/smoke_composition.py

echo "-- pytest -m gate (T0 curated set) --"
QT_QPA_PLATFORM=offscreen PYTHONPATH="$SYSTEM_PYTHONPATH" $PYTEST -m "gate" -q

echo "=== [BLOCKING] Safety Gate PASSED ==="
