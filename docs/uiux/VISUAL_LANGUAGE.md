# Visual Language — Michi Music Player (Presentation)

Lenguaje visual canónico para el modo de presentación. Sobrio, audiófilo,
premium. Nada de datos falsos presentados como reales.

## Colores base

| Token | Valor | Uso |
|-------|-------|-----|
| Canvas | `#090B11` | Fondo raíz de la app |
| Acento primario | `#8FB7FF` | Navegación, selección, foco, headers, cards |
| Acento tenue | `rgba(143,183,255,0.34)` | Halos, bordes activos suaves |
| Texto principal | `rgba(255,255,255,0.85–1.00)` | Nunca por debajo de 0.78 en navegación |
| Texto secundario | `rgba(255,255,255,0.62)` | Subtítulos |
| Texto muted | `rgba(255,255,255,0.52)` | Metadatos, hints |

## Acentos musicales cálidos

`#FF7A00` (naranja cálido) y familia fucsia/magenta están **reservados** a:
- Sliders de NowPlayingBar
- Bandas de EQ

Prohibidos en sidebar, cards, botones, headers y navegación: esos usan el
azul frío `#8FB7FF`.

## Superficies

| Nivel | Nombre | Descripción |
|-------|--------|-------------|
| 0 | Canvas | `#090B11` sólido, sin bordes |
| 1 | Section | `rgba(255,255,255,0.045)` + borde `rgba(255,255,255,0.08)` |
| 2 | Card | Gradiente vertical sutil (0.065 → 0.025) + borde 0.08 |
| 3 | Floating | Popups, diálogos, menús: mayor elevación, borde hover `rgba(143,183,255,0.28)` |

## Tipografía

Escala consistente con pesos válidos únicamente: **bold, 500, 600, 700**.
No usar 540/680/720/760 (no son pesos CSS válidos).

- Título de página: bold
- Header de sección: 600–700, opacidad 0.88
- Item de navegación: 500–600, opacidad 0.85
- Subtítulo/metadato: 500, opacidad 0.62

## Iconografía

- Siempre vía renderer alpha-safe: `get_qicon()`, `get_pixmap()`,
  `get_sidebar_icon()`. Nunca `QIcon(path)` / `QPixmap(path)` directos.
- `render_mode="native_color"` para SVGs con color propio.
- `render_mode="symbolic_tint"` para SVGs monocromos teñidos por estado
  (normal/hover/active).
- Registro único en `ui/icon_registry.py` (38+ iconos).

## Motion

| Duración | Uso |
|----------|-----|
| Fast (~120ms) | Hover, micro-interacciones, scale de botones |
| Normal (~220ms) | Transiciones de página, aparición de cards |
| Slow (~400ms) | Ambient glow, cambios de fondo, reveals de héroe |

Respeta reduced-motion: sin animaciones decorativas cuando el sistema lo pide.

## Texturas

- **Grain**: overlay de ruido sutil, opacidad máxima 0.02. Nunca perceptible
  de forma consciente.
- **Ambient glow**: halo radial frío (`#8FB7FF` a baja opacidad) detrás de
  superficies héroe y artwork. Cálido solo en contexto NowPlaying.
