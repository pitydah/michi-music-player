# Known Issues

## Audio
- EngineBackendAdapter creado pero no conectado como backend productivo por defecto
- MpdBackend no integrado con HybridAudioManager
- EQ, ReplayGain y Spectrum declarados como no soportados en capabilities

## Tests
- 106 tests legacy congelados como .py.skip (QtWidgets eliminado sin reemplazo QML)
- test_spectrum.py saltado (audio/spectrum.py no existe)
- test_large_library.py marcado como perf (no se ejecuta en CI normal)
- test_eq_advanced.py.skip (modulo audio/eq_advanced.py no existe)

## CI
- Coverage gate en 40% minimo pero no verificado localmente
- No hay ejecucion de CI verificable para el commit actual

## Deuda Tecnica
- 42 controladores legacy en legacy_widgets/ sin migrar a AppContext
- legacy_widgets/ui/window.py con 1455 lineas (objeto-dios)
- 3 ramas remotas experimentales sin limpiar
- track_action_service.py devuelve {"ok": True} sin verificar DB
- Varios servicios core no tienen tests
- Components de estado legacy (EmptyState, ErrorState, etc.) no unificados con Michi*

## Resueltos en 0.10.0-alpha.1
- 86 tests nuevos (D1) — logging en 25 servicios (D3) — estados QML 16 paginas (D4)
- Ramas reducidas de 21 a 3 (D6) — 6 tests E2E (D2) — Legacy congelado (D5)
- 2 benchmarks rendimiento (D9) — Errores tipados sync/home_audio/assistant (D11)
- Ventana movible, fullscreen, persistencia (D13) — Notificaciones (D14) — Tema (D15)
- Fase 0: Settings QtCore, mute, current_path, smoke test robusto, coverage gate
- Fase 1: EngineBackendAdapter, PlayerService->engine.play()
- Fase 2: 27 collection errors->0, EQ tests restaurados
- Fase 3: ActionRegistry contractual (service_name, method_name, capability)
- Fase 4: Subsonic mock, playlist hub, FTS5 fuzzer, PathView tests
- Fase 5: Snapcast lifecycle, Radio Browser, Transmit integration
- Fase 6: AutoEQ, EQ convert, DoP, AlbumInfo cache, ArtistInfo, Audio similarity
- Fase 7: Audio capture mock, Shazam, AudD, AcoustID, Matcher 4-tier, Detection
- Fase 8: HA client, Flatpak manifest, Sync mDNS, Receiver Wizard, Output profiles
- Fase 9: Michi AI propio (reemplaza Ollama)
- UX-0 a UX-13: auditoria completa, design system, componentes, sidebar con grupos,
  nowplaying reestructurado, inicio premium, library toolbar, reducedMotion global
- ~320 tests nuevos, 0 QML compilation errors
