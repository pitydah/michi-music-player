# QML Design System

## Objetivo
Base visual premium para Michi Music Player — dark premium, smoked glass, tipografía clara.

## Principios
- Dark premium con acento azul #8FB7FF
- Smoked glass (fondo semitransparente con bordes suaves)
- Componentes reutilizables con tokens
- No duplicar backend
- QtWidgets fallback estable
- QML experimental avanzado

## Tokens

| Archivo | Propósito | Propiedades |
|---|---|---|
| `MichiColors.qml` | Colores | 45 tokens (bg, surface, border, text, accent, badge, shadow) |
| `MichiSpacing.qml` | Espaciado | 7 tokens (xs→xxl, page) |
| `MichiTypography.qml` | Tipografía | 11 tokens (sizes hero→badge, weights light→bold) |
| `MichiMotion.qml` | Animación | 3 duraciones (fast/normal/slow) + easing presets |
| `MichiTheme.qml` | Agregador + extras | Colors + Typography + Spacing + Motion + radius (6), opacity (5), layout constants |

## Componentes

| Componente | Uso | Estado |
|---|---|---|
| `MichiButton.qml` | Botón genérico (primary/secondary/ghost/danger) | ✅ Nuevo |
| `MichiIconButton.qml` | Botón circular para controles/toolbar | ✅ Nuevo |
| `MichiSlider.qml` | Slider de progreso/volumen con thumb | ✅ Nuevo |
| `MichiBadge.qml` | Badge de estado (info/success/warning/danger/experimental/muted) | ✅ Nuevo |
| `GlassPanel.qml` | Panel glass base | ✅ Existente |
| `GlassCard.qml` | Card glass con bordes | ✅ Existente |
| `ActionButton.qml` | Botón de acción específico | ✅ Existente |
| `SearchField.qml` | Campo de búsqueda | ✅ Existente |
| `SectionHeader.qml` | Encabezado de sección | ✅ Existente |
| `SidebarItem.qml` | Item de sidebar | ✅ Existente |
| `StatusBadge.qml` | Badge de estado fuente | ✅ Existente |
| `EmptyState.qml` | Estado vacío | ✅ Existente |

## Migración aplicada

| Pantalla | Cambio |
|---|---|
| `NowPlayingBar.qml` | Usa `MichiTheme` tokens (colores, spacing, height, border) |
| `NowPlayingControls.qml` | Reemplazado `GlassMaterial`+`MouseArea` por `MichiIconButton` |
| `PlaybackPage.qml` | Usa `MichiTheme` tokens, `MichiIconButton`, `MichiGlassPanel` en vez de `GlassMaterial` |

## Reglas
- No lógica de DB en QML
- No estilos inline dispersos (usar tokens)
- No emojis como controles
- No reemplazar QtWidgets todavía
- Los componentes nuevos deben usar `MichiTheme` tokens exclusivamente
