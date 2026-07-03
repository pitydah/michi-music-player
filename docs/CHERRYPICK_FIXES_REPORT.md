# Cherry-pick Fixes Report

## Rama
- Base: `main` (cfbd99e)
- Rama de trabajo: `qml-selective-fixes`
- Fecha: 2026-07-02
- HEAD inicial: cfbd99e
- HEAD final: (pendiente commit)

## Objetivo
Aplicar correcciones selectivas desde `qml-migration-foundation` sin merge completo.
Cada cherry-pick se intenta individualmente. Si genera conflicto grande, se aborta y documenta.

## Commits aplicados
| Commit | Mensaje | Resultado | Conflictos | Tests posteriores |
|---|---|---|---|---|
| Ninguno de `qml-migration-foundation` | — | 0 commits netos — todos ya existen en `main` o `main` tiene versión superior | — | 165 QML passed |

## Commits omitidos — intentados y abortados por conflicto
| Commit | Motivo del aborto |
|---|---|
| `85fd282` | Conflicto en `test_qml_bridges.py` (945 líneas vs original) y `PageStack.qml`. Tests ya existen en `main`. |
| `1fcfaef` | Conflicto en `AGENTS.md` y `RUNTIME_BUDGET.md` — docs ya actualizadas en `main`. |
| `6572f2f` | Conflicto en `PageStack.qml` — `main` tiene 14 rutas vs 7 en versión antigua. |
| `bd23418` | Conflicto en `AppShell.qml` — `main` mantiene rutas radio/playlists vivas. |
| `b66a6cd` | Conflicto en 3 páginas QML — archivos divergidos. |
| `5bb177d` | Conflicto en `AppShell.qml` — archivo divergido. |
| `cce7e74` | Conflicto en `app_bridge.py` y `navigation_bridge.py` — `main` tiene versiones superiores (importlib.metadata, 14 rutas). |

## Commits omitidos — ya en main (cherry-pick vacío)
| Commit | Motivo |
|---|---|
| `bcdf67b` | Fix de sintaxis en `metadata_extractor.py` ya incorporado en `main` en commit previo. |
| `44ffb96` | `theme/qmldir` con declaraciones singleton ya existe en `main`. |

## Commits omitidos — no intentados por clasificación
| Commit | Clasificación original | Motivo |
|---|---|---|
| `d8a800e`, `38773ef`, `228725d`, `9e4490e`, `002d67f` | necesario | Tocan `test_qml_bridges.py` — mismo archivo divergido que `85fd282`. Omitidos en cadena. |
| `b55d303`–`3b5cbee` | necesario (refinamiento visual) | No aplicar automáticamente según plan. |
| `a82f8da`–`56c1f7b` | requiere revisión manual | No aplicar sin revisión explícita. |
| `017244d` | riesgoso | Audio core. No aplicar. |
| `1114cfb`–`f7d77d4` | descartable | Docs de rama obsoletas. |

## Conflictos resueltos — fuera de cherry-pick
| Archivo | Resolución |
|---|---|
| `ui_qml_bridge/cover_bridge.py` | Path hardcodeado corregido: ahora usa `core.paths.database_path()` con fallback seguro. |

## Tests ejecutados
| Comando | Resultado |
|---|---|
| `ruff check .` | 51 errores (preexistentes) |
| `python -m compileall -q -x '.venv/|\.tmpl\.' .` | ✅ |
| `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/qml/ -q` | **165 passed** |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python3 scripts/smoke_startup.py` | 1 pre-existing (`is_smart`) |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python3 scripts/smoke_ui_routes.py` | 1 pre-existing (`is_smart`) |

## Arranque manual
| Modo | Resultado |
|---|---|
| QtWidgets (`from ui.window import MainWindow`) | ✅ OK |
| QML (`from ui_qml_bridge.qml_main import main`) | ✅ OK |

## Anti-regresión
| Check | Resultado |
|---|---|
| `0.2.0-beta` o `0.1.0-qml` en código activo | ✅ No presente |
| `native widgets only, no QML` en código activo | ✅ No presente |
| Demo data sin gate `MICHI_QML_DEMO=1` | ✅ Demo data gated |
| Path hardcodeado `Path.home() / ".local" / "share"` | ❌ Corregido — `cover_bridge.py` ahora usa `core.paths.database_path()` |
| Audio/core/window/main tocado | ✅ No tocado |

## Riesgos restantes
1. `is_smart` schema bug bloquea smoke startup y ~12 tests.
2. `cover_bridge.py` mantiene fallback hardcodeado si `core.paths` no está disponible — tolerable.

## Conclusión
De 34 commits en `qml-migration-foundation`, 0 produjeron cambios netos aplicables sobre `main`.
- 2 ya estaban en `main` (cherry-pick vacío)
- 7 fueron intentados y abortados por conflicto (main tiene versión superior)
- 6 omitidos en cadena por archivo divergido
- 6 refinamientos visuales no aplicados automáticamente
- 9 requieren revisión manual
- 1 riesgoso (no aplicado)
- 4 descartables

La rama `qml-migration-foundation` puede marcarse como obsoleta.
