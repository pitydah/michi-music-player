# Test Authority Baseline

Reproducible snapshot of the test suite used as the evidence floor for
[Development Convergence Mode](DEVELOPMENT_CONVERGENCE_MODE.md).

- **SHA**: `a7391335cdfb5e5c0471a37a432075d739b6e7df`
- **Content**: audited numbers only. Nothing in this file is extrapolated; all counts come from collection/execution at the SHA above.
- **Proposals are marked PROPOSED** and are not implemented.

## Reproduce

```bash
git checkout a7391335cdfb5e5c0471a37a432075d739b6e7df
python -m pytest tests/ -q
```

Collection config (`pyproject.toml [tool.pytest.ini_options]`): `testpaths=["tests"]`,
`qt_api="pyside6"`, `addopts="-m 'not perf and not hardware'"`, `timeout=120`,
`asyncio_mode="auto"`.

Plugins: pytest 8.4.2, pytest-qt 4.5.0, pytest-timeout 2.4.0, pytest-asyncio 0.24.0.

## Summary

| Metric | Value |
|---|---|
| Total collected items | 16250 = 16241 + 9 deselected |
| Deselected | 9, all `@pytest.mark.perf` (via `addopts`) |
| Test files | 1087 = 363 flat + 724 in subdirectories |

## Per-directory inventory

| Directory | Items | Files |
|---|---|---|
| `tests/qml/` (total) | 11733 | 587 |
| `tests/qml/` (root) | 2098 | — |
| `tests/qml/responsive_x10` | 1284 | — |
| `tests/qml/library` | 666 | — |
| `tests/qml/accessibility_x10` | 590 | — |
| `tests/qml/visual_x10` | 440 | — |
| `tests/qml/accessibility` | 387 | — |
| `tests/qml/audio_lab` | 368 | — |
| `tests/qml/settings` | 366 | — |
| `tests/qml/devices` | 335 | — |
| `tests/qml/runtime` | 267 | — |
| `tests/qml/playback` | 248 | — |
| `tests/qml/productive_workflows` | 227 | — |
| `tests/qml/queue` | 178 | — |
| `tests/qml/tagging` | 121 | — |
| `tests/qml/functional` | 62 | — |
| `tests/qml/decommission` | 36 | — |
| `tests/qml/negative` | 11 | — |
| `tests/*.py` (flat) | 3420 | 363 |
| `tests/integration` | 319 | 49 |
| `tests/architecture` | 283 | 56 |
| `tests/core` | 278 | 16 |
| `tests/e2e` | 109 | 6 |
| `tests/perf` | 99 | 10 |

The enumerated rows above sum to 7684 items (5586 in the subdirectories listed
plus 2098 at the `tests/qml/` root). The remaining 4049 items live in 37
additional subdirectories not enumerated in this audit.

## Markers

Markers used at baseline (usage counts): `parametrize` 118, `skip` 35, `skipif` 32,
`qml_dimension` 19, `qml_module` 14, `asyncio` 13, `perf` 6, `qml_route` 5,
`recognition` 2, `timeout` 1, `isolation` 1.

- Registered in `pyproject.toml`: `hardware`, `perf`, `isolation`, `qml_module`,
  `qml_dimension`, `recognition`.
- Registered in `tests/qml/conftest.py`: `qml_module`, `qml_dimension`, `qml_route`,
  `qml_workflow`, `widget_replacement` — `qml_workflow` and `widget_replacement`
  are registered but unused.
- **Warning**: `qml_route` and `timeout` are used but not registered →
  `PytestUnknownMarkWarning` at collection.

## Skips and xfails

| Signal | Count |
|---|---|
| `pytest.skip` calls | 186, in 54 files |
| `skipif` markers | 32 |
| `skip` markers | 35 |
| `xfail` | **0** — `test_ci_obligatorio.py:43` asserts `"xfail"` is not in content |
| Parametrized tests | 3195 |
| Async tests (`asyncio` mode auto) | 13 |
| Files using `qtbot` | 17 |

## Performance tests

- `tests/perf`: 99 items (10 files).
- Additional perf items outside `tests/perf`: `test_large_library.py` (2),
  `test_performance_baseline.py` (2).
- The 9 deselected items (all `@pytest.mark.perf`) are selected with `-m perf`.

## Environment heuristics (counted per file)

