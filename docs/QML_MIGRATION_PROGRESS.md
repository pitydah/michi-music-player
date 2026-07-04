# QML Migration Progress

**Date:** 2026-07-04
**Branch:** qml-functional-closure-release-readiness

## Overall: 65.0% (+18.2pp desde baseline 46.8%)

| Area | Weight | Antes | Después | Estado | Evidencia |
|---|---:|---:|---:|---|---|
| Shell/navegación | 10% | 65% | 65% | FUNCTIONAL | NavigationBridge, route_registry, 25 rutas |
| Library/playback | 25% | 65% | 65% | FUNCTIONAL | LibraryBridge con DB real, PlaybackBridge, NowPlaying |
| Workflows core | 20% | 40% | 65% | FUNCTIONAL | Mix con tabla favorites real, Lyrics async+LRU+LRCLIB, Radio real |
| Advanced tools | 20% | 40% | 65% | FUNCTIONAL | EQ dict, AudioLab navigateTo, DiscDetectionService real, Tagging |
| Ecosystem/red | 10% | 20% | 65% | FUNCTIONAL | HA+Snapcast adapters, MichiLink real, Devices dict |
| Quality/release | 15% | 40% | 65% | FUNCTIONAL | Benchmark, physical check, 349 tests, CI gate |

## Key Changes (this migration)

| Cambio | Antes | Después |
|--------|-------|---------|
| Controladores HA/Snapcast | No existían | HomeAudioAdapter + SnapcastAdapter inyectados |
| Disc Lab | streaming/disc_service.py no existe | DiscDetectionService real de ui/audio_lab/ |
| SmartMix daily mix | .get_recommendations() inexistente | .create_mix(strategy='balanced_mix') |
| RadioBridge | Sólo add/delete/play | +editStation, +toggleFavorite, +search |
| Biblioteca benchmark | No existía | scripts/qml_library_benchmark.py + reporte |
| Audio físico check | No existía | scripts/qml_physical_audio_check.py + reporte |
| Tests QML | 312 → 329 → 337 → 342 → 349 | 349 tests (+37) |
| CI gate | No existía | scripts/qml_ci_gate.py, 11/11 pasos |

## Faltante para 75%

| Área | Peso | Actual | Objetivo | Δ | Lo que falta |
|---|---:|---:|---:|---:|---|
| Shell/library | 35% | 65% | 65% | 0 | — |
| Workflows core | 20% | 65% | 85% | +20 | RadioBridge: retry, codec real. Mix: explainCurrentMix |
| Advanced tools | 20% | 65% | 85% | +20 | DiscLab: ripping real. Metadata: smart tagging batch |
| Ecosystem | 10% | 65% | 85% | +20 | Conexión HA real validada, Snapcast runtime |
| Quality | 15% | 65% | 85% | +20 | Prueba física display, accessibility docs |

**Total ponderado faltante:** ~10pp → se necesitan ~20 puntos adicionales en al menos 3 áreas para alcanzar 75%.

## Veredicto
**APROBADO CON RIESGOS** — 65.0% de paridad funcional. Todas las áreas en FUNCTIONAL. Faltan verificaciones runtime (display) para alcanzar VERIFIED y superar 75%.
