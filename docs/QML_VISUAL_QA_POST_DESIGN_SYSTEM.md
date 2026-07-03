# QML Visual QA — Post Design System

## Base
- Branch: `qml-visual-qa-polish`
- HEAD inicial: fec354e
- Commits revisados: 2a9d171, 28c5ef3, a30eaff, eb5c0af, 7cfa487, fec354e

## Design System
| Elemento | Estado | Observación |
|---|---|---|
| MichiTheme.qml | ✅ | 6 radius, 5 opacity, 3 layout, colors/typography/spacing/motion delegates |
| MichiColors.qml | ✅ | 45 propiedades de color |
| MichiSpacing.qml | ✅ | 7 tokens (xs→xxl, page) |
| MichiTypography.qml | ✅ | 11 tokens (sizes, weights) |
| MichiMotion.qml | ✅ | 3 duraciones + easing presets |
| MichiButton.qml | ✅ | primary/secondary/ghost/danger |
| MichiIconButton.qml | ✅ | hover/selected/disabled con tooltip |
| MichiSlider.qml | ✅ | hover/disabled con thumb |
| MichiBadge.qml | ✅ | 6 variantes (info, success, warning, danger, experimental, muted) |
| MichiProgressBar.qml | ✅ | Determinado e indeterminado |

## Imports y tokens
| Check | Resultado |
|---|---|
| `ActionButton` en código activo | ❌ No (solo docs históricos) |
| `MichiColors`/`MichiSpacing`/`MichiTypography`/`MichiMotion` directos | ✅ Solo `RouteTransition.qml` → corregido a `MichiTheme` |
| Emojis como controles | ✅ No |
| Colores hardcodeados en componentes | ✅ Solo valores de hover/disabled sin token (intencional) |

## Componentes canónicos
| Componente | Uso esperado | Estado |
|---|---|---|
| GlassPanel | Panel glass base | ✅ Tokenizado |
| GlassCard | Card glass con bordes | ✅ Tokenizado |
| SearchField | Campo de búsqueda | ✅ Tokenizado |
| SectionHeader | Encabezado de sección | ✅ Tokenizado |
| SidebarItem | Item de sidebar | ✅ Tokenizado |
| StatusBadge | Badge de estado fuente | ✅ Tokenizado |
| EmptyState | Estado vacío | ✅ Tokenizado (MichiButton) |

## Riesgos visuales
| Riesgo | Severidad | Acción |
|---|---|---|
| `MichiButton` no tiene test de `variant` específico | Baja | Cubierto por test de instanciación |
| `MichiSlider` no testea `stepSize`/`moved(value)` | Baja | Agregar test |
| `StatusBadge` usa `Qt.rgba` para variantes (sin token) | Baja | No hay token específico para badge backgrounds |
| `Main.qml` y `MichiApp.qml` tienen colores hardcodeados | Baja | Entry points, aceptable |

## Pantallas revisadas
| Pantalla | Resultado | Observación |
|---|---|---|
| Sidebar.qml | ✅ | Tokenizado |
| HeaderBar.qml | ✅ | Tokenizado |
| NowPlayingBar.qml | ✅ | Tokenizado, MichiIconButton |
| NowPlayingControls.qml | ✅ | MichiIconButton, sin ActionButton |
| PlaybackPage.qml | ✅ | MichiIconButton, MichiGlassPanel, tokens |
| HomePage.qml | ✅ | Tokenizado |
| LibraryPage.qml | ✅ | Tokenizado |
| SongTable.qml | ✅ | Tokenizado |
| AlbumGrid.qml | ✅ | Tokenizado |
| ConnectionsPage.qml | ✅ | Tokenizado |
| AssistantPage.qml | ✅ | Tokenizado |

## Tests
| Comando | Resultado |
|---|---|
| `ruff check .` | ✅ 1 pre-existing |
| `compileall` | ✅ |
| `smoke_startup` | ✅ |
| `smoke_ui_routes` | ✅ |
| `tests/qml/ -q` | 186 passed |

## Veredicto
Design System QML estable, sin regresiones visuales. No se requiere acción correctiva urgente.
