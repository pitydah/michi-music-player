# Release Notes — Michi Music Player

## 0.10.0-alpha.1 (2026-07-17)

### Resumen
Estabilización post-merge UI/UX. CI funcional, AudioBackend contract tipado,
migraciones atómicas, ServiceContainer sin doble inicio, +30 tests nuevos.

### Cambios principales
- CI con 4 jobs (lint, test, qml-compile, build) y matrix Python 3.11/3.12
- AudioBackend: get_snapshot() devuelve PlaybackSnapshot tipado
- AudioBackend: play_next/play_prev reproducen realmente
- AudioBackend: pause/resume actualizan _playing
- AudioBackend: conversión file:// automática
- ServiceContainer: sin doble inicio (register + start)
- Migraciones: atómicas (BEGIN/COMMIT/ROLLBACK)
- 94 errores QML corregidos (DropShadow, DoubleValidator, etc.)
- 10 servicios core con tests
- 10 archivos audio/ con type hints y docstrings
