# Release Notes — Michi Music Player v0.2.0-alpha.1

**Fecha:** 2026-07-01  
**Versión:** 0.2.0-alpha.1 — Pre-beta técnica avanzada  
**UI estable:** QtWidgets (`python main.py`)  
**UI experimental:** QML (`python main.py --qml`)

## Resumen

Michi Music Player es un reproductor audiófilo para Linux/KDE Plasma con motor de audio híbrido GStreamer + MPD, biblioteca SQLite/FTS5, streaming Subsonic, sincronización Android y ecosistema multiroom.

## Novedades desde 0.1.x

### Biblioteca canónica
- Estado canónico con `LibrarySection`, `LibraryViewMode`, `LibraryState`
- Identidad de tracks estable (`TrackIdentityService` — 6 niveles de prioridad)
- `MediaRecordBuilder` para construcción unificada de registros DB
- `LibraryMutationService` para operaciones add/remove/update
- `LibrarySearchService` — búsqueda unificada en 5 secciones
- `LibraryOrganizeService` — preview + validación + rollback
- `LibraryHealthService` — health summary con score

### Audio
- Hybrid Audio Engine: GStreamer + MPD backends
- 9 perfiles de audio
- EQ gráfico 31-bandas + paramétrico
- ReplayGain avanzado
- Bit-perfect monitor
- Gapless + crossfade

### Ecosistema
- Michi HTTP API (REST, puerto 8124)
- mDNS advertiser
- Sync Manager para Android
- Snapcast multiroom
- Home Assistant integración

### UI
- QML experimental con 16+ bridges
- NowPlaying bar con calidad, formato, backend, perfil, salida
- Playlists hub con herramientas de curaduría
- Audio Lab con 12 módulos clasificados
- CoverFlow 3D
- 40+ atajos de teclado

### Estabilización
- Post-QML stabilization audit completado
- Demo data eliminado de todos los bridges
- DB path unificada via `core.paths`
- Versión unificada via `importlib.metadata`
- AGENTS.md actualizado con QML experimental

## Tests

- ~950 tests en suite completa
- 165 tests QML
- 228+ tests de biblioteca/navegación
- Ruff: 0 errores en código nuevo

## Known Issues

Ver `docs/KNOWN_ISSUES.md`

## Instalación

```bash
pip install .
python main.py
```

## Licencia

GPL-3.0-or-later
