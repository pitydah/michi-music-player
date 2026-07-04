# QML Migration Progress

**Date:** 2026-07-04
**Branch:** qml-functional-closure-release-readiness

## Overall: 58.8%

| Area | Weight | Before | After | State | Faltante |
|---|---:|---:|---:|---|---|
| Shell/navegación | 10% | 65% | 65% | FUNCTIONAL | Minor: NO_REFRESH bridges |
| Library/playback | 25% | 65% | 65% | FUNCTIONAL | LibraryBridge cache, playlists demo |
| Workflows core | 20% | 40% | 65% | FUNCTIONAL | Daily mix AI, radio backends |
| Advanced tools | 20% | 40% | 65% | FUNCTIONAL | DiscLab no backend, metadata real |
| Ecosystem/red | 10% | 20% | 40% | PARTIAL | HA/Snapcast backends not injected |
| Quality/release | 15% | 40% | 40% | PARTIAL | Performance/accessibility/physical |

## Key Changes
- Lyrics: synchronous → async WorkerManager + LRU cache + synced view + 11 tests
- Mix: `play_count` heuristic → real `favorites` table JOIN + `last_played` + `unplayed`
- Connections: `QMetaObject.invokeMethod("_navigate")` → injected NavigationBridge
- All bridges: `except: pass` → `except Exception: return {"ok": False, "error": ...}`
- All actions: `@Slot()` → `@Slot(result=dict)` with dict ok/error
- AudioLab: `navigateTo(module_id): pass` → `NavigationBridge.navigate(route)` + UNSUPPORTED
- EqBridge: all mutations return dict ok/error
- DevicesBridge: `serverActive=True` no longer set on `start()` failure
- Route registry: lyrics status updated to `functional`
- 21 new tests (lyrics: 11, mix: 6, home audio: 4)
- QML tests: 312 → 333 (+21)
- CI gate: 11/11 steps passing
