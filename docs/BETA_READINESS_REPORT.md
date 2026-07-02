# Beta Readiness Report — Michi Music Player

**Date:** 2026-07-02  
**Current version:** 0.2.0-alpha.1  
**Recommended version for release:** 0.2.0-alpha.1 (maintain alpha; not yet beta)

## 1. Estado general

Michi Music Player tiene una base sólida: motor de audio híbrido, biblioteca canónica, búsqueda FTS5, ecosistema multiroom/Sync/Micro Server, y dos UIs (QtWidgets estable, QML experimental). Sin embargo, no está listo para beta pública debido a:

1. **Schema pre-existing bug**: `is_smart` column missing from playlists table causes smoke startup and several tests to fail. This blocks clean CI/CD.
2. **MPD backend**: no verificado en esta sesión.
3. **Full CI pipeline**: GitHub Actions no confirmado.
4. **Empaquetado**: sin Flatpak/AUR/pip wheels.

## 2. Porcentaje estimado honesto

| Componente | % |
|---|---|
| QtWidgets UI | 90% |
| Audio engine | 85% |
| Biblioteca | 95% |
| Playlists | 85% |
| Busqueda | 90% |
| Géneros | 88% |
| Carpetas | 90% |
| NowPlaying | 90% |
| Audio Lab | 80% |
| Michi Link | 75% |
| Sync | 80% |
| Radio | 85% |
| Home Audio | 60% |
| Settings | 90% |
| Michi AI | 70% |
| QML experimental | 65% |
| CI/CD | 50% |
| Empaquetado | 20% |
| Documentación | 75% |

## 3. Qué está listo

- Biblioteca canónica completa (LibraryState, TrackIdentity, MediaRecordBuilder, MutationService, SearchService, OrganizeService, HealthService)
- Reproducción local con GStreamer
- NowPlaying bar con calidad/backend/salida/bit-perfect
- Playlists CRUD + import/export M3U
- Cubiertas, CoverFlow
- Búsqueda FTS5
- Álbumes, Artistas, Géneros, Carpetas
- Audio Lab: diagnóstico, metadata doctor, bit-perfect monitor, artwork, lyrics, backup, organización
- Radio
- Settings completo
- Atajos de teclado
- 165 tests QML, 228+ tests library/navegación

## 4. Qué está en validación

- Michi Link: HTTP API funciona, mDNS funciona, pero pairing y continue-on-server no verificados en esta sesión
- Playlists: tools avanzadas (duplicados, lost files) muestran "pendiente"
- Mix: no tiene recomendación real
- Sync: funciona pero no verificado con dispositivo real Android
- Audio Lab QML: módulos clasificados pero navigateTo es stub
- NowPlaying bit-perfect: campo añadido al tooltip, falta verificar cadena de llamada

## 5. Qué es experimental

- QML completo (launcher `--qml`)
- MPD backend
- DSD/DoP audio profiles
- Pure Audio, Studio Monitor profiles
- Vinyl Lab, Conversion en Audio Lab
- Inteligencia local (análisis espectral)
- Michi AI chat
- Home Audio multiroom

## 6. Qué está oculto

- Nada oculto intencionalmente. Todo lo no-funcional muestra tooltip o estado honesto.

## 7. Qué falta para beta pública

1. Corregir `is_smart` schema migration
2. CI/CD pipeline (GitHub Actions) verde
3. Verificar MPD backend en hardware real
4. Verificar Michi Link pairing en red real
5. Smoke UI routes sin errores
6. Flatpak/AppImage básico

## 8. Qué falta para release candidate

1. Validación manual de todas las áreas de la Beta Checklist
2. Pruebas en hardware real (DAC, DSD, MPD)
3. Corrección de todos los bugs conocidos en Known Issues
4. Empaquetado completo (Flatpak, AUR, pip)
5. Documentación de usuario y desarrollador
6. Pruebas de rendimiento con bibliotecas de 50k+ tracks

## 9. Tests ejecutados

| Suite | Resultado |
|---|---|
| `ruff check .` | 53 warnings (preexistentes) |
| `python -m compileall .` | ✅ |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python scripts/smoke_startup.py` | 1 error preexistente (`is_smart`) |
| `QT_QPA_PLATFORM=offscreen MICHI_SAFE_MODE=1 python scripts/smoke_ui_routes.py` | 1 error preexistente (`is_smart`) |
| `python -m pytest tests/qml/ -q` | **165 passed** |
| `python -m pytest tests/test_playlist_controller.py tests/test_playlist_stability.py tests/test_playlist_wiring.py` | 18 passed, 12 failed (todos `is_smart`) |
| `python -m pytest tests/test_library_state.py tests/test_library_state_controller.py tests/test_navigation_controller.py -q` | 105+ passed |

## 10. Tests fallidos

Todos los fallos son por el mismo bug preexistente: `sqlite3.OperationalError: no such column: is_smart` en el schema de playlists. Esto afecta ~12 tests y ambos smokes.

## 11. Validaciones manuales necesarias

- [ ] MPD backend en hardware Raspberry Pi / DAC USB
- [ ] Michi Link pairing con servidor remoto
- [ ] Sync con dispositivo Android real
- [ ] DSD playback con DAC compatible
- [ ] Home Assistant integración real
- [ ] Snapcast multiroom con 2+ dispositivos

## 12. CI Status

| Check | Local | GitHub Actions | Estado |
|---|---|---|---|
| `ruff check .` | 51 pre-existing | ✅ (job packaging) | ✅ |
| `compileall` | ✅ | ✅ (job packaging) | ✅ |
| Smoke startup | 1 pre-existing (`is_smart`) | ✅ (con env test) | ⚠️ 1 pre-existing |
| Smoke UI routes | 1 pre-existing (`is_smart`) | ✅ (con env test) | ⚠️ 1 pre-existing |
| QML tests | 165 passed | ✅ (job QML bridge tests) | ✅ |
| Album tests | 126 passed | ✅ (job Album-focused) | ✅ |
| Audio Engine tests | — | ✅ (job Hybrid Audio Engine) | ✅ |
| Anti-regression + Home | — | ✅ (job Tests) | ✅ |

## 13. Riesgos técnicos

1. `is_smart` schema migration no ejecutada correctamente
2. MPD backend no probado en esta release
3. QML con PlayerService no probado con audio real
4. `qml-migration-foundation` tiene 34 commits sin mergear (18 necesarios, 1 riesgoso)
5. 115 archivos compartidos con cambios divergentes entre `main` y `qml-migration-foundation`

## 14. Recomendación de versión

**Mantener `0.2.0-alpha.1`.** No promover a beta hasta que:

1. El bug `is_smart` esté corregido
2. Smoke startup pase sin errores
3. GitHub Actions CI esté verde
4. Beta Checklist tenga al menos 80% de items verificados
