# Runtime Budget — QML Experimental

## RAM Target (QML mode)
- No automatic measurement tool required for foundation phase.
- Guidelines:
  - No blur per item in lists/grids/tables
  - No shadows per item
  - `Loader` for page lazy loading
  - Lightweight delegates for data lists
  - ImageProvider (future) for cover art — no base64 in QML

## Current Baseline (Jul 2026)

### Build / Lint
| Metric | Value |
|--------|-------|
| QML files | 55 |
| QML bridge files | 9 |
| QML tests | 41 |
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
6. Future: ImageProvider for cover art
