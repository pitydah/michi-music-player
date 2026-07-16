# QML UI/UX System Refinement — X10 Report

## Baseline & Final

| Field | Value |
|-------|-------|
| Baseline SHA | `8811bc90` |
| Final SHA | `101403ce` |
| Files changed | 274 files, +18146 / -269 |
| Commits | 4 |

## Commits (8811bc90..HEAD)

```
b152836b uiux-x10-01: inventory QML components pages and visual debt
f6bad6da uiux-x10-02/03/04/05: theme tokens, controls unification, shell refinement
ab28c4dc uiux-x10-06/07/08/09/10/11/12: dominio central + avanzado refinements
101403ce uiux-x10-13/14: accesibilidad granular + responsive layouts
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

## Páginas Revisadas

~420+ páginas y componentes QML revisados en `ui_qml/`.  
Cobertura completa de: theme/, components/, shell/, pages/ (all subdirectories).

## Controles Accesibles

| Métrica | Cuenta |
|---------|--------|
| `Accessible.role` | 1112 instancias en todo ui_qml/ |
| `Accessible.name` | 705 instancias en todo ui_qml/ |
| `activeFocusOnTab` | 894 instancias en todo ui_qml/ |

## objectName

**No se eliminaron objectNames existentes.** La auditoría de objectName reporta 716 `NO_OBJECTNAME` (pre-existing en controles que no heredan de MichiControl o páginas legacy). El inventario inicial no se degradó — todos los objectNames que existían en baseline `8811bc90` se mantienen.

## Responsive

| Componente | Estado |
|------------|--------|
| MichiResponsive | Foundation singleton con breakpoints |
| Home | Página responsive con layout adaptativo |
| AlbumGridView | Grid adaptativo con MichiResponsive |
| Sidebar | Ancho responsive (`sidebarCompact`/`sidebarRegular`) |

## Tests

```
1713 passed, 136 skipped, 117 failed (pre-existing), 1 warning
```

Los 117 failures son pre-existentes (errores de convención de objectName,  
hardcoded spacing, y falta de responsive breakpoints en páginas legacy).  
Ningún failure proviene de archivos creados o modificados en este branch.

## Pendientes

- Revisar las 2 violaciones del contract guard (`SongTable.qml` y `ThemeStore.qml`:  
  creación directa de servicios/managers)
- Corregir ~182 hardcoded values restantes (token audit)
- Agregar objectName faltante a 716 controles (pre-existing)
- Agregar responsive breakpoints a ~80+ páginas que reportan `no_responsive_breakpoint`
- Renombrar `MichiMotion.easing._in` a algo mejor (evitar keyword `in`)
- Completar `Accessible.name` y `Accessible.role` en controles de páginas legacy
