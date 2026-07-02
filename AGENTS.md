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
| Audio engine | Hybrid: GStreamer 1.28 (default) + MPD (Hi-Fi/bit-perfect) |
| Hybrid engine | `audio/backends/` — `AudioBackend` API, `GStreamerBackend`, `MpdBackend`, `HybridAudioManager` |
| Database | SQLite 3 (WAL mode) + FTS5 full-text search |
| Metadata | mutagen (ID3, Vorbis, MP4, MusicBrainz, ReplayGain, BPM) |
| Recognition | shazamio, AudD HTTP API, AcoustID fpcalc + Chromaprint |
| Audio analysis | librosa, soundfile, numpy (feature extraction, acoustic profiling) |
| Smart mixes | recommendation engine based on acoustic features + play counts |
| Build system | pip install . / Flatpak |
| Tests | **~950** (pytest + pytest-qt) |

## 2. Directory Structure

```
michi-music-player/
├── audio/          → Motor híbrido GStreamer + MPD
│   ├── player.py, player_service.py → GStreamerEngine + PlayerService (fachada)
│   ├── pipeline_factory.py, dac_manager.py → construcción de pipelines GStreamer
│   ├── backends/   → AudioBackend API, GStreamerBackend, MpdBackend, HybridAudioManager
│   ├── mpd/        → mpd_client.py, mpd_protocol.py, mpd_path_mapper.py,
│   │                 mpd_config_builder.py, mpd_service_manager.py, mpd_discovery.py
│   ├── diagnostics/ → alsa_hw_params.py, bitperfect_verifier.py, bitperfect_report.py
│   ├── settings/   → audio_settings_schema.py, audio_settings_migrator.py
│   ├── eq_*.py, replaygain.py, quality_classifier.py, dsp_state.py, etc.
│   └── output_profiles.py (13 perfiles, 4 MPD)
├── library/        → SQLite + indexer: library_db.py, indexer.py, search_engine.py,
│                     coverflow.py, media_item.py, album_key.py,
│                     folder_index.py, folder_models.py, folder_health.py,
│                     folder_integrity.py
├── recognition/    → Identificación: detection_service.py, providers/shazam|audd|acoustid
├── integrations/   → home_assistant/, snapcast/, michi_api/, artist_metadata/
├── ui/             → window.py (MainWindow), controllers/ (15 controladores),
│                     folder_browser.py, folders/folder_problem_report.py,
│                     style_tokens.py, qss.py, icon_registry.py, icon_loader.py,
│                     central/ (central_styles.py, central_tokens.py),
│                     sidebar/ (7 módulos: tokens, styles, item, section, panel, brand, search)
├── core/           → app_context.py (DI container), interfaces.py, settings_manager.py,
│                     playback_controller.py, file_actions.py,
│                     file_manager_service.py, safe_file_ops.py,
│                     home/ (home_status.py dataclasses, home_dashboard_service.py),
│                     audio_lab/ (diagnostics_helpers.py)
├── sources/        → base_source.py, local_source.py, radio_source.py, subsonic_source.py
├── streaming/      → subsonic_client.py, radio_manager.py, transmit_manager.py
├── sync/           → Android REST API + UDP multicast discovery
├── lyrics/         → lrclib_client.py
├── metadata/       → album_info_repository.py (LRU 200 + SQLite fallback)
├── tests/          → pytest + pytest-qt suite (run: pytest -q)
├── docs/           → architecture.md, roadmap.md
├── icons/          → 38+ icons (SVG + PNG, sidebar_clean/, sidebar/, nowplaying_clean/, radio/)
└── AGENTS.md       → This file
```

**Total:** 15 controllers · 9 audio profiles · 3 recognition providers
**Verify:** `ruff check .` · `python -m compileall -q .` · `pytest -q`
**Note:** Do not trust handwritten test/file counts — run the commands above.

## 3. Architectural Patterns — MUST FOLLOW (migration in progress)

### Dependency Injection
- Preferred: `AppContext` (`core/app_context.py`) and `AppServices` (`core/app_services.py`)
- Current state: controllers store `self._ctx` directly; `self._win` retained for Qt parent/widget needs
- Pattern: `self._ctx.playback.toggle()`
- Migration: controllers that receive `ctx` should stop accessing `self._win._ctx`

