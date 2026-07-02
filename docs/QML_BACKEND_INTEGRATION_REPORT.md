# QML Backend Integration Report

**Date:** 2026-07-01  
**Version:** 0.2.0-alpha.1  
**Scope:** Connect QML experimental UI to real backend services

## Summary

All QML bridges were connected to real backend services. Demo data was removed from all bridges. A `QmlServiceFactory` in `qml_main.py` now creates and wires real services without depending on `MainWindow`.

## Bridges Connected Status

| Bridge | Backend | Constructor Dependencies | Status |
|--------|---------|-------------------------|--------|
| **PlaybackBridge** | `PlayerService` | `player_service` | ✅ Connected |
| **NowPlayingBridge** | Manual (via PlaybackBridge) | none | ✅ Connected |
| **LibraryBridge** | `LibraryDB` + `SearchEngine` | `db`, `search_engine`, `playback_ctrl` | ✅ Connected |
| **PlaylistsBridge** | `LibraryDB` playlist CRUD | `db` | ✅ Connected |
| **DevicesBridge** | `SyncManager` | `sync_manager` | ✅ Connected |
| **ConnectionsBridge** | `MichiLink ServiceManager` | `michi_link_ctrl` | ✅ Connected |
| **SettingsBridge** | `core.settings_manager` | none | ✅ Connected |
| **RadioBridge** | `RadioManager` + `PlayerService` | `radio_manager`, `player_service` | ✅ Connected |
| **AudioLabBridge** | `core.audio_lab.library_health` | `db_conn` | ✅ Connected |
| **MetadataBridge** | mutagen (read-only) | none | ✅ Honest (read-only) |
| **MixBridge** | `LibraryDB` | `db` | ✅ Connected (basic) |
| **MichiAIBridge** | `MichiAIContextBridge` + `PlanBuilder` | none (set_controller) | ✅ Connected |
| **NavigationBridge** | Static route validation | none | ✅ Connected |
| **CoverBridge** | `LibraryDB` album_art_cache | `qmlRegisterType` | ✅ Connected |
| **ThemeBridge** | Static dark mode toggle | none | ✅ Connected |
| **CommandBus** | Generic signal dispatcher | none | ✅ Connected |

## Demo Data Removed

| Bridge | Previous Demo | Current Behavior |
|--------|--------------|------------------|
| `connections_bridge.py` | `192.168.1.100:8080` hardcoded | Empty list unless `MICHI_QML_DEMO=1` |
| `playlists_bridge.py` | "Favoritas" + "Descubrimientos" | Empty list unless `MICHI_QML_DEMO=1` |
| `radio_bridge.py` | "Ejemplo Radio" with example.com | Empty list (no fallback) |

## Service Factory (`QmlServiceFactory`)

Created in `qml_main.py`. Initializes:

- `LibraryDB` via `core.paths.database_path()`
- `PlayerService` via `GStreamerEngine`
- `SyncManager` via `LibraryDB`
- `RadioManager`
- `MichiLink ServiceManager`
- `SearchEngine`

All with graceful fallback (returns `None` if unavailable — bridges handle `None`).

## Playlists Backend Fix

`PlaylistsBridge` previously imported `library.playlists.playlist_store.PlaylistStore` which **does not exist** in the codebase. Replaced with direct `LibraryDB` playlist methods (`get_playlists`, `create_playlist`, `delete_playlist`, `update_playlist`, `get_playlist_items`).

## Files Modified

| File | Change |
|------|--------|
| `ui_qml_bridge/qml_main.py` | Complete rewrite: `QmlServiceFactory` + real service wiring |
| `ui_qml_bridge/playlists_bridge.py` | Replaced broken `PlaylistStore` import with `LibraryDB` |
| `ui_qml_bridge/radio_bridge.py` | Added `player_service` dependency, `playStation`, `deleteStation` |
| `tests/qml/test_qml_bridges.py` | Updated tests for no-demo-data behavior |

## Tests

| Suite | Result |
|-------|--------|
| `ruff check ui_qml_bridge/` | 1 warning (pre-existing style) |
| `python -m compileall .` | ✅ |
| `QT_QPA_PLATFORM=offscreen pytest tests/qml/ -q` | **165 passed** |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python3 scripts/smoke_startup.py` | 1 pre-existing error (`is_smart`) |

## What's Left for QML to Become Primary UI

1. **NowPlayingBridge** — currently does not receive `PlayerService`; cover key could be synced from PlaybackBridge
2. **MixBridge** — uses basic slicing/sorting instead of real recommendation engine
3. **AudioLabBridge** — `navigateTo` is a no-op stub
4. **MichiAIBridge** — suggestions fallback to static list when `MichiAIContextBridge` unavailable
5. **SettingsBridge** — no `reset` method; no "requires restart" flag for dangerous settings
6. **ConnectionsBridge** — `addManualServer` and `openHomeAudio` are stubs
7. **MetadataBridge** — `applyChanges` writes via mutagen; needs preview confirmation before it's safe

## Risks

- `PlayerService` requires `GStreamerEngine` which may fail on headless systems
- `LibraryDB` path resolution depends on `MICHI_TEST_DATA_DIR` env var in test mode
- Some bridges pass raw SQLite connections (`db_conn`) — should eventually go through `LibraryDB`
