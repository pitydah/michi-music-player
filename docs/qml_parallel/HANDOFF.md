# HANDOFF — QML Runtime Convergence

## Estado actual (Julio 2026)

- Rama: `qml-runtime-convergence`
- Score V8: 83% (130 archivos con marcadores qml_module)
- Bridges: 45 puentes registrados en BridgeFactory
- Context properties: 45 bindings en context_bindings.py
- Rutas: 52 en route_registry.py
- Modelos QML: 10 en ui_qml/models/

## Módulos activos (config/qml_modules.yaml)

| Módulo | Peso | Estado |
|--------|------|--------|
| workflows | 25 | En desarrollo (workflow vertical + interacción real) |
| workflows_interaction_real | 20 | Real QML interaction tests |
| evidence | 15 | Evidencia V9 |
| library | 10 | Funcional (tabs Songs/Albums) |
| playback | 10 | Funcional (NowPlaying, Queue) |
| navigation | 10 | Funcional (PageStack, route registry) |
| settings | 5 | Placeholders |
| devices | 5 | Funcional (Device list + detail) |

## Tareas pendientes

- [ ] HU: Runtime quality gate
- [ ] HV: Tests multiplataforma (Linux + Windows)
- [ ] HW: Integration audit
- [ ] Completar settings pages (7 placeholders)
- [ ] Playlists backend (rama separada)
