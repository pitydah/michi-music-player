# QML Release Readiness

**Date:** 2026-07-12
**Status:** NOT READY for default UI (~70%)

## Criteria

| Criterion | Status | Evidence |
|---|---|---|
| All critical flows have QML consumer | ✅ | Library, Playlists, Queue, History, Home, Radio, Lyrics, Mix, Settings |
| All bridges return typed errors | ✅ | ERROR_QUERY_* codes, safe_message(), error_catalog |
| Async operations use WorkerManager | ✅ | All DB queries, scanner, smart tagging |
| Cancellation supported where applicable | ✅ | TaskHandle, CancellationToken, cancel_task() |
| No sync Indexer.run() from QML slot | ✅ | ScannerJobAdapter via WorkerManager |
| No filepath in public models | ✅ | TrackListModel, QueueListModel, HistoryListModel |
| Runtime smoke passes with 0 critical warnings | ✅ | 7/7 checks, 15 critical patterns detected |
| Full CI gate passes | ✅ | 12/12 steps |
| Library 100k tracks without UI freeze | ⚠️ | Not benchmarked yet |
| Physical audio tested | ❌ | DEFERRED |
| Classic parity documented | ❌ | Parity matrix not published |
| QML as default UI | ❌ | QtWidgets remains stable fallback |

## Blockers for default QML

1. **Physical audio tests** — DEFERRED until functional score >= 80%
2. **Classic parity** — no explicit comparison with QtWidgets per flow
3. **Benchmarks** — no baseline for 10k/50k/100k tracks
4. **Settings pages** — not all migrated (audio settings, library settings)

## Recommendation

Keep QML experimental. Continue migration of settings pages and audio tools.
Target for default QML evaluation: after Wave XV.
