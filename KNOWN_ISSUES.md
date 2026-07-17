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