### Hybrid Audio Engine Architecture
```
UI → PlayerService → HybridAudioManager
                        ├── GStreamerBackend → GStreamerEngine (default, DSP, visual)
                        └── MpdBackend → MPD (Hi-Fi, bit-perfect, DSD/DoP)
```
- Active backend chosen automatically by audio profile (13 profiles, 4 MPD)
- Fallback: if MPD unavailable, GStreamer is used with warning
- Queue is canonical in Michi, synced to MPD when MPD backend is active
- `audio/backends/` — `AudioBackend` Protocol, `GStreamerBackend`, `MpdBackend`, `HybridAudioManager`
- `audio/diagnostics/` — bit-perfect verifier reads `/proc/asound/*/hw_params`
- `audio/mpd/` — TCP client, protocol parser, path mapper, config builder, service manager
- `audio/settings/` — canonical audio settings schema with legacy migration
- Blocked DSP in MPD mode: EQ, ReplayGain, Spectrum emit errors
- MPRIS adapter uses `PlayerService` when MPD is active
- Radio/streams always force GStreamer regardless of backend

### PlayerService as Single Facade
- UI NEVER touches `GStreamerEngine` or `MpdBackend` directly
- All audio operations go through `PlayerService` (`audio/player_service.py`)
- Public wrappers: play, pause, stop, seek, next, prev, set_volume, get_eq_state,
  set_eq_graphic, set_eq_parametric, set_eq_bypass, set_eq_preamp,
  set_transmit_device, set_output_device_id, set_spectrum_enabled,
  switch_backend_for_profile, get_active_backend_id, start_mpd_service, etc.
- Private engine attributes accessed only from `player_service.py`

### Controllers (ui/controllers/)
- One controller per functional domain (14 total)
- Progressive migration toward `AppContext` + `AppServices` DI
- Emit Qt `Signal` for communication — never call UI methods directly
- NO business logic in controllers — delegate to services
- `window.py` is still the main orchestrator; avoid massive refactors without tests

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
Accent:            #8FB7FF (primary cool blue)
Accent faint:      rgba(143,183,255,0.34)
NowPlaying accent: #FF7A00 (warm palette for player bar sliders and EQ bands)
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
python -m compileall -q -x '.venv/|\.tmpl\.' .               # compile check
python -m pytest tests/ -q              # tests (pytest suite)
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

### Home Dashboard Rules
- `HomeDashboardService` is the orchestrator; keep it lean — delegate to builders
- `HomePage` renders snapshots only — no DB queries, no state logic
- **NEVER** declare `bitperfect_state = "verified"` — there is no real monitor; use `intended` at most
- **NEVER** mark `dac_active = True` based on profile name alone — use device name heuristics (keywords list)
- Micro Server detection uses `MichiLinkController`, **NOT** `streaming.subsonic_client`
- `can_continue_remote` requires: playback.can_continue + connected + contract_ok + can_continue_playback
- Assistant suggestions with `requires_confirmation=True` for destructive actions (metadata edits, artwork, sync)
- Safe mode: filter experimental features, show badge, disable remote capabilities
- Always test: `tests/test_home_dashboard_service.py`, `tests/test_home_page.py`, `tests/test_home_routes_contract.py`
- Before touching Home: `pytest tests/test_home_*.py -q` must pass

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
- `QIcon(path)` / `QPixmap(path)` bypasses alpha-safe renderer — always use `get_qicon()` / `get_pixmap()` for SVGs
- No inline QSS in `window.py` or widget files — use `central_styles.py` / `sidebar_styles.py`
- No text opacity below 0.78 for navigation
- Warm palette (`#FF7A00` naranja, fucsia, magenta) is reserved for NowPlayingBar sliders and EQ bands only. Do not use warm colors for sidebar, cards, buttons, headers or navigation.
- Cool blue `#8FB7FF` is the primary accent for all other UI (navigation, cards, buttons, headers, selection, focus).

## 9. Current State

| Metric | Value |
|--------|-------|
| Ruff | **0** (verificar con `ruff check .`) |
| Tests | **~950** (verificar con `pytest -q`)
| Bugs (F-class) | **0** |
| Stubs | **0** |
| Dead code | **0** |
| Audio profiles | **9** |
| Controllers | **15** (with Qt Signals, DI via AppContext/AppServices) |
| Recognition providers | **3 real** (ShazamIO, AudD, AcoustID) |
| Icons registered | **38+** |
| NAV_ROUTES validated | ✅ startup `RuntimeError` on stale routes |
| XDG paths consolidated | ✅ all via `core.paths` |
| System deps documented | ✅ PyGObject/pycairo/dbus-python via system, not pip |
| `sqlite3.connect(DB_PATH)` bypass removed | ✅ all via `core.paths.database_path()` |
| Home Dashboard dataclasses | ✅ `core/home/home_status.py` (9 dataclasses) |
| Home Dashboard service | ✅ `core/home/home_dashboard_service.py` (10 builder methods) |
| Home 7-card design | ✅ `ui/hubs/home_page.py` (render_snapshot entry point) |
| Spectral FLAC support | ✅ `core/audio_analysis/spectral_authenticator.py:can_analyse()` |

