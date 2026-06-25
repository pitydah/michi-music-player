# AGENTS.md — AI Assistant Context for Michi Music Player

## 1. Project Identity

**Michi Music Player** — Audiophile music player for Linux desktop (KDE Plasma / Qt 6).
Written in Python 3.11+ with PySide6, GStreamer 1.0, SQLite FTS5, mutagen, shazamio, PyAudio.

| Field | Value |
|-------|-------|
| License | GPL-3.0-or-later (derived from Miro Player — see NOTICE) |
| Repository | https://github.com/pitydah/michi-music-player |
| Python | 3.11+ |
| UI toolkit | PySide6 (Qt 6) — native widgets only, no QML, no Electron |
| Audio engine | GStreamer 1.28 (playbin, audioiirfilter, equalizer-nbands, rgvolume, tee, appsrc) |
| Database | SQLite 3 (WAL mode) + FTS5 full-text search |
| Metadata | mutagen (ID3, Vorbis, MP4, MusicBrainz, ReplayGain, BPM) |
| Recognition | shazamio, AudD HTTP API, AcoustID fpcalc + Chromaprint |
| Build system | pip install . / Flatpak |

## 2. Directory Structure

```
michi-music-player/
├── audio/          → Motor GStreamer: player.py, player_service.py,
│                     pipeline_factory.py, dac_manager.py, eq_*.py, replaygain.py,
│                     quality_classifier.py, dsp_state.py, output_profiles.py (9 perfiles)
├── library/        → SQLite + indexer: library_db.py, indexer.py, search_engine.py,
│                     coverflow.py, media_item.py, album_key.py
├── recognition/    → Identificación: detection_service.py, providers/shazam|audd|acoustid
├── integrations/   → home_assistant/, snapcast/, michi_api/, artist_metadata/
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

### Key Glue Files (connectors between layers)

| File | Role |
|------|------|
| `ui/window.py:937-1212` | `_on_sidebar_navigate()` — dispatches ALL sidebar clicks to views (giant if/elif chain) |
| `ui/sidebar_controller.py:18-69` | `rebuild()` — builds 7 sidebar sections and all items in order |
| `core/app_context.py` | DI container — all controllers access services via `ctx` |
| `ui/icon_registry.py` | Source of truth for all 38+ icons (key, path, family, render_mode) |
| `core/settings_manager.py` | QSettings wrapper — `DEFAULTS` dict has all config keys; `get()`/`set_()` API |
| `ui/window.py:110-127` | `SECTION_CONFIG` — header titles, icons, views, search visibility per section |
| `ui/window.py:28` | `VIEW_MODE_DEFS` — view mode configs for the view switcher |

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

### Icon Resolution Chain
Understanding how an icon key like `"home_audio"` becomes a visible QPixmap:

1. **Registry lookup** — `icon_registry.py` → `IconSpec(key="home_audio", path="icons/sidebar/home-audio.svg", render_mode="native_color")`
2. **Path resolution** — `icon_path("home_audio")` → resolves relative path to absolute filesystem path
3. **Loader dispatch** — `get_sidebar_icon("home_audio")` detects `.svg` + `render_mode == "native_color"`
4. **Safe render** — `render_svg_icon(path, size, padding=2)` → QImage 4x supersampling + dual-pass alpha sanitize → QPixmap
5. **Widget display** — `SidebarItem._load_icon()` → `QLabel.setPixmap(pix)`

For tinted SVGs (`render_mode="symbolic_tint"`): step 4 uses `_tinted_pixmap()` with `CompositionMode_SourceIn` + a `QColor` from `SIDEBAR_NORMAL/HOVER/ACTIVE`.

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

## 10. Key Data Flows

### Playback
```
sidebar click → _on_sidebar_navigate("library")
  → _apply_filters() → table populated
  → table double-click → _on_table_dbl → _play_file(fp)
  → PlayerService.play(fp)
    → GStreamerEngine.play()
      → probe_format(filepath)
      → get_profile(audio_profile)
      → DspState(eq, replaygain, spectrum, transmit)
      → DacManager.select_output_route(fmt, profile, device)
      → PipelineFactory.build_for_uri(uri, fmt, route, dsp, transmit_device)
        → _make_sink_bin() [queue→volume→EQ→convert→tee→output+spectrum+transmit]
      → Gst.Pipeline.set_state(PLAYING) → audio output
```

### Search (FTS5 + field filters)
```
search box textChanged → _on_search(text)
  → _apply_filters()
    → SearchController.search(text)
      → LocalSource.search(text)
        → SearchEngine.search(text)
          → SearchIndex.search_fts(text) [FTS5 MATCH with prefix *]
          → OR SearchIndex.search_like(text) [LIKE fallback]
        → results as dicts → TrackRef list
    → TrackRefTableModel.populate(refs)
    → QTableView updated

