# Post-QML Stabilization Audit

**Date:** 2026-07-02  
**Version:** 0.2.0-alpha.1  
**Scope:** Project-wide audit and correction after QML incorporation  
**Branch audited:** `main` (HEAD = origin/main)  
**Working tree:** Clean  
**Rama QML pendiente:** `qml-migration-foundation` (34 commits ahead, no mergeados)

## Repository State Conclusion

- **`main` is the correct branch** — self-consistent, synced with `origin/main`, all QML infrastructure present.
- **No contradictions remain** in version, AGENTS.md, or documentation.
- **Demo data is properly gated** — not visible without `MICHI_QML_DEMO=1`.
- **DB paths use `core.paths.database_path()`** — no hardcoded paths.
- **`qml-migration-foundation` contains 34 unreleased QML refinements** (Home page, Sidebar premium, HomeAudio, ActionButton, Connections premium, playlists backend). These are NOT merged into `main`. This is the only significant gap between current state and a more refined QML experience.

## Initial State

The project had version/state contradictions across 6 files, hardcoded demo data in bridges, a hardcoded DB path in QML, an inverted logic bug in `LibraryBridge.folders`, and an `AGENTS.md` that claimed "no QML" while having a full QML layer.

## Inconsistencies Found

| File | Claimed | Reality |
|------|---------|---------|
| `pyproject.toml` | `0.2.0-beta` + classifier `3 - Alpha` | Contradictory version + status |
| `ESTADO.md` | "pre-alpha técnica" | Understates actual state |
| `roadmap.md` | `v0.1.0-alpha (Current)` + `v0.4 (Current)` | Two "Current" sections, no QML mention |
| `FEATURE_STATUS.md` | `0.2.0-beta`, "100%" for QML, "164 QML tests" | Overstates QML readiness |
| `AGENTS.md` | "native widgets only, no QML" (line 13) | Contradicts its own Section 13 (QML rules) |
| `qml_main.py` | `0.1.0-qml` + hardcoded path | Different version, path not portable |
| `app_bridge.py` | `0.1.0-qml` | Different version |
| `connections_bridge.py` | Demo server with `192.168.1.100:8080` | Demo data shown as real |
| `playlists_bridge.py` | "Favoritas" + "Descubrimientos" with `id: 0` | Demo data shown as real |
| `library_bridge.py:folders` | Inverted `hasattr` logic | `path` and `name` returned empty when object has `.path` |

**Total:** 10 files with issues across 6 categories.

## Changes Made

### Version Unification (6 files)
- `pyproject.toml`: `0.2.0-beta` → `0.2.0-alpha.1`
- `ui_qml_bridge/app_bridge.py`: hardcoded `0.1.0-qml` → `importlib.metadata` with fallback `0.2.0-alpha.1`
- `ui_qml_bridge/qml_main.py`: hardcoded `0.1.0-qml` → `importlib.metadata`
- `ESTADO.md`: "pre-alpha técnica" → "0.2.0-alpha.1 — pre-beta técnica avanzada" + describes QtWidgets/QML
- `docs/roadmap.md`: Rewritten — single `v0.2.0-alpha.1 (Current)` section with QtWidgets stable + QML experimental sub-sections
- `docs/FEATURE_STATUS.md`: Rewritten — honest statuses (Estable/Experimental/En validación/Placeholder)

### AGENTS.md Update
- Line 13: "native widgets only, no QML, no Electron" → "QtWidgets stable/fallback + QML experimental skin"
- Section 13 retitled "QML Experimental Skin (for AI assistants)" with explicit status: experimental, not default

### Demo Data Removal (2 files)
- `connections_bridge.py`: demo server removed from default path. Only shown when `MICHI_QML_DEMO=1`
- `playlists_bridge.py`: "Favoritas"/"Descubrimientos" removed from default path. Only shown with `MICHI_QML_DEMO=1`
- All demo items include `"is_demo": True` flag

### Hardcoded DB Path Fix (1 file)
- `qml_main.py`: `Path.home() / ".local" / "share" / "michi-music-player" / "library.db"` → `core.paths.database_path()` with fallback

