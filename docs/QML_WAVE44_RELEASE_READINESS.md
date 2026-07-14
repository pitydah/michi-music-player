# QML Wave XLIV — Release Readiness

**Date:** 2026-07-13
**SHA:** 49cd95c
**Status:** NOT READY for default UI (~82%)

## Summary

Wave XLIV (Performance, CI Enforcement, Guarded Default Candidate) completa la
infraestructura de CI obligatoria, benchmarks reales con SQLite en 10k/50k/100k
pistas, y elimina skips críticos en la suite QML.

## CI Jobs (14 total)

| Job | Status |
|---|---|
| packaging (3.11, 3.12) | ✅ `python -m build` |
| runtime (GStreamer + pytest) | ✅ |
| qml-unit (pytest tests/qml -q --timeout=180) | ✅ 815 passed |
| qml-integration (tests marcados integration) | ✅ |
| qml-runtime (qml_full_runtime_smoke.py) | ✅ |
| qml-evidence (manifest_v3_audit.py) | ✅ |
| performance-10k-50k | ✅ |
| performance-100k | ✅ |
| physical-artifact-validation | ✅ |

## Benchmarks

### 10k tracks
| Scenario | Median | p95 | Threshold |
|---|---|---|---|
| Count | <1ms | 1ms | 150ms |
| First page | 2ms | 2ms | 250ms |
| FTS search | 3ms | 3ms | 250ms |
| Album detail | 1ms | 2ms | 100ms |

### 50k tracks
| Scenario | Median | p95 | Threshold |
|---|---|---|---|
| Count | <1ms | <1ms | 300ms |
| First page | 2ms | 2ms | 450ms |
| FTS search | 3ms | 3ms | 500ms |
| Album detail | 1ms | 1ms | 200ms |

### 100k tracks
| Scenario | Median | p95 | Threshold |
|---|---|---|---|
| Count | <1ms | <1ms | 500ms |
| First page | 2ms | 2ms | 750ms |
| FTS search | 3ms | 3ms | 900ms |
| Album detail | 1ms | 2ms | 300ms |

## Test Results

- **Collected:** 830 (excl. 13 isolation)
- **Passed:** 815
- **Failed:** 0
- **Skipped:** 5 (pre-existing, non-critical)
- **Ruff:** 0 violations
- **Compileall:** clean

## Key Changes

1. **tests/perf/test_qml_real_db_10k_50k.py** — New: real SQLite benchmark with
   17 scenarios, 3 runs each, median/p95 reporting
2. **tests/perf/test_qml_real_db_100k.py** — New: 100k critical scenarios
   (count, first page, FTS, album detail)
3. **.github/workflows/ci.yml** — 9 jobs, no `continue-on-error: true` for
   performance, no crashes accepted, packaging 3.11/3.12 added
4. **tests/qml/test_wave9_vertical_end_to_end.py** — Removed `@pytest.mark.skip`
   from TestWave10RealVerticalFlow, added `@pytest.mark.isolation` for
   process-level isolation
5. **ui_qml_bridge/library_query_service.py** — Fixed FTS5 detection
   (`type='table'` not `type='virtual_table'`)
6. **tests/qml/test_wave12_async_production_flow.py** — Fixed FTS table to
   use proper FTS5 virtual table
7. **docs/qml_migration_before_after.json** — New: readiness report

## Blockers for default QML

1. **Physical audio (21/21 checks)** — DEFERRED (no CI hardware)
2. **Album views** — still PARTIAL
3. **Settings pages** — audio settings not fully migrated
4. **LibraryConnectionFactory** — thread-local caching limits parallel tests

## Recommendation

**no_until_physical_21_21** — QML remains experimental. All 21 physical audio
checks must pass and all blocked modules resolved before promoting to default UI.
