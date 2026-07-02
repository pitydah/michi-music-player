# Michi Music Player — QML Migration Plan

## Objective
Migrate Michi Music Player UI from QtWidgets to Qt Quick (QML) progressively,
without rewriting the entire app, without breaking the existing QtWidgets UI,
and without touching playback, sync, or Android integration.

## Hybrid Architecture

```
┌──────────────────────────────────────────────┐
│  main.py (QtWidgets)        qml_main.py (QML) │
│  ┌──────────────────┐   ┌──────────────────┐ │
│  │ QtWidgets UI     │   │ Qt Quick / QML   │ │
│  │ (fallback stable) │   │ (premium skin)   │ │
│  └──────┬───────────┘   └──────┬───────────┘ │
│         │                      │              │
│         ▼                      ▼              │
│  ┌──────────────────────────────────────────┐ │
│  │ Python / PySide6 (brain)                 │ │
│  │ ui_qml_bridge/ (bridges)                 │ │
│  │ core/ library/ audio/ (untouched)        │ │
│  └──────────────────────────────────────────┘ │
└──────────────────────────────────────────────┘
```

## What stays in Python
- All business logic (playback, DB, sync, recognition, etc.)
- All existing QtWidgets UI
- All controllers, services, and models
- Audio engine, pipeline, GStreamer, MPD

## What goes to QML
- New premium visual layer (ui_qml/)
- Bridges layer (ui_qml_bridge/) connecting QML to Python
- Theme, materials, components, shell, pages

## How to run QML
```bash
python -m ui_qml_bridge.qml_main
python main.py --qml
```

## How to run classic app
```bash
python main.py
```

## Phases Completed (Foundation)

| Phase | Description | Status |
|-------|-------------|--------|
| 0 | Baseline & safe branch | ✅ |
| 1 | QML directory structure | ✅ |
| 2 | Theme QML (Colors, Typography, Spacing, Motion) | ✅ |
| 3 | Glass Materials (Glass, Hero, Popup, Sidebar, Input, Acrylic) | ✅ |
| 4 | Base Components (GlassPanel, GlassCard, ActionButton, StatusBadge, etc.) | ✅ |
| 5 | Shell (AppShell, Sidebar, HeaderBar, PageStack) | ✅ |
| 6 | Bridges (AppBridge, NavigationBridge, CommandBus, ThemeBridge) | ✅ |
| 7 | Home QML (Hero, Continue, Library, Ecosystem, Assistant cards) | ✅ |
| 8 | Connections QML (MicroServerHero, external servers, discovery) | ✅ |
| 9 | Home Audio QML (HA panel, Michi Music Stream, zones, receivers) | ✅ |
| 10 | Placeholders (Library, Assistant, AudioLab, Settings) | ✅ |
| 11 | Documentation | ✅ |
| 12 | Tests & smoke validation | ✅ |
| 13 | Hardening Pass — PageStack rutas, qmldir, bridges endurecidos, nav por bridge, conexión botones, tests estructurales | ✅ |
| 14 | Polish Pass + Premium Design — Header glass, ActionButton microinteracciones (scale, loading, focus), Sidebar glyphs (sin emojis), MichiGlass 2.0 (+15 tokens), Home sin emojis, externos grid 2x2, placeholders premium, route sync test, emoji prohibition test | ✅ |
| 15 | Hardening Navegación + UI Clásica — NavigationHistory dedup (últimos 2 entries), Alt+Left/Right con guard de foco editable, menú contextual sin emojis, toggle_favorite_by_filepath seguro, SongsPremiumPage load_data con stale guard | ✅ |
| 16 | Foundation Cierre Final — 41 tests QML, sidebar forbidden routes test, context menu emoji test, ruff 0 en ui_qml/ui_qml_bridge/tests | ✅ |
| 17 | Sidebar Final + Scope Compliance — Settings eliminado, Radio/Playlists como rutas principales, Michi AI como label visible, PageStack casos explícitos, ActionButton keyboard support, PlaceholderPage parametrizable, no-touch contract verificable, 53 tests | ✅ |
| 18 | Library QML Foundation + Michi AI Real — LibraryPage con tabs (Canciones/Álbumes), SongTable, AlbumGrid, bridges LibraryBridge/MichiAIBridge, chat funcional, 60 tests. Playlists backend separado a rama `playlists-premium-backend`. | ✅ |
| 19 | ImageProvider Attempt — PySide6 no exporta QQuickImageProvider. Se usa fallback QML premium con gradiente+glyph. LibraryBridge robusto con QVariantList. 70 tests. | ✅ |
| 20 | Phase 2.5 — Rama limpia: Broadcast/Podcasts separados, NowPlaying separado, Géneros eliminado del sidebar QML, Settings eliminado. CoverBridge final. | ✅ |
| 21 | Phase 3 — Metadata Inspector read-only con lectura real vía mutagen (title, artist, album, bitrate, samplerate, duration, channels, size). canApply=false. Sin escritura. | ✅ |
| 22 | Phase 4 Foundation — Audio Lab QML hub con Inspector de metadatos integrado. Cards seguras. Sin acciones destructivas. | ✅ |