Field filters: artist:Genesis album:"Lamb" format:flac year:>2000 bitrate:>=320
Parsed by query_parser.py → SQL WHERE clauses with numeric operators
```

### Scanning (Indexer 2.0)
```
folder add → FileActions.scan_path(path)
  → Indexer.from_db_path(path).run()
    → Phase 1: _walk_files() [ignore hidden dirs]
    → Phase 2: ChangeDetector [skip unchanged: size + mtime match]
    → Phase 3: MetadataExtractor [GStreamer + mutagen]
    → Phase 4: AlbumKeyBuilder [SHA1 key per album]
    → Phase 5: BatchWriter.add(record) [flush every 100]
    → Phase 6: _rebuild_indexes() + rebuild_fts()
    → Phase 7: _schedule_enrichment() [TheAudioDB artist enrichment]
  → _on_done: load_library() + reset CoverFlow cache + Toast
```

### Navigation
```
sidebar item clicked
  → SidebarItem.clicked.emit(key) [e.g. "home_audio"]
  → SidebarController._on_item_click(key)
    → navigation_requested.emit(key)
  → window._on_sidebar_navigate(key) [giant if/elif chain, line 937]
    → _configure_header_for_section(section_key)
      → reads SECTION_CONFIG dict for title/subtitle/icon/views/search
      → updates header labels + icon + search placeholder
    → _views.show(view_name) [switches QStackedWidget]
```

### Radio (station playback + filtering)
```
radio view shown → _on_sidebar_navigate("radio")
  → _radio_widget.reload()
  → RadioWidget._load_stations() → filter by _filter_text → render cards

search in radio → _on_search(text)
  → _radio_widget.set_filter(text) → filters cards in-place (never switches to table)

station click → RadioWidget.station_selected.emit(url, name)
  → window._play_radio(url, name)
    → TrackRef(source_type="radio", source_label=name)
    → GStreamerEngine.play_url(url)
```

### Recognition (continuous identification)
```
stream starts → IdentifierController.set_current_track(source_type="radio", ...)
  → _should_listen("radio") → True → _start_listening()
  → DetectionService.start()
    → creates AudioCaptureService + QTimer(15s)
    → every 15s: identify_once()
      → capture PCM bytes (22050Hz mono S16LE)
      → recognizer.identify(sample_bytes) [ShazamIO/AudD/AcoustID]
      → if match → _on_detection_result → RecognitionMatcher → history

local file starts → IdentifierController.set_current_track(source_type="local_file", ...)
  → _should_listen("local_file") → False → _pause("Archivo local: Michi ya conoce sus metadatos")
```

## 11. Common Tasks

### Add a sidebar item
1. `ui/sidebar_controller.py:rebuild()` — add `add_section()` + `add_item()` call
2. Icon: register in `ui/icon_registry.py` (PNG or SVG with correct `render_mode`)
3. Navigation: add `elif key == "my_key":` in `window.py:_on_sidebar_navigate()` (line ~937)
4. Header config: add entry in `SECTION_CONFIG` dict (`window.py` line ~110)
5. View: register in `window.py:_views.register("my_view", widget)` (line ~720)

### Add a new QSS style
1. Define function in `ui/central/central_styles.py` or `ui/sidebar/sidebar_styles.py`
2. Return the QSS string — use the central/sidebar tokens for colors/radii
3. Never write inline QSS in widget files — always `widget.setStyleSheet(my_qss())`

### Add a new icon
1. Place file in `icons/` subdirectory (SVG or PNG at multiple sizes: 24/48/64/128px)
2. Register in `ui/icon_registry.py`:
   ```python
   "my_icon": IconSpec(key="my_icon", path="icons/my_icon.svg",
       family="sidebar", render_mode="native_color", description="My Icon")
   ```
3. Use via `get_qicon("my_icon")`, `get_pixmap("my_icon")`, or `get_sidebar_icon("my_icon")`
4. SVG `render_mode`: `"native_color"` for colored SVGs, `"symbolic_tint"` for monochrome tint

### Add a settings key
1. Add default to `core/settings_manager.py:DEFAULTS` dict (line ~10-110)
2. Read: `from core.settings_manager import get; value = get("category/key")`
3. Write: `from core.settings_manager import set_; set_("category/key", value)`
4. Add UI control in `ui/settings_pages.py` — extend the appropriate `SettingsPage` subclass

### Add a new audio profile
1. Define in `audio/output_profiles.py:PROFILES` dict
2. Set properties: `allows_eq`, `allows_replaygain`, `bitperfect`, `dsd_mode`, `preferred_backend`, `allows_transmit`
3. The profile is available immediately via `get_profile("key")`

### Debug stale cache
```bash
# If code changes don't appear at runtime:
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null
python3 -m compileall -q .
python3 main.py
```

### Run before every commit
```bash
ruff check . --output-format concise     # must be 0
python -m compileall -q .                # must be clean
python -m pytest tests/ -q               # must be 206 passed
```
