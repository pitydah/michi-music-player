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
| `MichiSlider.qml` | Slider de progreso/volumen con thumb, foco y teclado | ✅ Nuevo |
| `MichiBadge.qml` | Badge de estado (info/success/warning/danger/experimental/muted) | ✅ Nuevo |
| `GlassPanel.qml` | Panel glass base | ✅ Existente |
| `GlassCard.qml` | Card glass con bordes | ✅ Existente |
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
| `PlaybackPage.qml` | Usa `MichiTheme` tokens, `MichiIconButton` y paneles glass canónicos |

## Reglas
- No lógica de DB en QML
- No estilos inline dispersos (usar tokens)
- No emojis como controles
- No reemplazar QtWidgets todavía
- Los componentes nuevos deben usar `MichiTheme` tokens exclusivamente

## Guía de contribución visual

### Cómo agregar un componente QML nuevo

1. Crear archivo en `ui_qml/components/MiComponente.qml`
2. Importar `"../theme"` para acceder a `MichiTheme`
3. Usar exclusivamente tokens de `MichiTheme` para colores, spacing, tipografía, radius y animación
4. Registrar en `ui_qml/components/qmldir`
5. Agregar test de instanciación en `tests/qml/test_qml_components.py`

### Cómo migrar una página existente

Reemplazar:
- `MichiColors.xxx` → `MichiTheme.colors.xxx`
- `MichiSpacing.xxx` → `MichiTheme.spacing.xxx`
- `MichiTypography.xxx` → `MichiTheme.typography.xxx`
- `MichiMotion.xxx` → `MichiTheme.motion.xxx`
- `radius: N` → `MichiTheme.radiusSm|Md|Lg|Xl`
- `border.width: 1` → `MichiTheme.borderWidth`
- `border.width: 2` → `MichiTheme.borderWidthFocus`

### Qué NO hacer

- ❌ No hardcodear colores (`#XXXXXX` o `Qt.rgba(...)`) — usar `MichiTheme.colors`
- ❌ No importar `MichiColors`, `MichiSpacing`, `MichiTypography` directamente — usar `MichiTheme`
- ❌ No usar emojis como controles — usar `MichiIconButton` con glifos ASCII estables o un proveedor de iconos futuro
- ❌ No usar `ActionButton` — fue retirado; usar `MichiButton`
- ❌ No poner lógica de DB o backend en QML — usar bridges Python
- ❌ No reemplazar QtWidgets todavía — mantener coexistencia

### Tokens disponibles

| Categoría | Acceso | Ejemplos |
|---|---|---|
| Colores | `MichiTheme.colors.xxx` | `bgApp`, `surfaceCard`, `textPrimary`, `accentBlue` |
| Espaciado | `MichiTheme.spacing.xxx` | `xs`, `sm`, `md`, `lg`, `xl`, `xxl`, `page` |
| Tipografía | `MichiTheme.typography.xxx` | `bodySize`, `sectionTitleSize`, `weightMedium` |
| Motion | `MichiTheme.motion.xxx` | `fast`, `normal`, `slow`, `easing.standard` |
| Radius | `MichiTheme.radiusXx` | `radiusSm: 8`, `radiusMd: 12`, `radiusLg: 16`, `radiusXl: 22`, `radiusPill: 999` |
| Layout | `MichiTheme.xxx` | `borderWidth: 1`, `sidebarWidth: 250`, `nowPlayingHeight: 88`, `headerHeight: 56` |

### Componentes disponibles

| Componente | Propósito |
|---|---|
| `MichiButton` | Botón genérico (primary, secondary, ghost, danger) |
| `MichiIconButton` | Botón circular para controles/toolbar |
| `MichiSlider` | Slider de progreso/volumen con `moved(value)`, foco y teclado |
| `MichiBadge` | Badge de estado (info, success, warning, danger, experimental, muted) |
| `MichiProgressBar` | Barra de progreso (determinada o indeterminada) |
| `GlassPanel` | Panel glass base |
| `GlassCard` | Card glass con bordes |
| `SearchField` | Campo de búsqueda con debounce |
| `SectionHeader` | Encabezado de sección |
| `SidebarItem` | Item de sidebar |
| `StatusBadge` | Badge de estado fuente |
| `EmptyState` | Estado vacío con icono, título, subtítulo y acción |

### Glass canónico

`GlassMaterial` es el material base. `GlassPanel` y `GlassCard` son wrappers canónicos para layouts:

- Usar `GlassPanel` para superficies de página o paneles de herramienta.
- Usar `GlassCard` para elementos repetidos, tarjetas de lista o previews.
- Evitar crear nuevos fondos glass con `Rectangle` manual si `GlassPanel` o `GlassCard` cubren el caso.

### Ejemplo: Card simple usando tokens

```qml
import QtQuick
import "../theme"
import "../components"

GlassPanel {
    width: parent.width
    height: 120

    Column {
        anchors.centerIn: parent
        spacing: MichiTheme.spacing.sm

        Text {
            text: "Título"
            font.pixelSize: MichiTheme.typography.cardTitleSize
            color: MichiTheme.colors.textPrimary
        }

        Text {
            text: "Subtítulo"
            font.pixelSize: MichiTheme.typography.bodySize
            color: MichiTheme.colors.textSecondary
        }

        MichiButton {
            text: "Acción"
            variant: "primary"
            onClicked: console.log("click")
        }
    }
}
```
