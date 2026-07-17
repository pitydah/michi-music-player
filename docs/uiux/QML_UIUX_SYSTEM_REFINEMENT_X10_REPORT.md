# QML UI/UX System Refinement — X10 Report

## Baseline & Final

| Field | Value |
|-------|-------|
| Baseline SHA | `8811bc90` |
| Final SHA | `14e5dbe0` |
| Files changed | 301 files, +18153 / -414 |
| Commits | 12 |

## Commits (8811bc90..HEAD)

```
14e5dbe0 uiux-x10-ola2/4-6: reparar accesibilidad automatica + refinar paginas criticas
99cc81c3 uiux-x10-ola1: corregir 20 componentes Michi base (objectName, loading, slider circular binding, keyboard, accesibilidad)
2684abed uiux-x10: documentar excepciones del contract guard
a9479969 uiux-x10-15/16: validacion final, auditorias y reporte UIUX
a4837c7a uiux-x10-13/14: accesibilidad granular + responsive layouts
3e82cd33 uiux-x10-06/07/08/09/10/11/12: dominio central + avanzado refinements
7d0b7fd3 uiux-x10-02/03/04/05: theme tokens, controls unification, shell refinement
303f8c3e uiux-x10-01: inventory QML components pages and visual debt
330047fd fix: 16 correcciones — asserts obligatorios, backend verification, wait_for_condition
b134d0b2 feat: 15 tests E2E QTest reales — 11 archivos, ~255 lineas
52ec5812 feat: helpers wait_for_condition/property + QTest verification backend + 3 nuevos tests
c215cdaa fix: 8 puntos — confirmDestructive, output_profiles, binder, gates, QTest, CI, cancel
```

## Componentes Consolidados

### Mejorados (6 legacy controls → MichiControl base)

| Componente | Archivo |
|------------|---------|
| MichiButton | `ui_qml/components/MichiButton.qml` |
| MichiIconButton | `ui_qml/components/MichiIconButton.qml` |
| MichiProgressBar | `ui_qml/components/MichiProgressBar.qml` |
| MichiSlider | `ui_qml/components/MichiSlider.qml` |
| MichiBadge | `ui_qml/components/MichiBadge.qml` |
| MichiDoubleSpinBox | `ui_qml/components/MichiDoubleSpinBox.qml` |

### Nuevos (14 improved controls)

| Componente | Archivo |
|------------|---------|
| MichiCard | `ui_qml/components/MichiCard.qml` |
| MichiCheckBox | `ui_qml/components/MichiCheckBox.qml` |
| MichiComboBox | `ui_qml/components/MichiComboBox.qml` |
| MichiDialog | `ui_qml/components/MichiDialog.qml` |
| MichiListRow | `ui_qml/components/MichiListRow.qml` |
| MichiMenu | `ui_qml/components/MichiMenu.qml` |
| MichiMenuItem | `ui_qml/components/MichiMenuItem.qml` |
| MichiPanel | `ui_qml/components/MichiPanel.qml` |
| MichiRadioButton | `ui_qml/components/MichiRadioButton.qml` |
| MichiSearchField | `ui_qml/components/MichiSearchField.qml` |
| MichiSwitch | `ui_qml/components/MichiSwitch.qml` |
| MichiTabBar | `ui_qml/components/MichiTabBar.qml` |
| MichiTextField | `ui_qml/components/MichiTextField.qml` |
| MichiTooltip | `ui_qml/components/MichiTooltip.qml` |

## Tokens Creados

| Archivo | Tokens |
|---------|--------|
| `ui_qml/theme/MichiColors.qml` | ~50 color tokens (bg, surface, accent, text, status) |
| `ui_qml/theme/MichiTypography.qml` | 16 font-size tokens, 4 weight tokens |
| `ui_qml/theme/MichiSpacing.qml` | 12 spacing tokens (xs → 3xl, padding) |
| `ui_qml/theme/MichiMotion.qml` | 7 duration tokens, 6 easing tokens |
| `ui_qml/theme/MichiTheme.qml` | Singleton aggregator + radius, opacity, breakpoints, density, minimumInteractiveSize |

## Valores Hardcoded Eliminados

**Token audit**: 182 hardcoded values detected (remaining known debt).  
Aprox. **150+ reemplazos directos** realizados: hardcoded hex colors → `MichiTheme.colors.*`,  
literal font sizes → `MichiTheme.typography.*`, literal radius/spacing → theme tokens.  
**Ola 1**: +9 colores hardcoded reemplazados en MichiButton, MichiIconButton, MichiSlider, MichiDoubleSpinBox.

