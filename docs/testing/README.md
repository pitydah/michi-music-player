# Testing — Michi Music Player

Index of the testing authority system: what blocks, what is advisory, and how
to act on a failing suite. Read this before running anything beyond the quick
start.

## Authority documents (read in order)

1. [Development Convergence Mode](DEVELOPMENT_CONVERGENCE_MODE.md) — the tier
   model (T0–T3, Quarantine, Legacy), rehabilitation process, promotion workflow.
2. [Test Authority Baseline](TEST_AUTHORITY_BASELINE.md) — audited suite
   snapshot at `a7391335`; per-directory inventory, failing clusters, PROPOSED
   classifications.
3. [Subsystem Maturity](SUBSYSTEM_MATURITY.yaml) — declared maturity per
   subsystem (documentary, not yet an automatic gate).
4. [AI Development Policy](../development/AI_DEVELOPMENT_POLICY.md) — how AI
   agents implement features and change tests (26A).
5. [Writing Tests](WRITING_TESTS.md) — placement, naming, fixtures.
6. [CI Pipeline](CI.md) — runner inventory and known contradictions.

## What blocks, what is advisory (summary)

| Level | Blocks merge? | Action |
|---|---|---|
| T0 Safety Gate | YES | Run before every merge: `pytest` on the T0 selection |
| T1 Stable | YES (regressions only) | A change must not regress T1 |
| T2 Development | No | Advisory; churn is expected |
| T3 Experimental/Env/Perf | No | Run manually with explicit markers |
| Quarantine | No | Visible, non-blocking; rehabilitation obligation |
| Legacy | No | Unvalidated contract; triage KEEP/REWRITE/QUARANTINE/DELETE |

Failing legacy test? Do not appease it. Triage it:
[rehabilitation process](DEVELOPMENT_CONVERGENCE_MODE.md#rehabilitation-process-keep-rewrite-quarantine-delete).

New feature? Add tests in the same work unit, default tier T2:
[adding tests for new features](DEVELOPMENT_CONVERGENCE_MODE.md#adding-tests-for-new-features).

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

# Perf (T3-manual): selects the 9 @pytest.mark.perf items
python -m pytest -m perf -q

# Lint
ruff check . --output-format concise
```

> Default collection deselects `perf` (and `hardware`) via
> `addopts = "-m 'not perf and not hardware'"` — see the
> [baseline config](TEST_AUTHORITY_BASELINE.md#reproduce).

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
| `tests/qml/productive_workflows/` | Canonical workflow suite (QML + bridge) |
| `tests/qml/negative/` | Isolated tests (keyboard, backend error, etc.) |
| `tests/qml/` | All QML tests (structural, bridge); 11733 items at baseline |
| `tests/` flat | Core service tests (3420 items); `integration`, `architecture`, `core`, `e2e`, `perf` subdirs |

## Markers

```python
pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("library"),
]
```

Registered markers and usage counts: see [baseline markers](TEST_AUTHORITY_BASELINE.md#markers).
