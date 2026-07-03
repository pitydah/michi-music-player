# Alpha2 Release Candidate Validation Report

## Base

- Branch: `alpha2-rc-validation-gate`
- Base commit: `13e87eb`
- Fecha: 2026-07-03
- Objetivo: Validar si el estado actual de `main` puede considerarse `0.2.0-alpha.2 release candidate`

## Resultado ejecutivo

| Gate | Resultado | Observación |
|---|---|---|
| Automated tests | ✅ | Todos pasan |
| QML runtime | ✅ | Sin errores críticos |
| Visual QA | ⚠️ | Parcial (entorno offscreen, requiere display) |
| Audio físico | ⏳ | No probado |
| Safe mode | ✅ | OK |
| QtWidgets fallback | ✅ | MainWindow creado correctamente |

**Decisión: APROBADO CON RIESGOS DOCUMENTADOS**

## Validación automatizada

| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `smoke_startup` | ✅ 7/7 |
| `smoke_ui_routes` | ✅ 2/2 |
| `check_runtime.py` | ✅ Todo listo |
| `tests/qml/ -q` | ✅ 238 passed |
| `tests/test_schema.py` | ✅ 15 passed |
| `tests/test_format_probe.py` | ✅ 41 passed |
| `tests/test_playback_controller.py` | ✅ 6 passed |

## Reglas QML

| Regla | Resultado | Observación |
|---|---|---|
| ActionButton activo | ✅ 0 | Solo docs históricos y test de ausencia |
| Emojis como controles | ✅ 0 | Ninguno |
| Flechas Unicode como controles | ✅ 0 | Ninguna |
| Imports directos Michi* | ✅ 0 | Todos via MichiTheme |
| Paths fake ejecutables | ✅ 0 | `/example/track.mp3` eliminado en PR #23 |
| Hardcoded hex en páginas | ✅ 0 | Solo en theme/components intencionales |
| Qt.rgba residuales | ✅ Documentados | Solo en componentes base (Glass, Slider, ProgressBar) y 1 en HomeAudioModeSelector (out of scope) |
| deletePlaylist con confirmación | ✅ 2 pasos | Corregido en PR #23 |

## Validación manual QML

| Área | Resultado | Observación |
|---|---|---|
| Startup | ✅ | Sin crash, Foundation loaded, 0 errores iconos |
| Sidebar | ✅ | 10 rutas, iconos SVG, collapse funciona |
| HeaderBar | ✅ | Título dinámico, search field |
| Home | ✅ | Hero visible, cards |
| Biblioteca | ✅ | 4 tabs funcionales |
| NowPlayingBar | ⚠️ | No verificado en display real |
| Reproducción real | ⏳ | No probado (requiere audio físico) |
| Playlists | ✅ | CRUD, confirmación delete, edit deshabilitado |
| Radio | ✅ | Lista + búsqueda + play |
| Assistant | ✅ | Chat + botón enviar |
| Connections | ✅ | Servidores, descubrimiento, empty state |
| Devices | ✅ | Lista, sync status |
| Settings | ✅ | Secciones, output profiles funcional |
| Metadata | ✅ | Inspector + artwork via CoverImage |
| Audio Lab | ✅ | Dashboard + subpáginas |
| EQ | ✅ | COMPLETO_VISUAL (marcado experimental) |
| Library Doctor | ✅ | COMPLETO_VISUAL (marcado experimental) |
| Smart Tagging | ✅ | PARCIAL (sin selector archivo) |
| Resize | ⏳ | No verificado (offscreen) |
| Cierre/reapertura | ⏳ | No verificado (offscreen) |

## Safe mode

| Prueba | Resultado | Observación |
|---|---|---|
| QML safe mode startup | ✅ | Foundation loaded sin errores |
| Rutas críticas sin crash | ✅ | Navegación funcional |
| Features experimentales gated | ✅ | Badge experimental presente |

## QtWidgets fallback

| Prueba | Resultado | Observación |
|---|---|---|
| MainWindow creado | ✅ | Sin crash |
| QML no default | ✅ | `main.py` sigue arrancando QtWidgets |
| Sidebar/navegación funcional | ⚠️ | QSS warnings preexistentes, no bloqueantes |

## Bloqueos

| Severidad | Área | Descripción | Acción requerida |
|---|---|---|---|
| — | — | Sin bloqueos P0/P1 detectados | — |

## Riesgos no bloqueantes

| Riesgo | Severidad | Acción recomendada |
|---|---|---|
| Audio físico no probado | Media | Probar reproducción real con DAC/altavoces |
| Prueba visual en display real | Media | Ejecutar `python main.py --qml` en escritorio Plasma/X11 |
| Smart Tagging sin selector archivo | Baja | PR futuro con selector desde Biblioteca |
| EQ sin backend DSP real | Baja | Migrar EqDialog a bridge QML |
| Library Doctor sin bridge | Baja | Migrar LibraryDoctorPanel a bridge QML |
| QSS warnings en QtWidgets | Baja | Deuda preexistente, no relacionada a QML |

## Decisión

**APROBADO CON RIESGOS DOCUMENTADOS**

## Veredicto

El estado actual de `main` (13e87eb) es candidato fuerte a `0.2.0-alpha.2`. Todos los tests automatizados pasan (238 QML + 15 schema + 41 format + 6 playback). El runtime QML carga sin errores de iconos ni crashes. Las reglas de migración se cumplen: 0 ActionButton, 0 emojis, 0 paths fake, delete con confirmación.

Sin embargo, **no puede declararse Alpha2 final** sin:
1. Prueba humana visual con `python main.py --qml` en escritorio real.
2. Prueba de reproducción con audio físico real.

Estos dos puntos quedan como prerequisitos para declarar `0.2.0-alpha.2` listo. El release automatizado gate está aprobado. El QML sigue siendo **experimental, no default**.
