# Wave XXIII — Truth Baseline Audit

**SHA:** 5d36419d33d2e62127e00329accf1048e1cfc95b  
**Date:** 2026-07-13  
**Score:** 65.7%

## Test results
- Passed: 471
- Skipped: 17 (4 Mix legacy SQL, 13 TestWave10RealVerticalFlow isolation)
- xfailed: 0
- Runtime smoke: 8/8 (7 PASSED + 1 extra route)
- Ruff: 0 errors

## BridgeFactory issues
1. `LibraryBridge` built before `JobBridge` (line 427 creates library, line 452 creates job)
2. `TrackActionService` may receive `playlist_bridge=None` if playlists not yet created
3. `LibrarySourcesBridge` may receive `job_bridge=None`
4. `HistoryQueryService` not injected into `HistoryBridge`
5. `GlobalSearchBridge` receives `db` but no `query_executor`
6. `DiagnosticsBridge` receives no `worker_manager` or `query_executor`
7. `settings` and `settings_v2` are separate bridge instances (duplicated)
8. `HomeBridge` receives `library_sources_service` from `_get_library_sources_service()` but not connections/home_audio bridges
9. `QueueBridge` receives `playlists_bridge` only if already created
10. `SmartTaggingBridge` doesn't receive `library_refresh_coordinator` or `job_service`

## Settings issues
11. `SettingsBridgeV2` has `categories`, `getValue`, `setValue` but no `selectedCategoryId`
12. `SettingsPage.qml` still consumes property `sections` from legacy bridge
13. 17 skipped tests related to Mix (legacy fetch_all tests)
14. No schema migration layer exists
15. No runtime coordinator exists

## Module status (score)
- advanced_tools: 65% (FUNCTIONAL)
- ecosystem_network: 65% (FUNCTIONAL)
- library_playback: 65% (FUNCTIONAL)
- quality_release: 72% (SCORE_72)
- shell_nav: 65% (FUNCTIONAL)
- workflows_core: 63% (SCORE_63)

## Critical P0 actions
- Fix BridgeFactory order: job_bridge before library_bridge
- Unify settings/settings_v2 as same instance
- Inject HistoryQueryService, query_executor, worker_manager where missing
- Connect SettingsPage.qml to V2 bridge
