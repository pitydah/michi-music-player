# Runtime Budget — QML Experimental

## RAM Target (QML mode)
- No automatic measurement tool required for foundation phase.
- Guidelines:
  - No blur per item in lists/grids/tables
  - No shadows per item
  - `Loader` for page lazy loading
  - Lightweight delegates for data lists
  - CoverBridge for cover art (QQuickPaintedItem, not ImageProvider)

## Current Baseline (Jul 2026)

### Build / Lint
| Metric | Value |
|--------|-------|
| QML files | 59 |
| QML bridge files | 11 |
| QML tests | 83 |
| `ruff` errors (QML/bridge/tests) | 0 |
| `compileall` errors | 0 |
| Python imports | `qml_main` OK, `main` OK |

### Structural Integrity
| Check | Status |
|-------|--------|
| PageStack routes exist | ✅ |
| theme/qmldir singletons | ✅ (5) |
| components/qmldir | ✅ (12) |
| materials/qmldir | ✅ (6) |
| shell/qmldir | ✅ (5) |
| Sidebar forbidden routes | ✅ |
| Sidebar emoji glyphs | ✅ (0) |
| Context menu emoji | ✅ (0) |

## CoverBridge Budget (Phase 2)
- **CoverBridge** (QQuickPaintedItem) registered as `MichiCover 1.0` in qml_main.py
- `paint()` only draws cached pixmap — **NO DB reads, NO image decode**
- Heavy work (DB read, image decode, scale) happens ONCE in `coverKey` setter
- Grid covers: max **512x512** via `_load_cover_image()` scaling
- **No QQuickImageProvider** (unavailable in PySide6 — QQmlImageProviderBase not instantiable)
- _COVER_CACHE: max **256 entries**, LRU-eviction via `_trim_cache()`
- _FALLBACK_CACHE: max **256 entries**, deterministic fallback per seed+size
- Fallback: QPixmap generated via QPainter (gradient + glyph), no disk I/O
- DB reads: via `LibraryDB.get_album_art_cache(album_key)`, connection closed immediately
- Invalid/empty covers: fallback returned. No crash
- Large images: scaled with `Qt.SmoothTransformation` to max 512px
- **No full-res images** in GridView delegates
- **No blur** in grids/lists/tables
- **No shadows** per item
- **No opacity** on parent containers with text

## Measurement Commands
```bash
# Process memory
ps -p $(pgrep -f qml_main) -o rss,vsz

# Detailed memory
smem -p -P "python.*qml_main"

# GPU (if AMD)
radeontop

# Execution time
/usr/bin/time -v python -m ui_qml_bridge.qml_main 2>&1 | grep -E "Maximum resident|User time|System time"
```

## Performance Rules
1. No blur on list/grid/table items
2. No shadows per item in lists/grids/tables
3. No opacity on parent containers with text
4. Use Loader for page lazy loading
5. Lightweight delegates for data lists
6. CoverBridge handles cover art — no ImageProvider needed
