# Changelog

## [0.10.0-alpha.1] - 2026-07-17

### Added
- Sistema de diseno centralizado (MichiTheme, 20 componentes base)
- Accesibilidad granular (734 Accessible.role, 554 activeFocusOnTab)
- Responsive design (breakpoints compact/medium/wide/ultrawide)
- Focus trap en MichiDialog
- Gates CI diferenciales con fingerprints
- ActionRegistry con validacion de duplicados y metodos
- ObservableServiceContainer con service_state_changed signal
- Migraciones formales versionadas (5 migraciones sobre tablas reales)
- GStreamerAudioBackend con toggle/get_snapshot/get_diagnostics/capabilities
- Volumen normalizado 0-100
- Sync transport (UMS)
- Micro Server service (Rust client HTTP)
- Home Audio service (Snapcast JSON-RPC + Home Assistant REST)
- Transporte UMS completo
- CI canonico con 4 jobs (lint, test, qml-compile, build)
- Wheel verificable con todos los paquetes
- STATUS.generated.md automatico
- scripts/ci_canonical.sh, build_wheel.sh, smoke_test.sh

### Fixed
- 5 action IDs duplicados en bootstrap (bloqueaban arranque)
- PlayerService creaba backend GStreamer duplicado
- Volumen usaba 0.0-1.0 en vez de 0-100
- _handler() silenciaba excepciones
- validate_all() no verificaba servicios reales
- pyproject.toml tenia include restrictivo que excluia paquetes core
- 94 errores de compilacion QML (DropShadow, DoubleValidator, etc.)
- Migrations.py usaba tablas paralelas (songs) en vez de las reales (media_items)
- HTTP API devolvia 200 OK sin verificar bridge
- 51 ramas experimentales sin merge eliminadas

### Changed
- GStreamerEngine ahora delega completamente en GStreamerAudioBackend
- Schema.run_migrations() integra formal_migrate()
- ApplicationBootstrap registra servicios OPTIONAL para sync/micro/home
