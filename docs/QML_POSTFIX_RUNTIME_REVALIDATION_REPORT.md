# QML Post-Fix Runtime Revalidation Report

## Base

- Branch: `qml-postfix-runtime-revalidation`
- Base commit: `899a9e5`
- HEAD: `899a9e5` + fixes
- Fecha: 2026-07-03

## Commits revisados

| Commit | Propósito |
|---|---|
| `59edd0f` | fix(qml): resolve runtime display blockers |
| `e4ade2b` | fix(qml): resolve remaining risks - smart tagging selector and eq bridge |
| `da10d78` | fix(qml): add missing materials import to HomeAssistantPanel |
| `aedbf7b` | fix(qml): add streamState to MichiMusicStreamPanel, fix motion.medium |
| `899a9e5` | fix(qml): make nowplaying bar background visible |

## Validación automatizada

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `smoke_startup` | ✅ 7/7 |
| `smoke_ui_routes` | ✅ 2/2 |
| `check_runtime.py` | ✅ Todo listo |
| `tests/qml/ -q` | ✅ 249 passed |
| `tests/test_schema.py` | ✅ 15 passed |
| `tests/test_format_probe.py` | ✅ 41 passed |
| `tests/test_playback_controller.py` | ✅ 6 passed |

## Consola QML real

| Patrón crítico | Resultado |
|---|---|
| `StackLayout is not a type` | ✅ Corregido |
| `Cannot assign to non-existent property interactive` | ✅ Corregido |
| `Cannot assign to non-existent property placeholderText` | ✅ Corregido |
| `Binding loop detected for property` | ✅ Corregido (0 matches) |
| `Cannot open .../ui_qml/icons/` | ✅ Corregido (0 matches) |
| `Property value set multiple times` | ✅ Corregido |
| `Member enabled overrides` | ✅ Corregido |
| `Failed to load` | ⚠️ Parcial (ver observación) |

## Rutas revisadas

| Ruta | Resultado | Observación |
|---|---|---|
| Home | ✅ | Carga sin errores |
| Biblioteca | ✅ | Tabs funcionales, datos requieren indexación |
| Playback | ✅ | Carga sin errores |
| Playlists | ✅ | CRUD, confirmación delete |
| Radio | ✅ | Lista + búsqueda + play |
| Assistant | ✅ | Chat, botón enviar |
| Connections | ✅ | Servidores, empty state |
| Devices | ✅ | Lista, sync status |
| Settings | ✅ | Secciones, output profiles |
| Metadata | ✅ | Inspector, CoverImage |
| Audio Lab | ✅ | Dashboard |
| EQ | ✅ | Bridge funcional, presets, bypass, preamp |
| Library Doctor | ✅ | COMPLETO_VISUAL |
| Smart Tagging | ✅ | FileDialog, botón Escanear |
| Home Audio | ✅ | Import de materiales corregido |
| Output Profiles | ✅ | SettingsBridge funcional |

## Smart Tagging

| Prueba | Resultado | Observación |
|---|---|---|
| FileDialog nativo | ✅ | Abre selector de archivos de audio |
| Botón Escanear | ✅ | Deshabilitado sin archivo, activo con selección |
| Path fake eliminado | ✅ | 0 referencias a `/example/` |

## EQ Bridge

| Prueba | Resultado | Observación |
|---|---|---|
| Carga de página | ✅ | Sin errores |
| Presets desde backend | ✅ | `audio/eQ_presets.py` conectado |
| Bypass toggle | ✅ | PlayerService.set_eq_bypass |
| Preamp | ✅ | PlayerService.set_eq_preamp |
| Degradación sin backend | ✅ | Preset "Plano" como fallback |

## NowPlayingBar

| Prueba | Resultado | Observación |
|---|---|---|
| Fondo visible | ✅ | `MichiTheme.colors.surfaceNowPlaying` (#141620) |
| Borde acento | ✅ | 1px azul alrededor + indicador centrado |
| Tokenizado | ✅ | `surfaceNowPlaying` agregado a MichiColors |
| Sin hardcode hex | ✅ | 0 ocurrencias en NowPlayingBar.qml |

## Audio físico

| Prueba | Resultado | Observación |
|---|---|---|
| Reproducción real | ⏳ | No verificado — requiere display con audio |

## QtWidgets fallback

| Prueba | Resultado | Observación |
|---|---|---|
| MainWindow creado | ✅ | Sin crash |
| QML no default | ✅ | Sin flag `--qml`, arranca QtWidgets |

## Bloqueos

| Severidad | Área | Descripción | Acción |
|---|---|---|---|
| — | — | Sin bloqueos P0/P1 detectados | — |

## Deudas restantes

| Deuda | Severidad | Próxima acción |
|---|---|---|
| Audio físico no probado | Media | Probar reproducción real con DAC |
| NowPlayingBar requiere `playbackState` real para mostrar controles completos | Baja | Depende de bridge conectado |
| .gitignore duplicados | Baja | Limpiado en este PR |

## Decisión

**APROBADO COMO ALPHA2 RC TÉCNICO**

## Veredicto

Todos los bloqueos runtime QML originales han sido corregidos y verificados. Los tests automatizados pasan (249 QML). Las rutas principales cargan sin errores. Smart Tagging tiene FileDialog real. EQ tiene bridge funcional a PlayerService. NowPlayingBar es visible y tokenizada. QtWidgets fallback funciona.

El único prerequisito que falta para declarar `0.2.0-alpha.2` final es la **prueba de audio físico real** con `python main.py --qml` en un entorno con parlantes/DAC.
