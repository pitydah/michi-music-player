# Testing Guide — Michi Music Player

## Quick start

```bash
# Core tests
python -m pytest tests/test_songs_service.py tests/test_library_service.py -q

# QML productive workflows (file by file to avoid PySide6 multi-file crash)
bash scripts/run_tests.sh tests/qml/productive_workflows/

# With Xvfb (fewer false crashes)
xvfb-run -a bash scripts/run_tests.sh tests/qml/productive_workflows/ xcb

# All QML tests
python -m pytest tests/qml/ -q

# Lint
ruff check . --output-format concise
```

## Runner script: `scripts/run_tests.sh`

Executes each `test_*.py` individually under `QT_QPA_PLATFORM=$PLATFORM`. Exit codes:

| Code | Meaning |
|------|---------|
| 0 | PASS |
| 5 | SKIP (no tests collected) |
| 124/137 | TIMEOUT (killed after 45s) |
| 134 | CRASH (SIGABRT — Qt abort in headless) |
| 139 | CRASH (SIGSEGV — segfault) |
| other | FAIL (test logic error) |

Runner exits with `FAILED + CRASHED + TIMED_OUT`.

## Test locations

| Directory | Contents |
|-----------|----------|
| `tests/qml/productive_workflows/` | Suite canónica (~42 files, QML + bridge) |
| `tests/qml/negative/` | Isolated tests (keyboard, backend error, etc.) |
| `tests/qml/` | All QML tests (structural, bridge) |
| `tests/` | Core service tests (no QML) |

## Markers

```python
pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("library"),
]
```
