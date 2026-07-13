# Wave XIX — Baseline Audit

**SHA:** 63e5e248ebdb3a1f0a440b4d09fc9d092502761c
**Date:** 2026-07-12

## Test results
- Passed: 475
- xfailed: 11 (MagicMock interference with real DB)
- xpassed: 2 (were xfail, now pass)
- Runtime smoke: 7/7 PASSED

## Known P0 problems (to fix in Wave XIX)

### WorkerManager
1. `taskCancelled` signal connected repeatedly (each run_task)
2. Progress callback can execute from worker thread
3. `cancel` ignores `cancellable=False`
4. Public error retains raw str(e)
5. Shutdown may emit on destroyed QObject

### QueryExecutor
6. `on_cancelled` delivered but not via WorkerManager's mechanism
7. `supersede` marks cancelled without confirming WorkerManager state
8. No terminal callback guard (exactly-once)
9. `submit` after shutdown returns request_id, but terminal emission path unclear

### BasePagedListModel
10. `refreshingChanged` not emitted consistently on cancel/stale
11. `emptyChanged` not separated from countChanged
12. `fetchMore` may insert duplicate rows under race
13. No `dispose` protection against late callback

### BridgeFactory
14. `create_job_bridge` depends on `library_bridge` which may not exist yet
15. `create_home_bridge` creates new `LibrarySourcesService` instead of reusing
16. Order allows `None` deps to be injected

### Scanner/JobBridge
17. `ScannerJobAdapter.scan()` called synchronously from Slot (runJob executor)
18. JobBridge creates ad-hoc ScannerJobAdapter per call
19. scanner uses main DB connection from worker thread

### Runtime smoke
20. Routes resolved to placeholder are not detected as failures
21. No Loader.Error check

## Test debt
- 11 xfail (MagicMock/DB interference)
- test_wave16_completion has 7 tests but only covers happy path
