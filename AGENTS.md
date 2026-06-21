# AGENTS.md — AI Assistant Context for Astra Music Player

## 1. Project Identity

**Astra Music Player** — Audiophile music player for Linux desktop (KDE Plasma / Qt 6).
Written in Python 3.11+ with PySide6, GStreamer 1.0, SQLite FTS5, mutagen, shazamio, PyAudio.

| Field | Value |
|-------|-------|
| License | GPL-3.0-or-later (derived from Miro Player — see NOTICE) |
| Repository | https://github.com/pitydah/astra-music-player |
| Python | 3.11+ |
| UI toolkit | PySide6 (Qt 6) — native widgets only, no QML, no Electron |
| Audio engine | GStreamer 1.28 (playbin, audioiirfilter, equalizer-nbands, rgvolume, tee, appsrc) |
| Database | SQLite 3 (WAL mode) + FTS5 full-text search |
| Metadata | mutagen (ID3, Vorbis, MP4, MusicBrainz, ReplayGain, BPM) |
| Recognition | shazamio, AudD HTTP API, AcoustID fpcalc + Chromaprint |
| Build system | pip install . / Flatpak |

## 2. Directory Structure

```
astra-music-player/
├── audio/          → Motor GStreamer: player.py, player_service.py,
│                     pipeline_factory.py, dac_manager.py, eq_*.py, replaygain.py,
│                     quality_classifier.py, dsp_state.py, output_profiles.py (9 perfiles)
├── library/        → SQLite + indexer: library_db.py, indexer.py, search_engine.py,
│                     coverflow.py, media_item.py, album_key.py
├── recognition/    → Identificación: detection_service.py, providers/shazam|audd|acoustid
├── integrations/   → home_assistant/, snapcast/, astra_api/, theaudiodb/
├── ui/             → window.py (MainWindow, 2644 lines), controllers/ (14 controladores),
│                     style_tokens.py, qss.py, icon_registry.py, icon_loader.py,
│                     central/ (central_styles.py, central_tokens.py),
│                     sidebar/ (7 módulos: tokens, styles, item, section, panel, brand, search)
├── core/           → app_context.py (DI container), interfaces.py, settings_manager.py,
│                     playback_controller.py, file_actions.py
├── sources/        → base_source.py, local_source.py, radio_source.py, subsonic_source.py
├── streaming/      → subsonic_client.py, radio_manager.py, transmit_manager.py
├── sync/           → Android REST API + UDP multicast discovery
├── lyrics/         → lrclib_client.py
├── metadata/       → album_info_repository.py (LRU 200 + SQLite fallback)
├── tests/          → **206 tests** in 25 files (pytest)
├── docs/           → architecture.md, roadmap.md
├── icons/          → 38+ icons (SVG + PNG, sidebar_clean/, sidebar/, nowplaying_clean/, radio/)
└── AGENTS.md       → This file
```

**Total:** 242 Python files · 206 tests · 14 controllers · 9 audio profiles · 3 recognition providers

## 3. Architectural Patterns — MUST FOLLOW

### Dependency Injection
- All dependencies obtained from `AppContext` (`core/app_context.py`)
- NEVER access `window` directly from a controller
- Controllers receive `ctx: AppContext` in `__init__`, not raw widget references
- Pattern: `self._ctx = ctx; self._ctx.playback.toggle()`

### PlayerService as Single Facade
- UI NEVER touches `GStreamerEngine` directly
- All audio operations go through `PlayerService` (`audio/player_service.py`)
- 7+ public wrappers: play, pause, stop, seek, next, prev, set_volume, set_eq_graphic, set_eq_parametric, set_eq_bypass, set_eq_preamp, set_transmit_device, set_output_device_id, set_spectrum_enabled
- 0 accesses to private engine attributes from outside `player_service.py`

### Controllers (ui/controllers/)
- One controller per functional domain (14 total)
- Receive only `AppContext`, not widget references
- Emit Qt `Signal` for communication — never call UI methods directly
- NO business logic in controllers — delegate to services

### Qt Signals
- Naming: `track_changed`, `playback_started`, `library_scanned`, `navigation_requested`
- Use `Signal` from PySide6 for cross-layer communication

## 4. Code Conventions

### Style
- Ruff with default config — **0 violations tolerated**
- Type hints on ALL public functions
- Docstrings on classes and complex methods (Google style)
- f-strings for interpolation — never `.format()` or `%`

### Naming
- Classes: `PascalCase` → `GStreamerEngine`, `AlbumInfoBanner`
- Functions/methods: `snake_case` → `get_album_key()`, `apply_replaygain()`
- Constants: `UPPER_SNAKE` → `DEFAULT_BUFFER_SIZE`, `MAX_RETRY`
- Files: `snake_case` → `pipeline_factory.py`, `dsp_state.py`

### SQLite
- WAL mode enabled in `library_db.py`
- Heavy operations in separate thread (`QThread` / `ThreadPoolExecutor`)
- `BatchWriter` for bulk inserts (batches of 100)
- FTS5 for full-text search — **never use LIKE for text searches**
- `search_advanced()` wraps `SearchEngine` → FTS5 with field filters

