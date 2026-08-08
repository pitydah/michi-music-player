# AGENTS.md — AI Assistant Context for Michi Music Player

## 1. Project Identity

**Michi Music Player** — Audiophile music player for Linux desktop (KDE Plasma / Qt 6).
Written in Python 3.11+ with PySide6, GStreamer 1.0, SQLite FTS5, mutagen, shazamio, PyAudio.

| Field | Value |
|-------|-------|
| License | GPL-3.0-or-later (derived from Miro Player — see NOTICE) |
| Repository | https://github.com/pitydah/michi-music-player |
| Python | 3.11+ |
| UI toolkit | PySide6 (Qt 6) — QML UI |
| Audio engine | Hybrid: GStreamer 1.28 (default) + MPD (Hi-Fi/bit-perfect) |
| Hybrid engine | `audio/backends/` — `AudioBackend` API, `GStreamerBackend`, `MpdBackend`, `HybridAudioManager` |
| Database | SQLite 3 (WAL mode) + FTS5 full-text search |
| Metadata | mutagen (ID3, Vorbis, MP4, MusicBrainz, ReplayGain, BPM) |
| Recognition | shazamio, AudD HTTP API, AcoustID fpcalc + Chromaprint |
| Audio analysis | librosa, soundfile, numpy (feature extraction, acoustic profiling) |
| Smart mixes | recommendation engine based on acoustic features + play counts |
| Build system | pip install . / Flatpak |
| Test authority | Tiered model (T0–T3, Quarantine, Legacy); see `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md`. Handwritten test counts are NEVER current truth — consult `docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md` or run the inventory. |

## 2. Orchestrator SDD — Reglas de Precedencia

Las skills son herramientas subordinadas al cambio SDD activo.
Ninguna skill puede ampliar el alcance, modificar contratos productivos,
crear compatibilidad artificial, debilitar tests o corregir dominios ajenos
sin evidencia explícita y autorización del orquestador.

### Precedencia de skills (orden de activación)

1. **SDD** — define alcance y contrato del cambio
2. **Python Expert** — diagnostica e implementa
3. **TDD** — valida causa raíz y corrección
4. **Code Quality** — revisa mantenibilidad
5. **Code Review** — busca regresiones
6. **Judgment Day** — gate final de aprobación
7. **Git Commit** — prepara el commit sin cambiar código

### Skills excluidas por defecto

- `Impeccable`, `ui-animation`, `docs-write`, `image-generation` y todo skill de frontend/UI solo se activan con orden explícita del orquestador.
- Skills Python no relacionadas con el diagnóstico activo (ej: `python-fastapi` para una corrección de fixtures) se omiten para evitar ruido.

---

## 2A. Development Convergence Mode — Normativa

Normativa para agentes (detalle completo en `docs/development/AI_DEVELOPMENT_POLICY.md` y `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md`):

- **Arquitectura primero, pasos pequeños (26A)**: nunca implementar una feature de una sola pasada. Pipeline obligatorio: spec → arquitectura → fases → baby step → conexión real → validación → checkpoint. Cambios por slices verticales, conexión temprana al runtime real y diseño para testabilidad.
- **Estados de feature**: CODED → WIRED → PRODUCTIVE → VALIDATED → STABLE. Prohibido declarar STABLE sin evidencia verde repetida; estados honestos PASS/PARTIAL/FAIL/NOT_TESTED/BLOCKED.
- **Tests son evidencia, no especificación**: prohibido apaciguar tests, cascadas de parches, dumps monolíticos y "mock-only" como finalización. Tests rotos se trian con KEEP/REWRITE/QUARANTINE/DELETE.
- **Jerarquía de tests**: T0 (safety gate, BLOQUEA), T1 (estable, bloquea SOLO en dominios explícitamente estables; promoción exige evidencia verde repetida), T2 (development, advisory), T3 (experimental/entorno/perf, manual/nightly), Quarantine (visible, NO bloquea, triage con plazo), Legacy (contrato sin validar, no autoritativo hasta auditar), Full inventory (DIAGNÓSTICO, no bloquea). Referencias normativas: `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md`, `docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md`, `docs/testing/SUBSYSTEM_MATURITY.yaml`.
- **Orquestación y handoff**: el orquestador divide el trabajo en work units con checkpoint propio; el handoff a Engram registra estado de feature, evidencia y próximos pasos (26A.34).

