# Component Consolidation — Presentation UI/UX

Inventario de componentes canónicos del modo presentación. Cada componente
tiene **una sola implementación**: prohibido duplicar variantes locales.

## Superficies y fondo

| Componente | Rol |
|------------|-----|
| MichiAmbientBackground | Fondo ambiental único de la app (canvas + glow + grain) |
| MichiHeroSurface | Superficie héroe para páginas con encabezado destacado |
| MichiArtworkGlow | Glow derivado del artwork (solo contexto musical/NowPlaying) |
| MichiSectionSurface | Superficie de sección estándar (nivel 1) |

## Páginas de features

| Componente | Rol |
|------------|-----|
| PlannedFeaturePage | Página honesta para features planeados (badge PLANNED, sin datos falsos) |
| IntegrationPreviewPage | Preview de integración con estado real (configuration_required, planned) |

## Componentes únicos (single source of truth)

| Componente | Rol |
|------------|-----|
| StatusBadge | **Único** badge de estado para toda la app (ready/planned/error/warning) |
| ConfirmDialog | **Canónico** para confirmaciones, incluidas acciones destructivas |
| PlaybackTransport | **Único** control de transporte (play/pause/next/prev) |

## Reglas

1. Si necesitás un badge de estado, usá `StatusBadge`. No crees otro.
2. Toda confirmación pasa por `ConfirmDialog`. Ningún botón destructivo
   ejecuta sin él.
3. El transporte de reproducción es `PlaybackTransport`. NowPlayingBar y
   cualquier mini-player lo consumen, no lo reimplementan.
4. Las páginas planeadas usan `PlannedFeaturePage` con `honest: true`:
   nunca muestran datos demo como si fueran reales.
