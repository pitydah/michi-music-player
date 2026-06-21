# AGENTS.md — AI Assistant Context for Astra Music Player

## Project Identity

- **Name:** Astra Music Player
- **What:** Audiophile-grade music player for Linux desktop (KDE/Qt6)
- **Stack:** Python 3.11+, PySide6 (Qt6), GStreamer 1.28, SQLite3 + FTS5
- **Repo:** `pitydah/astra-music-player` on GitHub
- **License:** GPL-3.0-or-later

## Absolute Rules

- **PySide6/Qt6 native only** — no QML, no Electron, no web views
- **0 stubs** — every module connected to a real flow
- **0 dead code** — every function called from production
- **ruff 0** — all lint checks pass
- **tests ≥ 206** — always passing
- **Glassmorphism everywhere:** `#090B11` background, `rgba(255,255,255,0.x)` overlays
- **No orange, pink, magenta, neon** in any UI element
- **Accent color:** cool blue `#8FB7FF`
- **SVG icons:** always through `render_svg_icon()` or `get_qicon()`/`get_pixmap()` — never `QIcon(path)` direct
- **Text readability:** section headers ≥ 78% opacity, nav items ≥ 82%
- **Font weights:** use valid CSS values (bold, 500, 600, 700) — not 540/680/720

## Architecture

```
astra-music-player/
├── audio/          # Audio engine (24 files)
│   ├── player.py            # GStreamerEngine — central playback
│   ├── pipeline_factory.py  # Pipeline construction per profile
│   ├── dac_manager.py       # DAC routing, device detection
│   ├── output_profiles.py   # 9 audio profiles
│   ├── dsp_state.py         # DSP state tracking
│   ├── replaygain.py        # ReplayGain config + computation
│   ├── quality_classifier.py # 6 quality categories
│   └── player_service.py    # Facade between UI and engine
├── library/        # Library + indexer (17 files)
│   ├── indexer.py           # Indexer 2.0 pipeline
│   ├── search_engine.py     # FTS5 + field filters
│   ├── library_db.py        # SQLite schema + CRUD
│   └── coverflow.py         # 3D CoverFlow
├── recognition/    # Music identification (10 files)
│   ├── detection_service.py      # Orchestrator
│   ├── identifier_controller.py  # Source-aware logic
│   └── providers/                # shazam.py, audd.py, acoustid.py
├── integrations/   # Home Audio + TheAudioDB + Astra API
├── ui/             # User interface (35+ files)
│   ├── window.py              # MainWindow (2644 lines)
│   ├── central/               # Central area styles (QSS centralized)
│   ├── sidebar/               # Sidebar modules (7 files)
│   │   ├── sidebar_tokens.py  # Visual tokens
│   │   ├── sidebar_styles.py  # QSS functions
│   │   ├── sidebar_item.py    # SidebarItem widget
│   │   ├── sidebar_section.py # Section header + container
│   │   ├── sidebar_panel.py   # Glass background painter
│   │   ├── sidebar_brand.py   # App brand card
│   │   └── sidebar_search.py  # Search field
│   ├── controllers/           # 14 controllers
│   └── icon_loader.py         # Icon resolution + tinting
├── streaming/      # Radio + Subsonic + transmit
├── core/           # AppContext DI, settings, playback ctrl
├── sources/        # MusicSource abstraction
├── tests/          # 206 tests in 25+ files
└── icons/          # 38+ icons (SVG + PNG)
```

## Key Service Responsibilities

| Service | Responsibility | Key File |
|---------|---------------|----------|
| PlayerService | Facade to GStreamerEngine. All UI calls go through here. | `audio/player_service.py` |
| PipelineFactory | Builds GStreamer pipelines per profile/format/route | `audio/pipeline_factory.py` |
| Indexer | Incremental file scanning with batch writing | `library/indexer.py` |
| SearchEngine | FTS5 full-text + field-filtered queries | `library/search_engine.py` |
| SidebarController | Builds sidebar sections/items, emits navigation_requested | `ui/sidebar_controller.py` |
| DetectionService | Continuous audio capture + recognition | `recognition/detection_service.py` |
| AppContext | DI container — all controllers access window via `self._win._ctx` | `core/app_context.py` |

## Current State

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

## What NOT to Touch (without explicit need)

- Sidebar layout/structure
- NowPlayingBar layout/structure
- CoverFlow 3D
- Audio engine core (`player.py` playback logic)
- Home Audio view (except visual fixes)
- PlayerService public API
- PlaybackController core logic
- QStackedWidget global structure

## Patterns to Follow

### Icon loading (ALWAYS)
```python
# SVG icons:
from ui.icons import get_qicon, get_pixmap
icon = get_qicon("key", size=24)        # returns QIcon
pix = get_pixmap("key", size=24)        # returns QPixmap

# Sidebar icons:
from ui.icon_loader import get_sidebar_icon
pix = get_sidebar_icon("key", active=False, size=24)

# NEVER:
QIcon(path)         # bypasses alpha-safe renderer
QPixmap(path)       # bypasses alpha-safe renderer
QIcon(get_icon(k))  # old pattern — use get_qicon()
```

### QSS styles (centralized)
```python
# In ui/central/central_styles.py or ui/sidebar/sidebar_styles.py:
widget.setStyleSheet(table_qss() + scrollbar_qss())

# NOT:
widget.setStyleSheet("""QTableView { background: ... }""")  # inline
```

### Glass visuals
```css
/* Backgrounds: solid dark base */
background: #090B11;
/* OR: glass overlay */
background: rgba(255,255,255,0.045);
/* OR: glass gradient */
qlineargradient(x1:0, y1:0, x2:0, y2:1,
  stop:0 rgba(255,255,255,0.065), stop:1 rgba(255,255,255,0.025));
/* Borders: always translucent white */
border: 1px solid rgba(255,255,255,0.08);
/* Accent: cool blue only */
#8FB7FF
rgba(143,183,255,0.34)
```

### Text colors (minimum opacity)
```
Navigation items:    rgba(255,255,255,0.85)  minimum
Section headers:     rgba(255,255,255,0.88)  minimum
Item hover:          rgba(255,255,255,0.96)
Item active:         rgba(255,255,255,1.00)
Subtitles/secondary: rgba(255,255,255,0.62)
Muted:               rgba(255,255,255,0.52)
```

## Quick Reference

```bash
# Lint
ruff check . --output-format concise

# Compile check
python -m compileall -q .

# Tests
python -m pytest tests/ -q

# Clear stale cache
find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null

# Run app
python main.py
```

**Key directories:**
- Icons: `icons/` (sidebar_clean for PNG, sidebar/ for SVG, nowplaying_clean for PNG, radio/ for radio SVG)
- Settings: `core/settings_manager.py` (QSettings wrapper)
- Theme: `ui/theme.py` (global QSS — avoid modifying, widget-specific QSS should use central_styles)

**Last commits (recent):**
```
f219611 fix: extend SVG alpha-safe renderer to entire app
5730faa fix: sidebar section headers — white text 0.88
6233287 fix: SVG native_color — remove pure black pixels + edge cleanup
9614995 fix: Home Audio — own sidebar section + transparent background
```
