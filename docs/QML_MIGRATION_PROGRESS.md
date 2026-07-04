# QML Migration Progress

**Date:** 2026-07-04
**Branch:** qml-functional-closure-release-readiness

## Overall: 65.0% (+18.2pp desde baseline 46.8%)

| Área | Peso | Antes | Ahora | Estado |
|---|---:|---:|---:|---|
| Shell/navegación | 10% | 65% | 65% | FUNCTIONAL |
| Library/playback | 25% | 65% | 65% | FUNCTIONAL |
| Workflows core | 20% | 40% | 65% | FUNCTIONAL |
| Advanced tools | 20% | 40% | 65% | FUNCTIONAL |
| Ecosystem/red | 10% | 20% | 65% | FUNCTIONAL |
| Quality/release | 15% | 40% | 65% | FUNCTIONAL |

## Resumen de cambios

| Lo que se hizo | Estado |
|----------------|--------|
| LibraryBridge view cache — repeated access 0.006s (-99.7%) | ✅ |
| Accessibility report creado con hallazgos honestos | ✅ |
| HomeAudioAdapter + SnapcastAdapter inyectados | ✅ |
| DiscDetectionService real inyectado | ✅ |
| SmartMixService.create_mix('balanced_mix') conectado | ✅ |
| RadioBridge: editStation/toggleFavorite/search añadidos | ✅ |
| Tests QML: 349 (+37 desde baseline) | ✅ |

## Para alcanzar 75%

Todas las áreas están en **FUNCTIONAL (65%)**. El próximo salto a **75%** requiere:

1. `python main.py --qml` con display — confirmar play/pause/seek/next físicamente
2. Verificar cover loading con display (CoverBridge funciona offscreen)
3. **Solo eso**: subiría quality_release de 65% a 85%, moviendo el total a ~68%
4. Para llegar a 75% se necesita además **VERIFIED** en otra área (p.ej. library_playback con benchmark < 1s para 50k)

El techo actual es **VERIFIED (85%)** en quality_release + performance benchmark. Sin display, el máximo honesto es 65%.

## Veredicto
**65.0% — APROBADO CON RIESGOS.** Todas las áreas FUNCTIONAL. El bloqueador único es la prueba física de audio con display para alcanzar 75%+.