| Heuristic | Files |
|---|---|
| `os.environ` reads | 54 (`MICHI_SAFE_MODE` 28, `MICHI_TEST_*` 20, `MICHI_MICRO_*` 10, `MICHI_UI` 10) |
| `subprocess` usage | 40 |
| snapcast/snapserver references | 40 |
| DBus references | 4 |
| `/proc` references | 1 |
| network references | 6 |
| pyaudio references | 1 |
| `skipif` on `QT_QPA_PLATFORM` | 3 |
| `skipif` on CI | 2 |
| `skipif` on `platform.system` | 20 |
| `skipif` on win32 | 2 |

## Verified fixture problems

`tests/qml/settings/test_settings_negative.py`:

- 7 `NameError: _load_page` (9 references; the helper is defined in 15 sibling
  files in `tests/qml/settings/` but not in this file).
- 2 `fixture 'bridge' not found` errors (lines 283 and 293).

## Duplicated helpers (second definition shadows the first → dead first class)

| Duplicated symbol | Location |
|---|---|
| `TestSettingsAboutPage` | own file, twice |
| `TestSettingsAccessibilityPage` | own file, twice |
| `TestSettingsNegative` | own file, twice |
| `TestSettingsPlaybackPage` | own file, twice |
| `FakeBus` | — |
| `PartiallyFailingService` | — |

Missing helpers:

- `_load_page` ×9 (`tests/qml/settings/test_settings_negative.py`)
- `_create_context` ×2 (`tests/qml/settings/test_settings_about.py`)

## Failing clusters at SHA (verified by execution)

| Cluster | Result | Breakdown |
|---|---|---|
| `tests/qml/settings` | 33 failed + 2 errors | unbound `QObject.metaObject` TypeError ×16, `NameError _load_page` ×12, `fixture 'bridge'` ×2, missing `SettingsCategoryPage.qml` ×1, objectName mismatch ×3, `DID NOT RAISE` ×1 |
| `tests/qml/tagging` | 3 failed | `smart_tagging` dotfile, `no_service_scan_track`, `no_worker_manager` |
| `tests/qml/queue` | 2 failed | `DID NOT RAISE` ×2 |
| **Total** | **38 failed + 2 errors** | referred to as the *vertical functional gate cluster* |

## CI runner inventory and contradictions

| Runner | Selection | Contradiction |
|---|---|---|
| CI unit job | `tests/` minus `qml`, `large_library`, `perf`; `-k not qt_widget`; one deselect | Conflicts with full-inventory job |
| CI full-inventory job | `tests/` with no ignores | Red by design |
| `Makefile` `test` target | Ignores `qml` and `large_library` only | No perf ignore, no `-k`, no deselect |
| `ci_canonical.sh` step 4 | Ignores `tests/test_audio_productive.py` | File does not exist — stale ignore |
| `ci_canonical.sh` step 5 | Runs only 2 `visual_x10` files | Narrow, does not represent `visual_x10` |
| `ci_local.sh` | Full suite, `set -euo pipefail` | Red by design with current suite |
| `.github/workflows/library-data/premium-validation.yml` | Branch-filtered narrow selections | Does not cover the suite |

Net effect: there is no single runner that represents the suite's real state;
each runner implies a different contract. Resolution of the runners is PR-B/PR-C
scope, not this document.

## Provisional per-directory classification (PROPOSED — not implemented)

| Directory | Proposed class |
|---|---|
| `tests/qml/settings` | quarantine |
| `tests/qml/tagging` | quarantine |
| `tests/qml/queue` | quarantine |
| `tests/perf` + `test_large_library.py` | legacy / T3-manual |
| `tests/qml/functional` | T1 candidate (single green run; not stable evidence) |
| rest of `tests/qml/` | unclassified |
| flat `tests/`, `tests/core`, `tests/architecture`, `tests/integration` | T1/T2 candidate (not fully green) |
| `tests/e2e` | T3-manual |
| `tests/qml/decommission` | legacy |
| T0 gate set (PR-B) | curated `@pytest.mark.gate` set — 15–25 deterministic, contract-critical tests (service manifest completeness, container shutdown-once, crash reporter, XDG paths consolidation, library DB WAL, search FTS5 sanitization) plus the existing script gates; exact membership materialized in PR-B, CI enforcement in PR-C |

This table is a starting hypothesis for the rehabilitation process
([Development Convergence Mode](DEVELOPMENT_CONVERGENCE_MODE.md#rehabilitation-process-keep-rewrite-quarantine-delete));
it changes only through KEEP/REWRITE/QUARANTINE/DELETE decisions.
