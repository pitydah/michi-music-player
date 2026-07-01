# Michi Hybrid Audio Engine — Final Report

## Estado final

| Área | Estado | Comentario |
|------|--------|-----------|
| PlayerService híbrido | 95% | Fachada real con HybridAudioManager, backend_changed signal, bloqueo DSP |
| MPD Client | 95% | Greeting OK MPD, ensure_connected, MpdError importado, timeout 2s |
| MpdBackend | 90% | set_volume bloqueado, enqueue_next con addid/moveid, next/prev por status |
| MpdServiceManager | 90% | Sin pkill, --no-daemon, get_status completo, solo mata proceso propio |
| MpdConfigBuilder | 85% | Crea directorios, pid_file opcional, dop condicional |
| MpdPathMapper | 90% | commonpath, is_inside, sin falsos prefijos |
| BitperfectVerifier | 90% | No verified sin matching device, compara canales, detecta volumen digital |
| HybridAudioManager | 85% | switch_to preserva cola, fallback_to_default público |
| Audio Lab monitor | 85% | Ruta navegable, card en AudioLabPage, handler en window.py |
| MPRIS | 85% | Next/Prev/OpenUri/Pause/Play/Stop via player_api, Seek/SetPosition fix |
| CrashReporter | 85% | faulthandler, sanitiza env, señales nativas seguras |
| Tests | 90% | 233 tests, cobertura de bugs corregidos |
| Documentación | 85% | 6 docs, final report, diagnostic script |
| CI | 50% | Workflow existente, falta integrar tests híbridos |

**Michi Hybrid Audio Engine: ~87%**

## Bugs críticos corregidos

1. **MpdError import** — `MpdError` no estaba importado en `mpd_client.py`, causaba NameError en ping()
2. **MPD greeting** — `connect()` usaba `parse_response()` para el saludo `OK MPD 0.23.x`, no lo reconocía como OK
3. **Parser playlistinfo** — No detectaba entradas nuevas sin blank lines entre canciones
4. **Parser outputs** — Fallaba con outputs sin blank lines
5. **set_volume en MPD** — Declaraba `supports_digital_volume=False` pero ejecutaba `setvol`
6. **enqueue_next** — Usaba `add()` que va al final, no insertaba después de la actual
7. **get_queue** — Llamaba `status()` dentro de cada iteración
8. **play_next/prev** — Usaban `_local_paths` en vez de `status.song`
9. **pkill removal** — `MpdServiceManager.stop()` llamaba `pkill -u USER mpd`
10. **MpdPathMapper** — Usaba `startswith(root)` inseguro
11. **BitperfectVerifier** — No comparaba canales; `_find_matching_device` limitado
12. **Verified falso** — Podía decir verified sin matching device
13. **objectName** — `card.object_name()` en vez de `card.objectName()`
14. **DSPPage** — Riesgo de NameError si no se definían lbl/row
15. **MPRIS SetPosition** — Variable `current_us` no definida si no había engine
16. **Audio Lab route** — BitperfectMonitorPage sin ruta navegable
17. **Timeout** — 5s default para MPD (congelaba UI)
18. **MpdServiceManager** — No usaba `--no-daemon`, status incompleto

## Tests ejecutados

```bash
python -m compileall -q .     # OK
ruff check audio/              # 0 en código nuevo (preexistentes)
QT_QPA_PLATFORM=offscreen python -m pytest \
  tests/test_audio_backend_base.py \
  tests/test_gstreamer_backend.py \
  tests/test_hybrid_audio_manager.py \
  tests/test_audio_settings_schema.py \
  tests/test_audio_settings_migrator.py \
  tests/test_alsa_hw_params.py \
  tests/test_bitperfect_verifier.py \
  tests/test_mpd_protocol.py \
  tests/test_mpd_client_mock.py \
  tests/test_mpd_path_mapper.py \
  tests/test_mpd_backend.py \
  tests/test_mpd_config_builder.py \
  tests/test_mpd_service_manager.py \
  tests/test_mpd_discovery.py \
  tests/test_audio_profile_backend_selection.py \
  tests/test_dsp_state.py \
  tests/test_player_service_hybrid.py \
  tests/test_output_profiles_mpd.py \
  tests/test_bitperfect_monitor_page.py \
  tests/test_mpris_hybrid.py \
  tests/test_hybrid_engine_end_to_end.py \
  -q
# Resultado: 233 passed, 1 warning
```

## Cómo probar manualmente

1. **Perfil Standard**: `audio/profile = standard` → GStreamer con DSP completo
2. **Perfil MPD**: `audio/profile = michi_hifi_mpd` → intenta MPD, fallback a GStreamer si no disponible
3. **Monitor Bit-Perfect**: Navegar a Audio Lab → Monitor Bit-Perfect
4. **MPD local**: DSPPage → botón "Iniciar MPD local" (requiere mpd instalado)
5. **Fallback**: Seleccionar perfil MPD sin MPD instalado → GStreamer automático

## Limitaciones conocidas

- Verified real requiere DAC físico + reproducción activa + lectura de /proc/asound
- DoP requiere DAC compatible + activación explícita en settings
- MPD remoto requiere path mapping correcto
- WASAPI/ASIO documentados para futuro Linux no aplica
- Tests requieren GStreamer runtime (no corre en CI sin dependencias)

## Archivos clave del motor híbrido

| Archivo | Rol |
|---------|-----|
| `audio/player_service.py` | Fachada única UI → HybridAudioManager |
| `audio/backends/hybrid_audio_manager.py` | Selector de backend por perfil |
| `audio/backends/gstreamer_backend.py` | Wrapper GStreamerEngine |
| `audio/backends/mpd_backend.py` | Backend MPD |
| `audio/backends/types.py` | PlaybackSnapshot, AudioDiagnostics, BackendCapabilities |
| `audio/mpd/mpd_client.py` | Cliente TCP MPD |
| `audio/mpd/mpd_protocol.py` | Parser respuestas MPD |
| `audio/diagnostics/bitperfect_verifier.py` | Verificador ALSA hw_params |
| `audio/output_profiles.py` | 13 perfiles (9 GStreamer + 4 MPD) |
| `ui/audio_lab/bitperfect_monitor_page.py` | Monitor UI |
| `adapters/mpris.py` | MPRIS con soporte híbrido |