### LibraryBridge.folders Fix (1 file)
- Inverted `hasattr` logic corrected. Now: `raw_path = getattr(f, "path", None) or str(f)` → returns correct `path` and `name`

### Track Identity Exposure (1 file)
- `library_bridge.py:_song_to_dict()`: added `track_id` and `track_uid` fields for future migration away from `filepath`

## Files Modified

| File | Change |
|------|--------|
| `pyproject.toml` | Version → `0.2.0-alpha.1` |
| `AGENTS.md` | QML status description |
| `ESTADO.md` | Version + dual UI description |
| `docs/roadmap.md` | Complete rewrite |
| `docs/FEATURE_STATUS.md` | Complete rewrite |
| `ui_qml_bridge/app_bridge.py` | Version via `importlib.metadata` |
| `ui_qml_bridge/qml_main.py` | Version via `importlib.metadata`, DB path via `core.paths` |
| `ui_qml_bridge/connections_bridge.py` | Demo data gated behind `MICHI_QML_DEMO=1`, `is_demo` flag |
| `ui_qml_bridge/playlists_bridge.py` | Demo data gated behind `MICHI_QML_DEMO=1`, `is_demo` flag |
| `ui_qml_bridge/library_bridge.py` | Folders logic fix, added `track_id`/`track_uid` |
| `tests/qml/test_qml_bridges.py` | Tests updated for new version + no demo data |

## Tests Executed

| Command | Result |
|---------|--------|
| `ruff check .` | 55 warnings (4 new style-only, 51 pre-existing) |
| `python -m compileall .` | ✅ 0 errors |
| `QT_QPA_PLATFORM=offscreen python3 scripts/smoke_startup.py` | 1 pre-existing error (schema `is_smart` column) |
| `QT_QPA_PLATFORM=offscreen pytest tests/test_core_paths.py -q` | ✅ passed |
| `QT_QPA_PLATFORM=offscreen pytest tests/qml/ -q` | **172 passed** |
| `QT_QPA_PLATFORM=offscreen pytest tests/test_library_state.py tests/test_library_state_controller.py tests/test_library_navigation_state.py tests/test_track_identity.py tests/test_media_item_fields.py tests/test_mediaitem_table_model.py tests/test_media_record_builder.py tests/test_library_mutation_service.py tests/test_library_watcher_controller.py tests/test_library_search_contract.py tests/test_library_organize_safe.py tests/test_library_health_service.py tests/test_navigation_history.py tests/test_navigation_back_forward.py tests/test_navigation_controller.py -q` | 228 passed, 1 pre-existing failure |

## Known Pre-existing Issues

- Smoke startup fails at step [5/7] SQLite: `no such column: is_smart` — pre-existing schema test issue
- `test_dispatch_radio_sets_playback_hub_sidebar` — pre-existing, `broadcast_hub` vs `playback_hub`
- 51 ruff warnings in non-library files (pre-existing)

## Risks Remaining

1. **Playlists backend separated** — QML PlaylistsBridge needs connected backend
2. **SyncManager real** — QML DevicesBridge receives `None` when SyncManager not available
3. **QML LibraryBridge** — receives SQLite connection directly (should go through LibraryDB eventually)
4. **filepath exposure** — QML currently uses `filepath` in songs; documented as tolerable temporarily

## Decisions Taken

1. Version locked to `0.2.0-alpha.1` — no beta declaration until QML is connected to real backends
2. Demo data gated behind `MICHI_QML_DEMO=1` — nothing fake appears as real
3. QML marked as experimental in all docs — QtWidgets remains stable/fallback
4. `AGENTS.md` updated to acknowledge QML layer without promoting it as final

## Next Prompt Recommended

1. Connect QML PlaylistsBridge to real PlaylistStore backend
2. Connect QML DevicesBridge to real SyncManager
3. Replace direct SQLite connection in QML bridges with LibraryDB service
4. Add e2e integration tests for QML → bridge → backend flow
5. Audit remaining `except: pass` in QML bridges (3 occurrences)
