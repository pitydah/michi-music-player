# Stabilization Smoke + Ruff Report

## Rama
- Base: `main` (d9f3273)
- Rama de trabajo: `stabilize-smoke-ruff`
- HEAD inicial: d9f3273
- HEAD final: (pendiente commit)

## Objetivo
Verificar fix `is_smart`, smoke tests, QML tests y deuda ruff.

## Verificación schema is_smart
| Check | Resultado |
|---|---|
| `smoke_startup` pasa sin error `is_smart` | ✅ |
| Columna `playlists.is_smart` existe tras schema init | ✅ (test_schema.py) |
| `idx_playlist_smart` se crea después de migraciones | ✅ (INDEX_SQL[:4] pre, INDEX_SQL[4:] post) |
| Schema idempotente (init dos veces) | ✅ |
| Migraciones playlist idempotentes | ✅ |

## Tests ejecutados
| Comando | Resultado |
|---|---|
| `python -m compileall -q -x '.venv/|\.tmpl\.' .` | ✅ |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python3 scripts/smoke_startup.py` | ✅ **All checks passed** |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python3 scripts/smoke_ui_routes.py` | ✗ `history search mismatch` (bug diferente, pre-existente) |
| `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/qml/ -q` | **165 passed** |
| `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_schema.py -q` | **9 passed** |
| `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_library_db.py -q` | **8 passed** |
| `QT_QPA_PLATFORM=offscreen python3 -m pytest tests/test_playlist_stability.py tests/test_playlist_wiring.py -q` | **19 passed** |

## Arranque importable
| Modo | Resultado |
|---|---|
| QtWidgets (`from ui.window import MainWindow`) | ✅ OK |
| QML (`from ui_qml_bridge.qml_main import main`) | ✅ OK |

## Ruff
| Métrica | Antes | Después |
|---|---:|---:|
| Total errores | 53 | 49 |
| Auto-fix aplicados | — | 6 |
| Pendientes | — | 49 |
| docs/RUFF_DEBT_AUDIT.md | — | Creado |

## Cambios realizados
| Archivo | Motivo |
|---|---|
| `tests/test_schema.py` | Nuevo: test idempotente de schema (9 tests, columna is_smart, índices) |
| `docs/RUFF_DEBT_AUDIT.md` | Nuevo: auditoría de deuda ruff |
| `scripts/diagnose_hybrid_audio.py` | Ruff --fix: imports no usados eliminados |
| `tests/test_hybrid_audio_manager.py` | Ruff --fix: import no usado eliminado |

## Issues restantes
| Issue | Severidad | Próxima acción |
|---|---|---|
| `smoke_ui_routes` falla por `history search mismatch` | Media | Diagnosticar test de navegación |
| `mpd_backend.py` 12 errores B904 | Media | Revisar cadena de excepción |
| `mpd_client.py` 2 errores F821 (MpdResponse) | Alta | Agregar import faltante |
| 49 errores ruff restantes en audio/tests | Baja | Clasificados en RUFF_DEBT_AUDIT.md |

## Estado honesto actualizado
- `is_smart` bug: **corregido**
- smoke_startup: **verde**
- smoke_ui_routes: **falla por causa diferente** (history search mismatch)
- QML tests: **165 passed**
- Schema/library/playlist tests: **36 passed**
- Ruff: 53 → 49 (mejoró)