## Sidebar Final
```
 1. Inicio        route: home        glyph: IN
 2. Biblioteca    route: library     glyph: BL
 3. Mix           route: mix         glyph: MX
 4. Reproducción  route: playback    glyph: RP
 5. Conexiones    route: connections  glyph: SV
 6. Radio         route: radio       glyph: RD  (placeholder)
 7. Playlists     route: playlists   glyph: PL  (placeholder)
 8. Home Audio    route: home_audio  glyph: HA
 9. Michi AI      route: assistant   glyph: AI  (ruta interna assistant)
10. Audio Lab     route: audio_lab   glyph: AL
```

## Commands
```bash
python -m pytest tests/qml/ -q    # 99+ tests
python scripts/check_no_touch_contract.py  # verify no-touch compliance
python -m ui_qml_bridge.qml_main  # launch QML UI
python main.py --qml              # launch QML from main
python main.py                    # classic QtWidgets
ruff check ./ui_qml ./ui_qml_bridge ./tests/qml  # lint
```

## Scope Decisions
- **Playlists backend**: Separado a rama `playlists-premium-backend`. Esta rama (`qml-migration-foundation-clean`) mantiene solo la ruta `playlists` como placeholder QML.
- **Michi Link**: NO TOCADO en esta rama.
- **Integrations/michi_link**: NO TOCADO en esta rama.

## Next Phases (Recommended)
1. **ImageProvider** — cover art Python → QML (requires cpp/cython bridge)
2. **Metadata híbrido** — InspectorPanel with real data
3. **Audio Lab QML**
4. **NowPlayingBar QML** (last, most complex)

## Commands
```bash
python -m pytest tests/qml/ -q    # 38 tests
python -m ui_qml_bridge.qml_main  # launch QML UI
python main.py --qml              # launch QML from main
python main.py                    # classic QtWidgets
ruff check ./ui_qml ./ui_qml_bridge  # lint
```

## Performance Rules (QML)
- No blur on list/grid/table items
- No shadows per item in lists/grids/tables
- No opacity on parent containers with text
- Use `Loader` for page lazy loading
- Lightweight delegates for data lists
- Future: ImageProvider for cover art (no base64 in QML)

## Contrast Rules
- TextPrimary: #F0F2F8 on bgApp #070A10 → ratio ~14:1
- TextSecondary: #D0D4E0 on bgApp #070A10 → ratio ~10:1
- TextMuted: #606878 on bgApp #070A10 → ratio ~5:1 (for non-critical text)
- AccentBlue: #8FB7FF on bgApp #070A10 → ratio ~7:1

## Do Not Touch (Protected)
- `ui/devices_page.py`
- `sync/` (entire directory)
- `sync_protocol.py`, `sync_server.py`, `sync_manager.py`
- Android integration
- `integrations/michi_link/` (Michi Link / Micro Server backend)
- `ui/nowplaying_bar.py`
- `ui/source_status_badge.py`
- Playback logic (`audio/player.py`, `audio/player_service.py`)
- `audio/pipeline_factory.py`
- `core/playback_controller.py`
- User database
- Existing SQLite migrations

## QML Migration Rules (for AI assistants)
1. QML does NOT access the database directly
2. QML emits intention; Python executes
3. Do NOT touch Sync or Android
4. Do NOT touch playback
5. No `opacity` on parent containers with text
6. No blur on lists/grids/tables
7. No per-item shadows in lists/grids/tables
8. Keep fallback QtWidgets intact
9. No fake data shown as real — use "No configurado", "Demo QML", "Experimental"
10. Theme tokens preferred over hardcoded colors
