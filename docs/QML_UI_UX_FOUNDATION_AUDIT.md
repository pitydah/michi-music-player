# QML UI/UX Foundation Audit

## Estado actual
- Archivos QML principales: 87 archivos .qml + 5 qmldir
- Componentes existentes: 20+ (ActionButton, GlassCard, GlassPanel, HeroPanel, SearchField, SectionHeader, SidebarItem, StatusBadge, etc.)
- Tokens existentes: MichiColors.qml (45 propiedades), MichiSpacing.qml (7), MichiTypography.qml (11), MichiMotion.qml, MichiTheme.qml
- NowPlayingBar conectado a PlayerService vía NowPlayingBridge
- PlaybackBridge como fachada de compatibilidad

## Problemas visuales detectados

| Problema | Ubicación |
|---|---|
| Tokens de radius no existe como singleton | Todos los componentes tienen radius hardcodeados |
| Tokens de opacity/borderWidth no existen | Todos los componentes tienen valores hardcodeados |
| `MichiTheme.qml` no se usa consistentemente | Muchos componentes importan colores/spacing directo |
| `MichiMotion.qml` subutilizado | Solo 1 animación referenciada |
| No hay `MichiButton.qml` genérico | Solo `ActionButton.qml` específico |
| No hay `MichiSlider.qml` genérico | SeekBar y Volume son componentes separados |
| No hay `MichiEmptyState.qml` genérico | `EmptyState.qml` existe pero no se usa en todas las páginas |
| No hay `MichiBadge.qml` genérico | `StatusBadge.qml` existe pero no cubre todos los casos |
| Colores hardcodeados en NowPlayingBar | Algunos colores no usan tokens |
| radius hardcodeados en ~30 lugares | 8, 10, 12, 14, 16, 17, 22 |

## Duplicación visual

| Tipo | Ubicación | Problema |
|---|---|---|
| Glass background | GlassMaterial.qml + GlassPanel.qml + GlassCard.qml | Lógica duplicada |
| Search field | SearchField.qml | No usa tokens de spacing |
| Icon button | NowPlayingControls.qml | Implementación manual, no componente reutilizable |

## Riesgos

| Riesgo | Severidad | Acción |
|---|---|---|
| NowPlayingBar sin tokens de color | Media | Migrar a tokens en esta fase |
| Radius hardcodeados por todo el código | Baja | Agregar tokens a Theme, migrar gradual |
| Sin MichiSlider genérico | Media | Crear componente en esta fase |
| Sin MichiButton/MichiIconButton genérico | Media | Crear componentes en esta fase |

## Decisión
Implementar Design System Foundation: agregar tokens faltantes, crear 6 componentes base,
migrar NowPlayingBar a usar tokens y componentes.