### GStreamer
- Pipelines built by `PipelineFactory` per audio profile
- DSP state tracked in `DspState` dataclass
- Pipeline changes: PAUSED → modify → PLAYING (never NULL in between)
- Errors: capture in bus message handler, emit Qt signal
- All `set_state()` calls MUST check `StateChangeReturn.FAILURE`
- NULL transition MUST call `get_state(CLOCK_TIME_NONE)` before disposal

### Qt / PySide6
- `moveToThread()` for heavy workers
- `deleteLater()` to clean up Qt objects
- NEVER use `time.sleep()` on main thread — use `QTimer`
- `QSettings` for preferences via `core/settings_manager.py`

## 5. Visual Rules — ABSOLUTE

### Colors
```
Accent:            #8FB7FF (cool blue only)
Accent faint:      rgba(143,183,255,0.34)
FORBIDDEN:         #FF7A00, magenta, pink, red, neon, orange
```

### Glassmorphism
```css
/* Background: solid dark */
background: #090B11;
/* OR translucent overlay */
background: rgba(255,255,255,0.045);
/* OR gradient */
qlineargradient(x1:0, y1:0, x2:0, y2:1,
  stop:0 rgba(255,255,255,0.065), stop:1 rgba(255,255,255,0.025));
/* Border: always translucent white */
border: 1px solid rgba(255,255,255,0.08);
/* Border hover: */
border: 1px solid rgba(143,183,255,0.28);
```

### Text Opacity — Minimum Values
```
Navigation items:  rgba(255,255,255,0.85)
Section headers:   rgba(255,255,255,0.88)
Item hover:        rgba(255,255,255,0.96)
Item active:       rgba(255,255,255,1.00)
Subtitles:         rgba(255,255,255,0.62)
Muted:             rgba(255,255,255,0.52)
Font weights:      bold, 500, 600, 700 (valid CSS — no 540/680/720/760)
```

### Icon Loading — ALWAYS Alpha-Safe
```python
# Correct:
from ui.icons import get_qicon, get_pixmap
from ui.icon_loader import get_sidebar_icon
icon = get_qicon("key", size=24)
pix = get_pixmap("key", size=24)
pix = get_sidebar_icon("key", active=False, size=24)

# NEVER (bypasses alpha-safe renderer producing black borders):
QIcon(path)
QPixmap(path)
QIcon(get_icon(key))
```

### QSS — Always Centralized
```python
# Correct:
widget.setStyleSheet(table_qss() + scrollbar_qss())

# Never:
widget.setStyleSheet("""QTableView { background: ... }""")  # inline QSS
```

## 6. Testing

### Framework & Rules
- Framework: pytest
- Mocks: `unittest.mock` (`MagicMock`, `patch`)
- Each new module must have `tests/test_<module>.py`
- GStreamer: mock `Gst.Pipeline`, never create real pipelines in tests
- SQLite: use `:memory:`, never touch real DB
- Run before commit: `python -m pytest tests/ -q`

### Quick Commands
```bash
ruff check . --output-format concise    # lint
python -m compileall -q .               # compile check
python -m pytest tests/ -q              # tests (206 expected)
find . -type d -name "__pycache__" -exec rm -rf {} +   # clear stale cache
python main.py                          # run app
```

## 7. Dependencies

**System (apt):**
```
python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-plugins-*
avahi-utils fpcalc (chromaprint) pactl (PulseAudio/PipeWire) dbus-python
```

**Python (requirements.txt):**
```
PySide6 mutagen numpy shazamio pyaudio requests
```

## 8. What NOT to Do

### Quality
- No generic "helper" files without a clear owner module
- No business logic in `window.py` — goes in controllers or services
- No `threading.Thread` — use `QThread` or `ThreadPoolExecutor`
- No GStreamer imports in UI layers directly
- No breaking `PlayerService` encapsulation
- No new dependencies without updating `requirements.txt` and `install_*.sh`

### Modules NOT to Touch (without explicit need)
- Sidebar layout/structure
- NowPlayingBar layout/structure
- CoverFlow 3D
- Audio engine core (`player.py` playback logic)
- Home Audio view (except visual fixes)
- PlayerService public API
- PlaybackController core logic
- QStackedWidget global structure

### Visual
- No orange, pink, magenta, red, neon anywhere
- No `QIcon(path)` / `QPixmap(path)` for SVGs — use `get_qicon()` / `get_pixmap()`
- No inline QSS in `window.py` or widget files — use `central_styles.py` / `sidebar_styles.py`
- No text opacity below 0.78 for navigation

## 9. Current State

| Metric | Value |
|--------|-------|
| Tests | **206** in 25 files |
| Python files | **242** |
| Ruff | **0** |
| Bugs (F-class) | **0** |
| Stubs | **0** |
| Dead code | **0** |
| Audio profiles | **9** |
| Controllers | **14** |
| Recognition providers | **3 real** (ShazamIO, AudD, AcoustID) |
| Icons registered | **38+** |

**Last commits:**
```
f219611 fix: extend SVG alpha-safe renderer to entire app
5730faa fix: sidebar section headers — white text 0.88
6233287 fix: SVG native_color — remove pure black pixels + edge cleanup
9614995 fix: Home Audio — own sidebar section + transparent background
```
