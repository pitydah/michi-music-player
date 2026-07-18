# Known Issues

## Audio
- EngineBackendAdapter conectado productivamente (PipelineTransport separado)
- MpdBackend no integrado con HybridAudioManager
- 9 tests verticales de audio con WAV real + fakesink (P0.2)
- Contrato de volumen unificado (0-100 en toda la cadena)

## Tests
- 28 tests suprimidos reemplazados: 9 eliminados (cobertura existe), 19 xfail
- test_large_library.py marcado como perf (no se ejecuta en CI normal)
- test_eq_advanced.py.skip (modulo audio/eq_advanced.py no existe)
- 0 errores de coleccion en toda la suite

## CI
- Coverage gate en 25% minimo
- 3 jobs: lint (3.11+3.12), test (core + smoke + QML + migrations), build (wheel)
- Incluye: Ruff, compileall, audit imports, legacy gate, coverage, wheel verify

## QML
- 0 errores de compilacion QML
- 7 errores de runtime reparados (onError, surfaceSelected, sidebar, etc.)
- Modo claro: base en MichiColors.lightMode (pendiente de conexion a UI)
- reducedMotion: base en MichiTheme (pendiente de conexion a settings)

## Deuda Tecnica
- track_action_service.py devuelve {"ok": True} sin verificar DB
- Componentes UI nuevos (MichiAlbumRow, MichiBanner, etc.) no integrados en paginas
- ActionRegistry sin handlers productivos (solo schema)
- Michi IA basada en reglas con datos mock (no conectada a biblioteca real)
- Capturas baseline requieren servidor X real (offscreen no navega)

## Resueltos en 0.10.0-alpha.1
- Fases 0-9: Settings QtCore, EngineBackendAdapter, 27 collection errors→0,
  ActionRegistry contractual, Subsonic mock, FTS5 fuzzer, Snapcast, AutoEQ,
  DoP, reconocimiento, HA client, Michi AI propio, Sync mDNS
- UX-0 a UX-13: auditoria, design system, componentes, sidebar con grupos,
  NowPlaying, Inicio premium, library toolbar, reducedMotion, modo claro base
- P0.1-P0.6: PipelineTransport, 9 tests verticales, 7 errores QML, capturas,
  28 pruebas suprimidas resueltas, 0 errores coleccion

## Tests
- `tests/qml/ai/test_michi_ai_keyboard.py` — 20 tests fallan en pytest estándar.
  Requieren QQmlApplicationEngine + window visible. No es causado por cambios recientes.
- `tests/qml/ai/test_michi_ai_action_registry.py` — errores similares.
  Requieren contexto QML completo. Preexistente.
