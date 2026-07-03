# POST PR #7 Merge Audit

Fecha local: 2026-07-02 21:43 America/Santiago

## Resumen

PR #7 quedo mergeado correctamente en `main`.

- PR: https://github.com/pitydah/michi-music-player/pull/7
- Merge commit: `7cf280c49abaf522c53eba249fbc84c48b595d9d`
- `main` local tras `git pull --ff-only`: `7cf280c49abaf522c53eba249fbc84c48b595d9d`
- GitHub Actions en `main`: success
- Estado recomendado: candidato a `0.2.0-alpha.2` o `0.2.0-beta.0-rc1` interna, no beta publica todavia.

## Verificacion de main

Comandos ejecutados:

```bash
git checkout main
git pull --ff-only
git rev-parse HEAD
```

Resultado:

```text
7cf280c49abaf522c53eba249fbc84c48b595d9d
```

Conclusion: `main` quedo exactamente en el merge commit de PR #7.

## Revision manual

Archivos revisados:

- `ui_qml_bridge/nowplaying_bridge.py`
- `ui_qml_bridge/playback_bridge.py`
- `ui_qml_bridge/qml_main.py`
- `ui_qml/components/NowPlayingBar.qml`

Hallazgos:

- `qml_main.py` crea un solo `NowPlayingBridge` real respaldado por `PlayerService`.
- `PlaybackBridge` funciona como fachada de compatibilidad y delega en esa misma instancia compartida.
- `NowPlayingBar.qml` prioriza `nowplayingBridge` y conserva fallback a `playbackBridge`.
- `NowPlayingBridge` resuelve correctamente `current` como objeto, dict o string, evitando cover keys basados en `repr`.
- No se detectaron bloqueos de merge en el wiring QML de Now Playing.

Observacion no bloqueante:

- `toggleShuffle` y `toggleRepeat` en `NowPlayingBridge` mantienen estado QML local. Conviene validarlos en una pasada funcional posterior contra el contrato real de `PlayerService`/backend.

## Matriz local

| Check | Resultado |
| --- | --- |
| `ruff check .` | OK |
| `python -m compileall -q -x '.venv/|\.tmpl\.' .` | OK |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python scripts/smoke_startup.py` | OK |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python scripts/smoke_ui_routes.py` | OK |
| `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q` | 169 passed |
| `python -m pytest tests/test_schema.py -q` | 15 passed |

Notas:

- Los smokes muestran warnings Qt conocidos de stylesheet/system tray, pero terminan con `All checks passed`.
- Pytest muestra un warning de `PyGIDeprecationWarning` en GI, no bloqueante.

## CI remoto

Run de GitHub Actions en `main`:

- Workflow: CI
- Run: https://github.com/pitydah/michi-music-player/actions/runs/28632767148
- Head SHA: `7cf280c49abaf522c53eba249fbc84c48b595d9d`
- Conclusion: success

## Veredicto

PR #7 quedo integrado de forma limpia.

El estado post-merge es significativamente mejor que el previo:

- `smoke_ui_routes` cerrado.
- Cobertura de schema restaurada.
- `MpdResponse`/F821 cerrado.
- Ruff repo-wide en cero.
- CI de PR y CI de `main` verdes.
- QML Now Playing conectado al `PlayerService` real con fachada de compatibilidad.

Recomendacion:

- No etiquetar todavia como beta publica.
- Si se quiere cortar version, usar `0.2.0-alpha.2`.
- `0.2.0-beta.0-rc1` puede considerarse solo como beta-rc interna, despues de una prueba manual de reproduccion real con una biblioteca local.