**Installation:**
```
./scripts/install.sh              # unified distro auto-detection (Arch, Debian, Fedora, openSUSE)
./scripts/install.sh --minimal    # core only, no optional deps
./scripts/install.sh --no-venv    # system deps only
./scripts/run_from_source.sh      # run without system install
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

### Home Dashboard (Centro de Situación)
```
sidebar "Inicio" click → SidebarController → navigation_requested.emit("home")
  → MainWindow._on_sidebar_navigate("home") → NavigationController.dispatch("home")
    → configure_header("Inicio") → MainWindow._show_home_page()
      → HomeController.show()
        → _ensure_page() → HomePage()
        → _ensure_service() → HomeDashboardService(db, playback, context_svc, ...)
        → refresh()
          → HomeDashboardService.build_snapshot()
            → _build_library_status() [ContextService → DB fallback]
            → _build_playback_status() [PlayerService state + queue]
            → _build_audio_status() [engine + settings]
            → _build_ecosystem_status() [servers + sync + API]
            → _build_alerts() [max 5, critical > warning > info]
            → _build_assistant_suggestions() [max 3, ContextService → basic]
            → _derive_overall_state() [ready/empty_library/playback_active/...]
            → _format_headline() + _format_subtitle()
          → HomeDashboardSnapshot typed dataclass
        → HomePage.render_snapshot(snapshot)
          → _render_status() [headline + badges]
          → _render_playback() [Continuar card]
          → _render_library() [Biblioteca card with metrics]
          → _render_audio() [Audio card with output/DSP]
          → _render_ecosystem() [Ecosistema Michi card]
          → _render_alerts() [Atención requerida card, 5 max]
          → _render_assistant() [Michi Assistant card, 3 suggestions]
          → _render_add_music() [contextual, visible on empty]
```

Each card tolerates partial failure without breaking the dashboard.
Snapshot built every time the user navigates to Inicio.

**HomeDashboardSnapshot** (`core/home/home_status.py`):
- `overall_state`: ready | empty_library | playback_active | needs_attention | safe_mode | limited_services | error
- `library`: LibraryHomeStatus (track/album/artist/genre counts, health)
- `playback`: PlaybackHomeStatus (current track, queue, state)
- `audio`: AudioHomeStatus (output device, profile, DSP, bit-perfect)
- `ecosystem`: EcosystemHomeStatus (Micro Server, mobile sync, API, Home Audio)
- `alerts`: list[HomeAlert] (prioritized, actionable, max 5)
- `assistant_suggestions`: list[AssistantSuggestion] (contextual, max 3)
- `actions`: list[HomeAction] (quick actions based on state)

**Key files:**
- `core/home/home_status.py` — 9 dataclasses
- `core/home/home_dashboard_service.py` — HomeDashboardService
- `ui/controllers/home_controller.py` — orchestration
- `ui/hubs/home_page.py` — 7 glass cards, render_snapshot()

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
python -m compileall -q -x '.venv/|\.tmpl\.' .                # must be clean
python -m pytest tests/ -q               # must pass
```

## 12. Protected Files — Risk of Silent Regression

These files have an **integrity guard** at the module level that raises `AssertionError` at import time if the file is reverted to an incompatible version. Do NOT remove or modify this guard without also updating all callers:

| File | Protected Signature | Guard Location |
|---|---|---|
| `ui/audio_lab/diagnostics_page.py` | `DiagnosticsPage.__init__(self, worker_mgr=None, job_manager=None, db=None)` | End of file |

### Symptoms of regression
If `DiagnosticsPage` loses its `worker_mgr`/`job_manager`/`db` kwargs:
1. **Import-time crash**: `AssertionError` with message "IntegrityError: DiagnosticsPage.__init__ must accept worker_mgr= kwarg"
2. **Silent fallback**: `AudioLabDiagnosticsPage._inner` becomes `None`, showing "Diagnóstico no disponible" in the UI
3. **Test failure**: `test_diagnostics_page_renders` asserts `page._inner is not None`

