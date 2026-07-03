# Ruff Debt Audit

## Resumen
- Total de errores inicial: 53
- Errores auto-fix seguros aplicados: 6 (F401, F841, SIM117)
- Errores restantes: 47
- Errores que requieren revisión manual: 30
- Errores no tratados en esta fase: 47

## Categorías

| Código ruff | Cantidad | Riesgo | Acción |
|---|---:|---|---|
| B904 | 15 | Medio | `raise ... from err` faltante en audio backends — requiere revisión manual, no cambiar semántica |
| SIM102 | 3 | Bajo | Combinar `if` anidados — seguro pero toca audio core |
| SIM115 | 8 | Bajo | Usar context manager para archivos temporales en tests — seguro |
| SIM116 | 1 | Bajo | Usar diccionario en vez de `if` consecutivos — toca `adapters/mpris.py` |
| SIM105 | 4 | Bajo | Usar `contextlib.suppress` en vez de `try/except/pass` — seguro |
| SIM117 | 5 | Bajo | Combinar `with` anidados — seguro |
| F821 | 2 | **Alto** | `MpdResponse` no definido — forward ref sin import |
| F841 | 3 | Bajo | Variable asignada pero no usada — seguro |
| F401 | 1 | Bajo | Import no usado en scripts — seguro |
| B007 | 2 | Bajo | Variable de loop no usada — seguro |
| E741 | 1 | Bajo | Nombre de variable ambiguo `l` — seguro |

## Archivos más afectados

| Archivo | Cantidad | Acción |
|---|---:|---|
| `audio/backends/mpd_backend.py` | 12 | Requiere revisión (B904) |
| `audio/mpd/mpd_client.py` | 6 | B904 + F821 (MpdResponse) |
| `tests/` (varios) | ~22 | Bajo riesgo, mayoría SIM115/SIM117 |
| `audio/diagnostics/bitperfect_verifier.py` | 2 | SIM102 |
| `audio/player_service.py` | 1 | SIM102 |
| `ui/genres/genre_operation_dialog.py` | 1 | F841 |

## Errores auto-fix seguros (no aplicados aún)

`ruff check . --unsafe-fixes` podría corregir algunos más, pero no se ejecuta para evitar cambios semánticos no deseados.

## Errores que requieren revisión manual (no corregir ahora)

- **B904** en `mpd_backend.py` y `mpd_client.py`: agregar `from e` preserva la cadena de excepciones pero cambia el stack trace. Debe revisarse con el equipo de audio.
- **F821** en `mpd_client.py`: `MpdResponse` necesita import — corregir requiere entender el tipo.

## No tratar todavía

- Errores en `audio/backends/` y `audio/mpd/` — requieren revisión manual del motor de audio.
- Errores en `adapters/mpris.py` — SIM116 no cambia comportamiento pero toca integración MPRIS.