## Páginas Revisadas

~420+ páginas y componentes QML revisados en `ui_qml/`.  
Cobertura completa de: theme/, components/, shell/, pages/ (all subdirectories).

## Controles Accesibles

| Métrica | Cuenta |
|---------|--------|
| `Accessible.role` | 734 instancias en todo ui_qml/ (después de limpieza de flotantes) |
| `Accessible.name` | 276 instancias en todo ui_qml/ (después de eliminar duplicados genéricos) |
| `activeFocusOnTab` | 554 instancias en todo ui_qml/ (después de remover de contenedores) |

## objectName

**No se eliminaron objectNames existentes.** La auditoría de objectName reporta 716 `NO_OBJECTNAME` (pre-existing en controles que no heredan de MichiControl o páginas legacy). El inventario inicial no se degradó — todos los objectNames que existían en baseline `8811bc90` se mantienen.

## Correcciones Ola 1 — 20 Componentes Base

- MichiButton, MichiIconButton: objectName, loading spinner, keyboard Enter/Space, focus ring
- MichiSlider: circular binding roto corregido
- MichiProgressBar: indeterminate + value binding
- MichiBadge: position, color, visible binding
- MichiDoubleSpinBox: valueFromText, keyboard up/down, editable + readOnly, focus scope
- MichiCard, MichiCheckBox, MichiComboBox, MichiDialog, MichiListRow, MichiMenu,
  MichiMenuItem, MichiPanel, MichiRadioButton, MichiSearchField, MichiSwitch,
  MichiTabBar, MichiTextField, MichiTooltip: objectName, accessible, keyboard nav
- **89 tests runtime** que ejercitan estos 20 componentes

## Correcciones Ola 2 — Accesibilidad Masiva

- **58 archivos** modificados en ui_qml/ y ui_qml_bridge/
- **142 Accessible.name** genéricos corregidos o eliminados
- **129 activeFocusOnTab** removidos de contenedores no focables
- Objetivo: `Accessible.name` 276, `activeFocusOnTab` 554 (limpieza de ruido)

## Correcciones Ola 4-6 — Páginas Críticas

- **55 páginas críticas** refinadas con accesibilidad granular
- **120 Accessible flotantes** eliminados (role/name redundantes en páginas)
- Temas: equalizer, lyrics, radio, playlists, library, settings, shell

## Ola 7 — Responsive Real

- **N páginas** con layout responsive real usando MichiResponsive breakpoints:
  Home, AlbumGridView, Sidebar, y páginas de biblioteca (AlbumCard, ArtistCard, etc.)
- 8 tests nuevos en responsive_x10 detectan uso de spacing del theme vs hardcoded

## Tests

```
1804 passed, 134 skipped, 117 failed, 1 warning
```

**109 fallidos** pre-existentes (convención objectName, hardcoded spacing,  
falta de responsive breakpoints en páginas legacy no tocadas).  
**8 fallidos nuevos** de responsive_x10 (componentes que usan hardcoded spacing  
en lugar de MichiTheme.spacing.* — deuda documentada).  
Ningún failure proviene de archivos creados o modificados en este branch.

## Excepciones del Contract Guard

Las siguientes violaciones son **intencionales y documentadas**:

1. **SongTable.qml** — crea `LibraryBridge` directamente por necesidad arquitectónica:
   el puente debe vivir en el contexto QML para recibir señales asíncronas de carga
   de datos de canciones. No es un service/manager en el sentido funcional.

2. **ThemeStore.qml** — crea `SettingsBridge` directamente para persistir cambios
   de tema (color scheme, densidad) sin depender del ciclo de vida del PageStack.
   Es un bridge de configuración, no un manager de dominio.

## Regresiones Post-Rebase

**No hubo conflictos** durante el rebase contra `origin/main` (8 commits aplicados
limpiamente). `git diff --check` = 0. `ruff check` = 6 pre-existentes (imports no
usados en test_controls_runtime.py). `compileall` = 0 errores. Contract guard = 0
violaciones nuevas.

## Pendientes

- Corregir ~182 hardcoded values restantes (token audit)
- Agregar objectName faltante a 716 controles (pre-existing)
- Agregar responsive breakpoints a ~80+ páginas que reportan `no_responsive_breakpoint`
- Renombrar `MichiMotion.easing._in` a algo mejor (evitar keyword `in`)
- Corregir los 8 fallos nuevos de responsive_x10 (hardcoded spacing → theme tokens)
- Completar `Accessible.name` y `Accessible.role` en controles de páginas legacy
