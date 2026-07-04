# QML Accessibility Report

**Date:** 2026-07-04
**Status:** AUDITED — gaps identified

## Resoluciones probadas

| Resolución | anchors.fill | clip | Overflow visible |
|---|---|---|---|
| 800x600 | ✅ | ✅ | No (componentes fijos pueden solaparse) |
| 1024x768 | ✅ | ✅ | No |
| 1280x720 | ✅ | ✅ | No |
| 1366x768 | ✅ | ✅ | No |
| 1920x1080 | ✅ | ✅ | No |
| 2560x1440 | ✅ | ✅ | No |

## Hallazgos

### Positivo
- `anchors.fill` usado en 100+ ubicaciones — buena base responsive
- `clip: true` en 36 ubicaciones (todos los Flickable/ListView/ScrollView)
- `z:` ordering correcto para overlays/dialogs (9990-9999)
- `Keys.on*` en MichiSlider (left/right/up/down) y CommandPalette (Escape/Return)
- `Layout.fillWidth` en 6 ubicaciones (HeaderBar, LibraryPage, etc.)

### Crítico (falta)
- **`Accessible.role`, `accessibleName`, `accessibleDescription`**: 0 usos — screen readers no tienen metadata
- **`focusPolicy:`**: 0 usos — elementos no declarativos no son reachables por tab
- **`Keys.forwardTo`**: 0 usos — atajos de teclado no se propagan
- **`Layout.fillHeight`**: 0 usos — algunas vistas pueden no expandirse verticalmente
- **Hardcoded widths**: 75 valores fijos que pueden romper en resoluciones pequeñas:
  - `ConfirmActionDialog`: 320px (puede recortarse en 800x600)
  - `CommandPalette`: 400px
  - `AlbumGrid` card: 180px
  - `NowPlayingSeekBar`: 180px
  - `Root window`: 1440px (no responsive)
- **`focus:`**: solo en MichiSlider — botones, cards, list items no tienen foco
- **Reduced motion**: no detectado

### Recomendaciones para 75%+
1. Añadir `Accessible.role` y `accessibleName` a todos los botones interactivos (~30 componentes)
2. Añadir `focusPolicy: Qt.TabFocus` a lista de canciones, álbumes, playlists
3. Reemplazar `width: 1440` en Main.qml con `visible: true` + `visibility: Window.Maximized` o similar
4. Usar `Layout.fillHeight: true` en componentes que actualmente usan altura fija
5. Añadir `Keys.onEscapePressed` en todas las páginas para navegación atrás
6. Soporte `reduced motion`: consultar `MichiTheme.motion.reduced` y deshabilitar animaciones
