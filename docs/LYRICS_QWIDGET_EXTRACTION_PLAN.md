# Lyrics QWidget Extraction Plan

This document catalogs business logic found in QtWidgets files that must be extracted to `core/lyrics/` or `infrastructure/lyrics/` in future branches.

## Files to Extract

### `ui/lyrics_widget.py`

| Method | Responsibility | Target |
|--------|---------------|--------|
| `LyricsWidget.load_lyrics()` | Calls LrcLibClient directly | `LyricsService.resolve()` |
| `LyricsWidget.set_position()` | Tracks playback position | `LyricsTimeline.active_line()` |
| `LyricsWidget.set_duration()` | Stores duration | UI only — keep |
| `LyricsWidget._display` (paint) | Custom glassmorphism paint | UI only — keep |

### `ui/audio_lab/lyrics_page.py`

| Method | Responsibility | Target |
|--------|---------------|--------|
| `LyricsPage._search_lyrics()` | Direct LrcLibClient call | `LyricsService.search_candidates()` |
| `LyricsPage._search_sync()` | Sync HTTP call via WorkerManager | `LyricsService.resolve()` |
| `LyricsPage._save_lyrics()` | File write + tag write | `LyricsStorageService.save_sidecar()` |
| `LyricsPage._clear_lyrics()` | In-memory clear | `LyricsService.invalidate()` |

### `ui_qml_bridge/lyrics_bridge.py`

| Method | Responsibility | Target |
|--------|---------------|--------|
| `LyricsBridge._search_impl()` | HTTP + parsing + cache | `LyricsService.resolve()` |
| `LyricsBridge._parse_lrc()` | Duplicate parser | `core/lyrics/parser.py` |
| `LyricsBridge._cache` | In-memory LRU cache | `infrastructure/lyrics/cache_repository.py` |
| `LyricsBridge.saveLocalLyrics()` | In-memory save only | `LyricsStorageService.save_sidecar()` |
| `LyricsBridge.getActiveLine()` | Timeline lookup | `LyricsTimeline.active_line()` |
| `LyricsBridge.searchManual()` | Broken import + search | `LyricsService.search_candidates()` |

## Extraction Order

1. Replace `LyricsBridge._search_impl()` with `LyricsService.resolve()`
2. Replace `LyricsBridge._cache` with `SqliteLyricsCacheRepository`
3. Replace `LyricsBridge.saveLocalLyrics()` with `LyricsStorageService.save_sidecar()`
4. Replace `LyricsBridge.getActiveLine()` with `LyricsTimeline.active_line()`
5. Remove duplicate parser from bridge
6. Remove `LrcLibClient` direct usage from widget and audio lab
7. Migrate settings to `LyricsSettings` model
