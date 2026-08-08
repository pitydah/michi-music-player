#!/usr/bin/env bash
set -euo pipefail
# Safety Gate [BLOCKING] — lint, compile, authority gates, composition smoke
# and the T0 curated gate marker set. Any step failure exits 1.
# Usage: ./scripts/test_gate.sh

PYTEST="python -m pytest"

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
QT_QPA_PLATFORM=offscreen PYTHONPATH=/usr/lib/python3/dist-packages python scripts/smoke_composition.py

echo "-- pytest -m gate (T0 curated set) --"
QT_QPA_PLATFORM=offscreen $PYTEST -m "gate" -q

echo "=== [BLOCKING] Safety Gate PASSED ==="
