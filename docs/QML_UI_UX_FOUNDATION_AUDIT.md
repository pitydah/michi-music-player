# QML UI/UX Foundation Audit

## Estado post-estabilización
- Archivos QML principales: 87 archivos .qml + 5 qmldir
- Componentes existentes: 20+ (MichiButton, MichiIconButton, MichiSlider, MichiBadge, MichiProgressBar, GlassCard, GlassPanel, HeroPanel, SearchField, SectionHeader, SidebarItem, StatusBadge, etc.)
- Tokens existentes: MichiColors.qml (45 propiedades), MichiSpacing.qml (7), MichiTypography.qml (11), MichiMotion.qml, MichiTheme.qml
- NowPlayingBar conectado a PlayerService vía NowPlayingBridge
- PlaybackBridge como fachada de compatibilidad

## Problemas visuales detectados

| Problema | Ubicación |
|---|---|
| Migración incompleta a `MichiTheme` | Varias pantallas antiguas aún importan materiales/tokens directos |
| Iconografía basada en texto | `MichiIconButton` usa glifos ASCII como transición hasta tener proveedor de iconos |
| Glass heredado | Muchas páginas usan `GlassMaterial` directamente; mantenerlo como material base |
| Estados vacíos dispares | `EmptyState.qml` existe, pero no todas las páginas lo usan todavía |

## Duplicación visual

| Tipo | Ubicación | Problema |
|---|---|---|
| Glass background | GlassMaterial.qml + GlassPanel.qml + GlassCard.qml | Resuelto como jerarquía: material base + wrappers canónicos |
| Search field | SearchField.qml | Pendiente de migración completa a `MichiTheme` |
| Icon button | NowPlayingControls.qml | Resuelto con `MichiIconButton` |

## Riesgos

| Riesgo | Severidad | Acción |
|---|---|---|
| Migración visual parcial | Media | Migrar AppShell/sidebar/header en fases pequeñas |
| Glifos ASCII como iconos | Media | Sustituir por proveedor de iconos cuando exista contrato estable |
| Uso directo de `GlassMaterial` | Baja | Preferir `GlassPanel`/`GlassCard` en componentes nuevos |

## Decisión
Design System Foundation queda estabilizado como v0.1: tokens agregados, componentes base creados,
`ActionButton` retirado, tests de carga presentes y CI debe ejecutarse en modo QML headless.
