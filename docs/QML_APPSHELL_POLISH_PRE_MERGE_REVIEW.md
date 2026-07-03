# QML AppShell Polish — Pre-Merge Review

## Base
- Branch: `qml-appshell-polish`
- Base branch: `main`
- HEAD: `48cf3b9`
- Commit revisado: `48cf3b9 fix(qml): stabilize app shell visual polish`

## Alcance
| Área | Estado | Observación |
|---|---|---|
| App root | ✅ | `#070A10` → `MichiTheme.colors.bgApp` |
| Sidebar | ✅ | Flickable scrollable + separador visual + mejor jerarquía |
| HeaderBar | ✅ | SearchField width refinado |
| PageStack / RouteTransition | ✅ | Behavior on opacity para transición suave |
| NowPlayingBar | ✅ | Info responsiva, cover tokenizado |
| Tests QML | ✅ | 207 passed (+11 tests nuevos) |
| Docs | ✅ | Audit creado + pre-merge review |

## Archivos modificados
| Archivo | Motivo |
|---|---|
| `ui_qml/Main.qml` | Color hardcodeado → token `bgApp` |
| `ui_qml/MichiApp.qml` | Color hardcodeado → token `bgApp` |
| `ui_qml/shell/Sidebar.qml` | Flickable + separador + mejor jerarquía |
| `ui_qml/shell/HeaderBar.qml` | SearchField width refinado |
| `ui_qml/shell/PageStack.qml` | Behavior on opacity para fade |
| `ui_qml/shell/RouteTransition.qml` | Simplificado a helper dinámico |
| `ui_qml/components/NowPlayingBar.qml` | Info width dinámico |
| `ui_qml/components/NowPlayingControls.qml` | Item wrapper para play button |
| `ui_qml/components/NowPlayingInfo.qml` | `width: 200` → `parent.width` |
| `ui_qml/components/NowPlayingCover.qml` | `Qt.rgba(1,1,1,0.04)` → `borderInner` |
| `tests/qml/test_qml_components.py` | 11 tests nuevos (shell, nowplaying, ActionButton ausente) |
| `docs/QML_APPSHELL_POLISH_AUDIT.md` | Nueva auditoría |
| `docs/QML_VISUAL_QA_POST_DESIGN_SYSTEM.md` | Actualizado: 207 passed |

## Restricciones verificadas
| Restricción | Resultado |
|---|---|
| No audio/backend | ✅ Solo `ui_qml/`, `tests/qml/`, `docs/` |
| No `window.py` | ✅ No tocado |
| No `ui_qml_bridge` | ✅ No tocado |
| No `ActionButton` activo | ✅ Solo en test de verificación de ausencia |
| No imports directos prohibidos | ✅ 0 matches |
| No emojis como controles | ✅ 0 matches |
| QML no default | ✅ `main.py` no modificado |

## Validación local
| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ All checks passed |
| `compileall` | ✅ OK |
| `smoke_startup` | ✅ 7/7 |
| `smoke_ui_routes` | ✅ 2/2 |
| `tests/qml/ -q` | ✅ 207 passed |
| `tests/test_schema.py -q` | ✅ 15 passed |

## Riesgos restantes
| Riesgo | Severidad | Acción recomendada |
|---|---|---|
| `NowPlayingCover` depende de plugin C++ `MichiCover` (no instanciable en tests aislados) | Baja | Tests de existencia ya cubren; depende del runtime |
| Sidebar con glyphs en vez de iconos SVG | Baja | Post 0.2.0-alpha.2 |
| Sidebar compact/collapse no implementado | Baja | Post 0.2.0-alpha.2 |

## Veredicto
**Aprobado para PR hacia main.** Todos los checks locales están verdes. No hay cambios fuera de alcance. No se toca backend/audio/QtWidgets. No se declara beta.