### How regression happened historically
Commits outside the Audio Lab scope that touch `ui/audio_lab/diagnostics_page.py` can contain a stale 400-line version of the file that lacks the required constructor. This was overwritten 3 times by `refactor(inicio)` and `refactor` commits. The integrity guard prevents this from happening silently.

### How to safely modify DiagnosticsPage
1. Keep the constructor signature: `def __init__(self, worker_mgr=None, job_manager=None, db=None):`
2. Keep `diagnostics_updated = Signal(list)` and `navigate_requested = Signal(str)`
3. Keep the `# INTEGRITY GUARD` block at the end of the file
4. If you need to add/remove constructor params, update the guard accordingly and update `AudioLabDiagnosticsPage` in `ui/audio_lab/sub_pages.py`

## 13. QML Migration Rules (for AI assistants)

### Architecture
- QML does NOT access the database directly
- QML emits intention; Python executes
- Bridges (ui_qml_bridge/) are the only communication layer between QML and Python
- Python remains the brain; QML is the premium skin

### Protected Files — QML Migration
- `ui_qml/` is the new QML UI layer (experimental, parallel)
- `ui_qml_bridge/` is the Python bridge layer
- Do NOT touch `ui/devices_page.py`, `sync/`, `ui/nowplaying_bar.py`, `ui/source_status_badge.py`
- Do NOT touch playback logic (`audio/player.py`, `audio/player_service.py`, `audio/pipeline_factory.py`, `core/playback_controller.py`)
- Do NOT touch Android integration or sync protocol
- Keep fallback QtWidgets intact

### Visual Rules (QML)
- No `opacity` on parent containers with text
- No blur on lists/grids/tables
- No per-item shadows in lists/grids/tables
- Theme tokens preferred over hardcoded colors
- No fake data shown as real — use "No configurado", "Demo QML", "Experimental"

### How to run
```bash
# QML experimental
python -m ui_qml_bridge.qml_main
python main.py --qml

# Classic app
python main.py

# Tests
python -m pytest tests/qml/ -q    # 60 tests
ruff check ./ui_qml ./ui_qml_bridge ./tests/qml
python scripts/check_no_touch_contract.py
```

### Current QML Status (Jul 2026)
- **99+ tests** — bridges, structural, emoji/sidebar prohibition, Library, Michi AI, CoverBridge, MetadataBridge, Audio Lab
- **0 ruff errors** in QML/bridge/tests
- **0 compileall errors** in QML/bridge/tests
- **Sidebar final** (10 items): Inicio, Biblioteca, Mix, Reproducción, Conexiones, Radio, Playlists, Home Audio, Michi AI, Audio Lab
- **Labels**: No "Settings", no "Ajustes", no "Asistente". "Michi AI" as visible label, "assistant" as internal route
- **PageStack** with explicit radio/playlists → PlaceholderPage, no settings
- **NavigationBridge** with VALID_ROUTES, invalid routes → placeholder
- **Library QML**: LibraryPage with tabs (Songs/Albums), SongTable, AlbumGrid, LibraryBridge
- **Michi AI real**: ChatBubble, SuggestionCard, AssistantPage with functional chat and contextual suggestions
- **Placeholders**: Radio ("sección de streaming y emisoras"), Playlists ("gestión editorial de listas")
- **No backend playlists** in this branch (separated to `playlists-premium-backend`)
- **No Michi Link** modified in this branch
- Sidebar with glyph system (no emojis), forbidden routes check
- Header with glass/smoked background, search field, experimental badge
- ActionButton with scale 0.985, loading spinner, focus ring, 6 variants, keyboard support
- MichiGlass 2.0: 30+ color tokens, microinteractions (Behavior on color/border)
- Home, Connections, HomeAudio pages fully migrated with bridge navigation
- Context menu without emojis, toggle_favorite_by_filepath secure method
- SongsPremiumPage.load_data with stale result guard (`_load_counter`)

### QML Directory Structure
```
ui_qml/
├── theme/        → Colors, Typography, Spacing, Motion, Theme
├── materials/   → Glass, Hero, Popup, Sidebar, Input, Acrylic
├── components/  → GlassPanel, GlassCard, ActionButton, StatusBadge, ...
├── shell/       → AppShell, Sidebar, HeaderBar, PageStack, RouteTransition
├── pages/
│   ├── home/          → HomePage (fully migrated)
│   ├── connections/   → ConnectionsPage (fully migrated)
│   ├── home_audio/    → HomeAudioPage (fully migrated)
│   ├── assistant/     → Placeholders
│   └── library/       → Placeholder
└── effects/     → Reserved for future effects
```
