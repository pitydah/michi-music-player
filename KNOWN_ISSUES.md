# Known Issues

## Audio
- GStreamerAudioBackend usa playbin básico, no PipelineFactory completo
- MpdBackend no integrado con HybridAudioManager
- EQ, ReplayGain y Spectrum declarados como no soportados en capabilities

## CI
- test_app_starts y test_app_no_duplicate_actions solo se ejecutan en CI
- No hay ejecución de CI verificable para el commit actual

## Tests
- test_spectrum.py saltado (audio/spectrum.py no existe)
- test_large_library.py marcado como perf (no se ejecuta en CI normal)

## Deuda Técnica
- 38 ramas remotas experimentales sin limpiar
- track_action_service.py devuelve {"ok": True} sin verificar DB
- Varios servicios core no tienen tests

## Resueltos en 0.10.0-alpha.1
- 86 tests nuevos (D1)
- Logging en 25 servicios/bridges (D3)
- Estados QML en 16 paginas (D4)
- Ramas reducidas de 21 a 2 (D6)
- 6 tests de integracion E2E (D2)
- Legacy congelado con gate CI (D5)
- 2 benchmarks de rendimiento (D9)
- Errores tipados para sync, home_audio, assistant (D11)
- Ventana movible, fullscreen, maximizar, persistencia (D13)
- Notificaciones con limite, timestamps, agrupacion (D14)
- Modo claro, fontScale, transiciones, tooltips, skeletons (D15)