---

## 3. Directory Structure

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
├── ui_qml/          → QML pages, components, shell
│                     folder_browser.py, folders/folder_problem_report.py,
│                     style_tokens.py, qss.py, icon_registry.py, icon_loader.py,
│                     central/ (central_styles.py, central_tokens.py),
│                     sidebar/ (7 módulos: tokens, styles, item, section, panel, brand, search)
├── core/           → interfaces.py, settings_manager.py,
│                     playback_controller.py, file_actions.py,
│                     file_manager_service.py, safe_file_ops.py,
│                     home/ (home_status.py dataclasses, home_dashboard_service.py),
│                     audio_lab/ (diagnostics_helpers.py)
├── sources/        → base_source.py, local_source.py, radio_source.py, subsonic_source.py
├── streaming/      → subsonic_client.py, radio_manager.py, transmit_manager.py
├── sync/           → Android REST API + UDP multicast discovery
├── lyrics/         → lrclib_client.py
├── metadata/       → album_info_repository.py (LRU 200 + SQLite fallback)
├── tests/          → pytest suite — run the safety gate `scripts/test_gate.sh` (T0) as the ordinary validation
├── docs/           → architecture.md, roadmap.md
├── icons/          → 38+ icons (SVG + PNG, sidebar_clean/, sidebar/, nowplaying_clean/, radio/)
└── AGENTS.md       → This file
```

**Total:** 15 controllers · 9 audio profiles · 3 recognition providers
**Verify:** `scripts/test_gate.sh` (T0 SAFETY GATE = BLOCKING) · `ruff check .` · `python -m compileall -q .`
**Note:** Do not trust handwritten test/file counts — consult `docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md` or run the inventory; no handwritten counts are current truth.

## 4. Architectural Patterns — MUST FOLLOW

> **LEGACY / NON-CANONICAL NOTICE (M0.1 truth alignment, baseline fd451afb):**
> The QtWidgets `ui/` tree (window.py, sidebar_controller.py, QStackedWidget views,
> `ui/controllers/`, `ui/icon_registry.py`, `ui/central/`, `ui/sidebar/`) was
> **removed from the productive runtime** (commit `5ddacff1`, "remove QtWidgets
> legacy code — QML-only runtime"). None of those paths exist at baseline
> `fd451afb`. They are kept below ONLY as historical references — do NOT reuse
> them as patterns. The productive architecture is:
>
> **QML UI (`ui_qml/`) → bridges (`ui_qml_bridge/`) → canonical services (`core/`) → adapters/backends**
>
> - Composition root: `core/composition/` (builders) + `core/service_manifest.py` (`SERVICE_MANIFEST`, single source of truth for container lifecycle, ADR-001)
> - `ServiceContainer` (`core/service_container.py`) derives start/shutdown from `SERVICE_MANIFEST`
> - Route/sidebar truth: `ui_qml_bridge/route_registry.py` (VALID_ROUTES, `resolve_route`, `get_sidebar_sections`)
> - Entry point: `main.py` → `michi.app_launcher.launch()` → `michi.qml_app.run_qml()` (MICHI_UI=qml is the only valid mode; `widgets` mode was retired)

### Dependency Injection
- Bridges receive typed service references from `ServiceContainer`
- Pattern: bridges emit Qt `Signal` for communication — never call UI methods directly
- `core/composition/*` builders construct services; the manifest is the source of truth
- Migration complete: no legacy DI containers remain

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

### Controllers (LEGACY / NON-CANONICAL — `ui/` was removed)
- One controller per functional domain (14 total)
- QML bridges receive dependencies from `ServiceContainer`
- Emit Qt `Signal` for communication — never call UI methods directly
- NO business logic in controllers — delegate to services
- `window.py` was the main orchestrator; it no longer exists at fd451afb

### Qt Signals
- Naming: `track_changed`, `playback_started`, `library_scanned`, `navigation_requested`
- Use `Signal` from PySide6 for cross-layer communication

### Key Glue Files (connectors between layers)

| File | Role |
|------|------|
| `ui/window.py:937-1212` | **LEGACY** `_on_sidebar_navigate()` — dispatches ALL sidebar clicks to views (giant if/elif chain); file does not exist at fd451afb |
| `ui/sidebar_controller.py:18-69` | **LEGACY** `rebuild()` — builds 7 sidebar sections; file does not exist at fd451afb |
| `core/service_manifest.py` | **PRODUCTIVE** `SERVICE_MANIFEST` — single source of truth for container lifecycle (ADR-001) |
| `core/composition/` | **PRODUCTIVE** builders — construct every service registered on the container |
| `ui_qml_bridge/route_registry.py` | **PRODUCTIVE** `VALID_ROUTES`, `resolve_route`, `get_sidebar_sections` — route/sidebar truth |
| `core/settings_manager.py` | QSettings wrapper — `DEFAULTS` dict has all config keys; `get()`/`set_()` API |
| `ui/icon_registry.py` | **LEGACY** source of truth for all 38+ icons; file does not exist at fd451afb (icons live in `ui_qml/theme` + `icons/`) |
| `ui/window.py:110-127` | **LEGACY** `SECTION_CONFIG`; file does not exist at fd451afb |
| `ui/window.py:28` | **LEGACY** `VIEW_MODE_DEFS`; file does not exist at fd451afb |

## 5. Code Conventions

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

## 6. Visual Rules — ABSOLUTE

> **LEGACY / NON-CANONICAL NOTICE:** the QtWidgets `ui/` paths in this section
> (`ui.icons`, `ui.icon_loader`, `ui/central/central_styles.py`,
> `ui/sidebar/sidebar_styles.py`) do not exist at fd451afb. The productive UI
> is QML: theme tokens live in `ui_qml/theme/` (see `ui_qml/AGENTS.md`). The
> rules below are retained as historical reference for any legacy maintenance.

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

## 7. Testing

### Framework & Rules
- Framework: pytest
- Mocks: `unittest.mock` (`MagicMock`, `patch`)
- Each new module must have `tests/test_<module>.py`
- GStreamer: mock `Gst.Pipeline`, never create real pipelines in tests
- SQLite: use `:memory:`, never touch real DB
- Ordinary validation: `scripts/test_gate.sh` (T0) — see §2A
- **T0 SAFETY GATE = BLOCKING**; **FULL INVENTORY = DIAGNOSTIC** (not a global pre-commit requirement, not a correctness definition, not merge authority)

### Test hierarchy (normative)

| Tier | Meaning | Blocks? |
|---|---|---|
| T0 | Safety gate (`scripts/test_gate.sh`): lint, compile, authority gates, composition smoke, curated `-m gate` set | **YES** |
| T1 | Stable regression set | **YES** — but only for explicitly stable domains; promotion requires repeated green evidence |
| T2 | Development | No (advisory) |
| T3 | Environmental / performance / experimental | No (manual/nightly) |
| Quarantine | Known-failing register | No (visible, time-bounded triage) |
| Legacy | Unvalidated contract | No (non-authoritative until audited) |
| Full inventory | Complete suite run | No (diagnostic only) |

Normative references: `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md`,
`docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md`,
`docs/testing/SUBSYSTEM_MATURITY.yaml`, `docs/development/AI_DEVELOPMENT_POLICY.md`.

### Quick Commands
```bash
scripts/test_gate.sh                       # T0 SAFETY GATE — BLOCKING (ordinary validation)
ruff check . --output-format concise       # lint
python -m compileall -q -x '.venv/|\.tmpl\.' .               # compile check
find . -type d -name "__pycache__" -exec rm -rf {} +   # clear stale cache
python main.py                          # run app
```

## 8. Dependencies

**System (apt):**
```
python3-gi gir1.2-gstreamer-1.0 gstreamer1.0-plugins-*
avahi-utils fpcalc (chromaprint) pactl (PulseAudio/PipeWire) dbus-python
```

**Python (requirements.txt):**
```
PySide6 mutagen numpy shazamio pyaudio requests
```

## 9. What NOT to Do

### Quality
- No generic "helper" files without a clear owner module
- No business logic in `window.py` — goes in controllers or services (**LEGACY**: `ui/window.py` was removed; productive entry is `michi/qml_app.py` → bridges)
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

## 10. Current State

| Metric | Value |
|--------|-------|
| Ruff | **0** (verificar con `ruff check .`) |
| Test counts | **No handwritten counts are truth** — consult `docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md` or run the inventory (full inventory is diagnostic only) |
| Bugs (F-class) | **0** |
| Stubs | **0** |
| Dead code | **0** |
| Audio profiles | **9** |
| Controllers | **15** (with Qt Signals, DI via ServiceContainer) |
| Recognition providers | **3 real** (ShazamIO, AudD, AcoustID) |
| Icons registered | **38+** |
| NAV_ROUTES validated | ✅ startup `RuntimeError` on stale routes |
| XDG paths consolidated | ✅ all via `core.paths` |
| System deps documented | ✅ PyGObject/pycairo/dbus-python via system, not pip |
| `sqlite3.connect(DB_PATH)` bypass removed | ✅ all via `core.paths.database_path()` |
| Home Dashboard dataclasses | ✅ `core/home/home_status.py` (9 dataclasses) |
| Home Dashboard service | ✅ `core/home/home_dashboard_service.py` (10 builder methods) |
| Home 7-card design | ✅ `ui_qml/pages/home/HomePage.qml` (**LEGACY**: `ui/hubs/home_page.py` no longer exists) |
| Spectral FLAC support | ✅ `core/audio_analysis/spectral_authenticator.py:can_analyse()` |

**Installation:**
```
./scripts/install.sh              # unified distro auto-detection (Arch, Debian, Fedora, openSUSE)
./scripts/install.sh --minimal    # core only, no optional deps
./scripts/install.sh --no-venv    # system deps only
./scripts/run_from_source.sh      # run without system install
```

## 11. Key Data Flows

> **LEGACY / NON-CANONICAL NOTICE:** flows below that start at
> `_on_sidebar_navigate()` / `SidebarController` / `QTableView` / `HomePage()`
> describe the removed QtWidgets runtime (see §4). Keep them as historical
> reference; the productive entry points are the QML bridges in
> `ui_qml_bridge/` (e.g. `route_registry.py`, `navigation_bridge.py`).
> The engine-side flow (PlayerService → GStreamerEngine → PipelineFactory)
> remains current.

### Playback
```
sidebar click → _on_sidebar_navigate("library")   [LEGACY — see §4]
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
sidebar "Inicio" click → SidebarController → navigation_requested.emit("home")   [LEGACY — see §4]
  → navigationBridge.navigate("home")
    → AppShell updates header via NavigationBridge
      → HomeController.show()   [LEGACY — productive: ui_qml_bridge/home_bridge.py]
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
- `ui_qml_bridge/home_bridge.py` — QML orchestration (**LEGACY**: `ui/controllers/home_controller.py` / `ui/hubs/home_page.py` no longer exist)

## 12. Common Tasks

> **LEGACY / NON-CANONICAL NOTICE:** the tasks below reference the removed
> QtWidgets `ui/` tree (see §4). They are kept as historical reference. The
> productive equivalents: sidebar/route changes go through
> `ui_qml_bridge/route_registry.py` + `ui_qml/shell/Sidebar.qml`; styles use
> `ui_qml/theme/` tokens; icons live in `ui_qml/theme` + `icons/`.

### Add a sidebar item (LEGACY — productive path: `ui_qml_bridge/route_registry.py`)
1. `ui/sidebar_controller.py:rebuild()` — add `add_section()` + `add_item()` call
2. Icon: register in `ui/icon_registry.py` (PNG or SVG with correct `render_mode`)
3. Navigation: add `elif key == "my_key":` in `window.py:_on_sidebar_navigate()` (line ~937)
4. Header config: add entry in `SECTION_CONFIG` dict (`window.py` line ~110)
5. View: register in `window.py:_views.register("my_view", widget)` (line ~720)

### Add a new QSS style (LEGACY)
1. Define function in `ui/central/central_styles.py` or `ui/sidebar/sidebar_styles.py`
2. Return the QSS string — use the central/sidebar tokens for colors/radii
3. Never write inline QSS in widget files — always `widget.setStyleSheet(my_qss())`

### Add a new icon (LEGACY — productive: `ui_qml/theme` tokens + `icons/`)
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
4. Add UI control in `ui/settings_pages.py` — extend the appropriate `SettingsPage` subclass (**LEGACY**; productive: `ui_qml/pages/settings/`)

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
scripts/test_gate.sh                       # T0 SAFETY GATE — BLOCKING (ordinary validation)
ruff check . --output-format concise       # must be 0
python -m compileall -q -x '.venv/|\.tmpl\.' .   # must be clean
```
> Full inventory (`python -m pytest tests/`) is DIAGNOSTIC ONLY — never a
> pre-commit requirement and never a merge veto (see §2A / §7).

## 13. Protected Files — Risk of Silent Regression

> **LEGACY / NON-CANONICAL NOTICE:** `ui/audio_lab/diagnostics_page.py` does
> not exist at fd451afb (`ui/` removed, QML-only runtime). The productive
> diagnostics surfaces are the QML pages `ui_qml/pages/DiagnosticsPage.qml` /
> `ui_qml/pages/home_audio/DiagnosticsPage.qml` and the bridge
> `ui_qml_bridge/audio_lab_bridge.py`. The history below documents why
> integrity guards exist; re-apply the pattern to any protected file.

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

## 14. Sources of Truth — Hierarquía

Ante cualquier duda sobre el estado real del proyecto, consultar en este orden.
Los documentos históricos son referencias, NUNCA autoridad de estado actual.

**Arquitectura / desarrollo:**
1. Instrucción explícita del owner (orquestador humano)
2. AGENTS.md — normativa vigente (este archivo)
3. `docs/development/AI_DEVELOPMENT_POLICY.md` — política 26A (baby steps, estados honestos)
4. OpenSpec activo (`openspec/changes/`, no archivado)
5. `core/service_manifest.py` (`SERVICE_MANIFEST`) + `core/composition/` — runtime real
6. `docs/development/PRODUCT_CATASTRO.yaml` — cuando exista (catastro de dominios)
7. `docs/testing/SUBSYSTEM_MATURITY.yaml` — madurez por subsistema
8. Documentos históricos (`docs/audits/`, BACKLOG, etc.) — solo referencia

**Tests:**
1. `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md` — modelo de tiers (T0–T3, Quarantine, Legacy)
2. `docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md` — inventario y clasificación auditada
3. Configuración y scripts T0 (`scripts/test_gate.sh`, `pyproject.toml` markers)
4. Contratos estables explícitos (T1)
5. Tests de desarrollo (T2)
6. Quarantine (visible, no bloquea)
7. Legacy (no autoritativo hasta auditar)
8. Expectativas históricas sin validar (baselines viejos) — NUNCA autoridad

## 15. QML UI — Runtime Productivo

**Status:** QML es el ÚNICO runtime. La UI clásica QtWidgets (`ui/`) fue retirada
(commit `5ddacff1`); `MICHI_UI=widgets` ya no existe. Siempre ejecutar
`python main.py`.

### Architecture
- QML does NOT access the database directly
- QML emits intention; Python executes
- Bridges (ui_qml_bridge/) are the only communication layer between QML and Python
- Python remains the brain; QML is the productive skin
- QML (`python main.py`) is the only runtime

### Protected Files — QML
- `ui_qml/` is the QML UI layer
- `ui_qml_bridge/` is the Python bridge layer
- Do NOT touch playback logic (`audio/player.py`, `audio/player_service.py`, `audio/pipeline_factory.py`, `core/playback_controller.py`)
- Do NOT touch Android integration or sync protocol
- All UI is QML
- Never show demo data as if it were real

### Visual Rules (QML)
- No `opacity` on parent containers with text
- No blur on lists/grids/tables
- No per-item shadows in lists/grids/tables
- Theme tokens preferred over hardcoded colors
- No fake data shown as real — use "No configurado", "Demo QML", "Experimental"

### How to run
```bash
python main.py

# Legacy QML entry (deprecated)
# python -m ui_qml_bridge.qml_main

# Tests
ruff check ./ui_qml ./ui_qml_bridge ./tests/qml
python scripts/check_no_touch_contract.py
```
> QML test counts change continuously — consult the test authority docs (§7);
> no handwritten count is current truth.

### Current QML Status (Jul 2026)
- QML-only runtime; no QtWidgets surface remains
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

## 16. Regla Obligatoria para Agentes (cambios sustanciales)

Antes de implementar un cambio sustancial, el agente DEBE:

1. Leer `docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md` y `docs/testing/SUBSYSTEM_MATURITY.yaml`
   para el/los subsistema/s afectados.
2. NO usar fallas de la suite completa como veto automático: el inventario completo
   es DIAGNÓSTICO; el bloqueo real es T0 (y T1 solo en dominios explícitamente estables).
3. NO usar archivos históricos como autoridad de arquitectura actual: lo productivo
   se determina por `SERVICE_MANIFEST` + `core/composition/` + `ui_qml_bridge/` (§4, §14).
4. Trabajar en baby steps: CODED → WIRED → PRODUCTIVE → VALIDATED → STABLE, con
   conexión temprana al runtime real y checkpoint con evidencia en cada fase (§2A).
5. Recordar que una feature que solo existe en código está CODED; NO describirla
   como implementada/completa salvo que su camino productivo haya sido verificado.

## 17. Workflow de Desarrollo (default)

```
LEER POLICY (AI_DEVELOPMENT_POLICY.md) → LEER SPEC ACTIVA (openspec activo)
→ INSPECCIONAR CÓDIGO ACTUAL (SERVICE_MANIFEST + composición + bridges)
→ DEFINIR WORK UNIT PEQUEÑA → IMPLEMENTAR → WIRE (conectar al runtime real)
→ VALIDAR CAMINO PRODUCTIVO → CORRER T0 (scripts/test_gate.sh)
→ CORRER TESTS DE DOMINIO RELEVANTES → CHECKPOINT
```

Explícitamente NO es: "implementar todo → `pytest tests/` → parchear hasta verde".

## 18. Política de Quarantine

Los 665 ítems en Quarantine (register en
`docs/testing/TEST_AUTHORITY_MIGRATION_REPORT.md`) son una **obligación de
triage**, NO un backlog de "tests a hacer pasar":

- Cada ítem recibe una decisión: KEEP / REWRITE / QUARANTINE (mantener)/ DELETE.
- El triage corre en paralelo con el desarrollo y NUNCA bloquea la convergencia
  productiva (no son parte de ningún gate).
- Plazo normativo: 2 ciclos de release o 30 días, lo que ocurra primero
  (propietario: maintainer/orchestrator).
