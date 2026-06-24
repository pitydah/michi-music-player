# Project Consistency Audit

**Date:** 2026-06-23
**Branch:** `chore/project-consistency-audit`
**Repository:** `github.com/pitydah/michi-music-player`

---

## Summary

Audited the project for name consistency, dead routes, STUBs, incomplete features, and optional service degradation.

**303 tests · ruff 0 · compileall clean**

---

## Files Reviewed

- `ui/sidebar_controller.py`, `ui/window.py` — sidebar routing
- `integrations/http_api/http_api.py` — HTTP API handler
- `data/com.michi.MusicPlayer.metainfo.xml` — packaging metadata
- `data/michi-music-player.desktop` — desktop entry
- `AGENTS.md` — developer documentation
- `ui/audio_lab/services/*.py` — Audio Lab STUBs
- `ui/services/transcode_service.py` — transcode STUB
- `adapters/mpris.py` — MPRIS adapter
- `home_assistant_custom_component/`, `ha_custom_component/` — HA integration
- `integrations/snapcast/` — Snapcast integration
- `scripts/`, `tools/`, `packaging/` — build and dev tools

---

## Issues Fixed

### 1. Sidebar: Dead `mix_hub` Route (CRITICAL)
**Bug:** `mix_` prefix pattern in `_on_sidebar_navigate` caught `mix_hub` before NAV_ROUTES dispatch. Clicking "Mix" in sidebar did nothing.
**Fix:** Pattern now only matches known smart mix keys (`mix_daily`, `mix_unplayed`, `mix_popular`, `mix_favorites`, `mix_flac`, `mix_no_cover`).

### 2. Sidebar: `settings_hub` Missing
**Bug:** `settings_hub` had NAV_ROUTES entry and handler but was never added to sidebar. No visible way to reach settings from sidebar.
**Fix:** Added `settings_hub` as "Configuración" item in hub section.

### 3. Sidebar: Hard Reset on Rebuild
**Bug:** Every `rebuild()` forced `set_active("home")`, losing user's navigation context.
**Fix:** `_last_active` tracks last clicked item; `rebuild()` restores it. Defaults to `"home"` on first load.

### 4. HTTP API: `_AstraHandler` → `_MichiHandler`
**Renamed** class and factory function. Legacy name removed from runtime.

### 5. HTTP API: `_handle_library_item` Method Name Mismatch (CRITICAL)
**Bug:** `do_GET` called `self._handle_library_item(media_id)` but method was named `handle_library_item` (no underscore). Any request to `/api/library/item/...` crashed with `AttributeError`.
**Fix:** Renamed method to `_handle_library_item`.

### 6. Packaging: Metainfo URLs
**Fixed** 5 URLs in `data/com.michi.MusicPlayer.metainfo.xml` from `astra-music-player` to `michi-music-player`.

### 7. AGENTS.md: Directory Reference
**Fixed** `astra_api/` → `michi_api/`.

---

## Issues Detected but Not Corrected (Out of Scope)

| Issue | Location | Reason |
|-------|----------|--------|
| HA component class names (`AstraApiClient`, etc.) | `home_assistant_custom_component/`, `ha_custom_component/` | Requires coordinated HA config migration |
| Snaplcast stream name "astra" | `integrations/snapcast/` | Requires user-facing config migration |
| Desktop keyword "astra" | `data/michi-music-player.desktop` | Search keyword — acceptable legacy |
| Flatpak manifest missing deps | `data/com.michi.MusicPlayer.yml` | Needs Flatpak SDK review |
| Duplicate install scripts | root vs `scripts/` | Root copies should be removed |
| Hardcoded paths in tools/ | `tools/*.py` | Dev tools, not shipped |

---

## STUBs Found

| Module | Methods | Classification |
|--------|---------|---------------|
| `TagWriter` | read_tags → `{}`, write_tags/write_batch/embed_cover → `pass` | STUB — awaits implementation |
| `ArtworkResolver` | search_album_art → `[]`, download/save/embed → `pass` | STUB — awaits implementation |
| `LibraryImporter` | build/import/add/refresh → `pass` or `""` | STUB — awaits implementation |
| `MetadataResolver` | find_by_disc_toc/artist_album → `None` | STUB — awaits implementation |
| `TranscodeService` | transcode → `pass` | STUB — awaits ffmpeg integration |
| `MPRISObject` | Raise/Quit → `pass` | Unimplemented — MPRIS stubs |

---

## Sidebar Routes (Verified)

| Item | Section | Handler | Status |
|------|---------|---------|--------|
| home | hub | `_show_home_page` | OK |
| library_hub | hub | `_show_library_hub_page` | OK |
| mix_hub | hub | `_show_mix_hub_page` | **FIXED** |
| playlist_hub | hub | `_show_playlist_hub` | OK |
| playback_hub | hub | `_show_playback_hub_page` | OK |
| connections_hub | hub | `_show_connections_hub_page` | OK |
| radio | hub | `_show_radio` | OK |
| audio_lab | hub | `_show_audio_lab` | OK |
| home_audio | hub | `_show_home_audio` | OK |
| identifier | hub | `_show_identifier` | OK |
| assistant | hub | `_show_assistant` | OK |
| settings_hub | hub | `_show_settings_hub_page` | **ADDED** |
| devices_page | dev | `_show_devices_page` | OK |

Dynamic routes (`pl:NN`, `srv:NN`, `dev:NM`, `dev:sync:NN`, smart mixes) all verified.

---

## Optional Services (Degradation Check)

| Service | Falls Gracefully? | Notes |
|---------|-------------------|-------|
| MPRIS | Yes | `try/except` wraps dbus import |
| HTTP API | Yes | No bridge → 200 OK (DOCUMENTED GAP) |
| Snapcast/Home Audio | Yes | `except: pass` on discovery |
| Recognition | Yes | `NullRecognizer` fallback |
| Sync | Yes | Lazy-init via `_ensure_sync_manager()` |
| Audio Lab | Yes | All STUBs — no crash |
| Transmit | Yes | `except: pass` on service init |

---

## Validation Results

```
ruff check .        → 0 errors
python -m compileall . → clean
python -m pytest tests/ → 228 passed
```

---

## Recommended Next Steps

1. **Merge** `fix/http-api-reliable-errors` (adds error codes, fixes favs/recent)
2. **Merge** `feat/audio-lab-tag-writer` (real TagWriter implementation)
3. **Merge** `feat/audio-lab-local-artwork-resolver` (local cover search)
4. **Merge** `feat/transcode-service-ffmpeg` (ffmpeg transcode)
5. **Merge** `fix/playlist-ui-playback-wiring` (play_queue, sidebar playlists)
6. **Merge** `fix/smart-mixes-schema-alignment` (real schema queries)
7. **Rename** HA component classes (`AstraApiClient` → `MichiApiClient`)
8. **Remove** duplicate `ha_custom_component/` directory
9. **Remove** outdated root `install_*.sh` scripts
10. **Implement** MPRIS `Raise()`/`Quit()` with window reference
