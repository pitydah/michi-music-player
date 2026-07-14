# Lyrics Core V2 — Baseline Audit

**HEAD:** c73c76a Macrofases AI-BM: Segunda convergencia masiva QML

## Files Audited

| File | Lines | Role |
|------|-------|------|
| `lyrics/lrclib_client.py` | 152 | LRC HTTP client, parser, in-memory cache, throttling |
| `lyrics/__init__.py` | 0 | Empty |
| `ui/lyrics_widget.py` | 204 | QtWidgets synced lyrics display |
| `ui/audio_lab/lyrics_page.py` | 295 | Audio Lab lyrics search/edit/save |
| `ui_qml_bridge/lyrics_bridge.py` | 332 | QML bridge with duplicate parser and cache |
| `ui_qml/pages/lyrics/LyricsPage.qml` | 187 | QML lyrics page |
| `ui_qml/pages/LyricsPage.qml` | ~150 | Duplicate legacy QML page |
| `ui_qml/components/SyncedLyricsView.qml` | 116 | Synced scroll component |
| `tests/test_lrclib_client.py` | 298 | Unit tests for LrcLibClient |
| `tests/test_lyrics_page.py` | 19 | Nav route contract test |
| `tests/test_audio_lab_lyrics.py` | 29 | Render/no-crash tests |
| `tests/qml/lyrics/test_lyrics_workflow.py` | 96 | Bridge unit tests |
| `metadata/tag_reader.py` | L116-122 | Reads USLT into TrackTags.lyrics |
| `metadata/tag_writer.py` | L30, L46 | Writes lyrics to tags |
| `core/settings_schema.py` | L284, L308-319 | Lyrics settings keys defined |

## Current Public API

### `lyrics.lrclib_client.LrcLibClient`
- `get_lyrics(title, artist, album, duration) -> Optional[LyricsResult]`
- `search(query) -> list[LyricsResult]`
- `_parse(data) -> Optional[LyricsResult]` (internal)
- `_parse_lrc(lrc_text) -> list[LyricLine]` (static)

### Data models
- `LyricLine(timestamp: float, text: str)`
- `LyricsResult(lines: list[LyricLine], plain: str, source: str)`

### Providers
- Only LRCLIB (lrclib.net), no Genius or Musixmatch despite schema
- Rate limiting via `time.sleep()` (blocking)
- Generic `except Exception: return None` on errors

### Cache
- `LrcLibClient._cache`: in-memory dict, unbounded, key=(title.lower(), artist.lower())
- `LyricsBridge._cache`: in-memory dict, LRU-50, key="title||artist||album||duration"
- No disk persistence despite setting `lyrics/cache_days=30`

### Parsers
- Parser 1: `LrcLibClient._parse_lrc()` — typed, multi-timestamp, sorted
- Parser 2: `lyrics_bridge._parse_lrc()` — raw dicts, less robust
- Parser 3: `LyricsResult._parse()` — implicit, generates artificial timestamps for plain text

### Critical Bugs
1. `lyrics_bridge.py:272`: imports non-existent `search_lyrics` from `lyrics.lrclib_client`
2. `lyrics_bridge.py:34-35`: accesses `result.plain_lyrics` and `result.synced_lyrics` which don't exist

### Duplications
- Two parsers (lrclib_client.py:100 vs lyrics_bridge.py:45)
- Two caches (LrcLibClient._cache vs LyricsBridge._cache)
- Two QML LyricsPage.qml files (pages/ vs pages/lyrics/)
- Two LyricLine representations (dataclass vs dict)

### Missing Features
- Disk persistence
- Sidecar .lrc file support
- Multi-provider resolution
- Track matching/fuzzy matching
- Attribution policy
- Offline mode
- Cancellation (partial in bridge only)
- Sync offset persistence
- Editor undo/redo

### Risks
- Blocking sleep in sync path blocks UI thread
- Unbounded memory cache
- W3_LEGACY_ONLY status for widget path
- Broken import path in searchManual()

## Compatibility Plan
- Legacy `LrcLibClient` wrapper delegates to new `LrcLibProvider`
- `LyricsResult` and `LyricLine` maintained as aliases
- New typed models added in parallel
- Bridge and widget code NOT modified in this branch
