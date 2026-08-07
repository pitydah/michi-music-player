# P0 Stabilization — Completion Report

Informe de cierre de la estabilización P0 del runtime: 11 falsos éxitos del baseline
corregidos, 11 fases completadas, 12 commits sobre la rama
`agent/runtime-refactor-p0-stabilization` (baseline `66245d11` → head `6ae14b89`).

## 1. Resumen ejecutivo

| Métrica | Baseline (`66245d11`) | Head (`6ae14b89`) | Delta |
|---|---|---|---|
| Suite no-QML | 4134 passed / 3 failed / 96 skipped / 13 errors | **4348 passed / 3 failed / 96 skipped / 13 errors** | +214 passed, fallos idénticos (ambientales, reproducidos base=head) |
| `tests/architecture` + `tests/integration` | 358 passed | **563 passed** | +205 |
| Auditores de runtime | 5 (exit 0) | **7 (exit 0, 7/7)** | +2 nuevos, 5 ampliados (A–H) |
| Ruff | 0 | **0** | — |
| compileall | limpio | **limpio** | — |
| Falsos éxitos conocidos | 11 | **0** | 11 corregidos y gateados |

Los 3 fallos de la suite no-QML son los mismos del baseline (2 perf FTS 10k/50k que
exigen base real indexada + 1 flaky `test_player_service_apply_profile` que pasa en
aislamiento). Los 13 errors son de colección en `tests/perf` (fixture `_qt_app`
ausente) — idénticos a baseline, fuera del alcance canónico P0.

## 2. Cierre por problema (11 falsos éxitos + mandatos de fase)

### 2.1 Falsos éxitos del baseline

| # | Problema | Causa raíz | Archivo anterior → corregido | Cambio realizado | Test vertical | Validación | Resultado | Deuda restante |
|---|---|---|---|---|---|---|---|---|
| 1 | `cancel_all()` global desde Mix cancela jobs ajenos | Sin scope de cancelación por dominio | `ui_qml_bridge/mix_bridge.py:310` → `mix_service` + `DurableJobService.cancel_owner` | Cancelación scoped; mix cancela solo su job id | `tests/integration/jobs/test_cancel_mix_does_not_cancel_scan.py` | suite + auditor F | 0 cancel_all no administrativo | — |
| 2 | Dispatch de estrategias y estado en el BRIDGE (duplicado del servicio) | Lógica de negocio en capa de presentación | `ui_qml_bridge/mix_bridge.py:369-439` → adapter fino + `mix_generate` durable | Estados 1:1 a QML; `save_mix_as_playlist` con `playlist_id` real; `PARTIAL_SUCCESS` | `tests/integration/test_mix_generation_job_vertical.py` (13 tests) | suite + auditor B/E | 0 construcción en bridges | Skin QML renderiza estados parciales |
| 3 | `confirmed=True` autodeclarado con `source` | Confianza en string, no en token | `core/metadata_editor_service.py:251` → flujo `ConfirmationToken` | ADR-003: token por command/target/fields hash; errores tipados; audit JSONL | `tests/integration/test_metadata_token_security.py` | suite + gate `test_no_self_declared_confirmation` | `confirmed=True` rechazado | — |
| 4 | `source="doctor"` autodeclarado | Ídem, en doctor | `core/library_doctor_service.py:146` → token emitido | Reparación con token + readback | Ídem + `tests/integration/test_metadata_apply_and_undo_vertical.py` | gate | doctor sin token falla | — |
| 5 | `source="ui"` autodeclarado | Ídem, en bridge | `ui_qml_bridge/metadata_bridge.py:280` → token del ConfirmationService | `effective_fields = proposal ∩ selected` | `test_selected_fields_respected_end_to_end` | gate | selección respetada | — |
| 6 | Jobs RUNNING→INTERRUPTED ausentes de memoria; QUEUED nunca reprocesados (24+ zombies) | Recovery sin visibilidad ni auto-resume | `core/jobs/job_service.py:146-151` → `jobs/` v2 | `RUNNING→INTERRUPTED` visible+retryable; `QUEUED` auto-resume tras registrar handlers; `HANDLER_UNAVAILABLE` persistido | `tests/integration/jobs/test_job_restart_running_visible.py`, `test_job_restart_queued_resume.py`, `test_job_persistence_restart.py` | suite + auditor D | 0 zombies | — |
| 7 | `retryJob` sin iniciar vs `NotificationActionService.retry` con semántica distinta | Dos caminos de retry | `job_bridge.py:184` + `notification_action_service.py:90` → `job_service.retry_job` único | Retry unificado que re-ejecuta payload original | `tests/integration/jobs/test_retry_semantics_unified.py`, `tests/integration/test_notification_retry_real_job.py` | suite | 1 método, 1 semántica | — |
| 8 | `threading.Lock` + dict `_jobs` paralelo; `hash(mount_path)` como serial | Sistema de jobs duplicado + identidad inestable | `core/device_sync_service.py` → facade + `core/device_sync/` pipeline | Jobs durables `device_sync`/`device_transfer` owner `device:{id}`; identidad `usb_serial→mtp→uuid→vendor→fingerprint→fallback`; migración 10 | `tests/integration/test_device_sync_vertical.py` (incl. `test_checksum_mismatch`) | suite + gate `test_device_sync_single_authority` | 0 jobs internos | — |
| 9 | Pairing HMAC 6 dígitos sin prueba de posesión de clave | Código ≠ clave privada | `core/mobile_sync_service.py:314-326` → challenge-response Ed25519 | ADR-007: nonce single-use; fingerprint server-side; legacy loopback+TTL 300s+audit; `PERSISTENCE_FAILED`; `DeviceRegistry` inyectado | `tests/integration/test_mobile_pairing_signature.py` (5+), `test_mobile_pairing_persistence.py`, `test_mobile_trust_revocation.py` | suite + gate `test_mobile_pairing_no_unverified_fingerprint` | firma real verificada | App móvil debe soportar firma (loopback para legacy) |
| 10 | `BUILTIN_DEPENDENCIES` + listas históricas = segundo inventario y segundo grafo | Doble fuente de verdad del ciclo de vida | `core/service_container.py:47,128,146,155,159` → manifest única | ADR-001: lifecycle solo desde `SERVICE_MANIFEST`; `alias_of` (2 alias); `ManifestCycleError` | `tests/architecture/test_single_graph_manifest.py`, `test_manifest_cycle_detected.py`, `test_alias_single_start_shutdown.py` | suite + auditor D | 0 listas productivas | — |
| 11 | Ciclo settings_service ↔ settings_coordinator | Dependencia circular sin detección en import | `core/settings_service.py` ↔ `settings_coordinator` → autoridad única | Coordinador eliminado; ciclo roto por diseño; `ManifestCycleError` como red de seguridad | `tests/architecture/test_settings_cycle_resolved.py` | suite | boot sin ciclo | — |

### 2.2 Mandatos de fase adicionales (F4, F5, F9, F10, F11)

| Problema | Causa raíz | Cambio realizado | Test vertical | Validación | Resultado | Deuda restante |
|---|---|---|---|---|---|---|
| F4 — Desfavoritar álbum destruía favoritos directos de tracks; bulk silenciaba inexistentes; `ok=True` sin readback | Origen de favorito no modelado; bulk sin desglose; identidad por path | Origen `direct/inherited_album/inherited_artist/inherited_genre/migrated_legacy` + `parent_entity` (migración 9); bulk `applied/already_set/not_found/failed` atómico; `READBACK_MISMATCH`; identidad `track_uid`; fix migración 7 `DEFAULT strftime` | `tests/integration/test_favorites_integrity.py` (`test_direct_favorite_inside_favorited_album`, `test_bulk_mixed_ids`) | suite + gate `test_favorites_single_identity` | PASS | — |
| F5 — Radio reportaba éxito sin backend en `PLAYING`; registraba `play` en `CONNECTING` | Sin máquina de estados ni readback en el adapter | `RadioPlaybackAdapter` sobre `PlayerService`; estados IDLE→FAILED; `accepted=True` solo en `PLAYING`; historial kinds `attempt/play/failure/reconnect/stopped`; sin fallback `return True` | `tests/integration/test_radio_playback_vertical.py` (`test_backend_absent`, `test_no_play_history_on_connecting`) | suite + gate `test_radio_no_success_without_playback` | PASS | — |
| F9 — `MichiAIEngine` 415 líneas con pipeline paralela; runtime fuera de composición; capabilities sin health real | Dos pipelines; service locator en bridge | ADR-006: `AssistantRuntime` única (10 interfaces); engine → facade 50 líneas; `CapabilityResolver` con `health_provider`; `assistant_runtime` registrado + `michi_ai_service` dependency | `tests/architecture/test_assistant_runtime_single.py`, `tests/integration/test_assistant_runtime_vertical.py` (`test_runtime_registered_full`) | suite + auditor D | PASS | Facade puede crecer si no se migra lógica nueva |
| F10 — Múltiples event buses / `DeviceRegistry` paralelos; Recognition compuesto sin ports; Home Assistant con red en composición | Duplicación de autoridades de ecosistema | `LyricEventBus`/radio EventBus = wrappers finos sobre `event_bus` canónico; `DeviceRegistry` único compartido; Home Assistant sin red en composición; `FileManagerService` port; Recognition con `ProviderManager`/`AudioCapture`/`DetectionService`; privados→ports | `tests/architecture/test_single_event_bus_and_registry.py`, `test_lyrics_single_authority.py`, `test_no_bridge_constructs_playlist_service.py` | suite + auditor B/E | PASS | — |
| F11 — Sin verificación semántica del runtime | Falsos éxitos detectables solo por AST | 7 auditores A–H (A falsos éxitos 0/598, 23 allowlist, 16 QUERY; B construcción fuera composición 0/52 doc; C identidad 2 alias ✓; D locator 0/7 probes; E estado paralelo 0/5; F cancel_all 0; G subprocess 0/633, 2 en port, 16 adaptadores; H nominales 165 warn-only) | gates en `tests/architecture/` (56 archivos) | `tools/audit_*.py` 7/7 exit 0 | PASS | 165 tests nominales (deuda H) |

## 3. Archivos modificados por fase

| Fase | Commit | Archivos productivos principales | Tests |
|---|---|---|---|
| F1 Container+Settings | `670d0857` | `core/service_container.py`, `core/service_manifest.py`, `core/composition/infrastructure.py` | 7 nuevos (graph manifest, cycle, alias, settings cycle, orphan, required, registered) |
| F2 Jobs | `1600f1f5` | `core/jobs/` (service, handlers, ports), `job_bridge.py`, `notification_action_service.py`, `device_sync` ports | 12+ en `tests/integration/jobs/` (restart, retry, handler_unavailable, cancel scoped) |
| F3 Metadata | `68a7aecf` | `core/confirmation_service.py` (token), `metadata_editor_service.py`, `library_doctor_service.py`, `metadata_bridge.py`, auditoría JSONL, backup 7d | `test_metadata_token_security.py`, `test_metadata_apply_and_undo_vertical.py` |
| F4 Favorites | `0f5130ed` | `core/favorites` (origin, parent_entity), migración DB 9, `favorites_service.py` | `test_favorites_integrity.py` |
| F5 Radio | `e2cbb204` | `audio/radio_playback_adapter.py`, historial kinds, máquina de estados | `test_radio_playback_vertical.py` |
| F6 Mix | `5cf339fd` | `ui_qml_bridge/mix_bridge.py` (adapter fino), `core/mix_service.py`, `core/jobs/handlers.py` (mix_generate), `core/mix/models.py` | `test_mix_generation_job_vertical.py` (13), `test_mix_no_matches_status.py` + gates |
| F7 Pairing | `c171400f` | `core/mobile_sync_service.py` (Ed25519, challenge-response, legacy TTL), `DeviceRegistry` inyectado, listener subclass | `test_mobile_pairing_signature.py` + persistence + revocation |
| F8 Device Sync | `aa0b9dca` | `core/device_sync/` (models/identity/discovery/profile_resolver/planning/transcode_planning/transfer/verification/history), facade `device_sync_service.py`, migración 10 | `test_device_sync_vertical.py` + gates |
| F9 AI | `6fbf2f86` | `core/assistant/` runtime (10 interfaces), `MichiAIEngine` → 50 líneas, `CapabilityResolver` + `health_provider`, manifest | `test_assistant_runtime_vertical.py`, `test_assistant_runtime_single.py` |
| F10 Ecosistema | `7388f068` | buses wrappers (`lyrics`, radio), `DeviceRegistry` único, `FileManagerService` port, Recognition ports, Home Assistant sin red | gates de autoridad única (8 dominios) |
| F11 Auditores | `6ae14b89` | `tools/audit_*` (5 ampliados, 2 nuevos: process_isolation, nominal_tests) | 56 gates en `tests/architecture/` |

## 4. Servicios removidos / deprecados / integrados

- **Removidos**: `BUILTIN_DEPENDENCIES` y listas históricas de `service_container.py`;
  `settings_coordinator`; `_jobs`/`threading.Lock` de `device_sync_service`; dispatch de
  estrategias en `mix_bridge`; lógica de planificación de `MichiAIEngine`; `cancel_all`
  no administrativo.
- **Deprecados (deshabilitados explícitamente)**: confirmación autodeclarada por
  `source` → `LEGACY_OPERATION_DISABLED`; pairing code-only fuera de loopback (TTL 300s +
  audit); métodos legacy de metadata sin token.
- **Integrados en autoridad única**: `DeviceSyncService` → facade sobre pipeline
  `core/device_sync/`; `MixBridge` → adapter fino sobre `mix_generate` durable;
  `MichiAIEngine` → facade 50 líneas sobre `AssistantRuntime`; `LyricEventBus`/radio
  EventBus → wrappers de `event_bus`; `DeviceRegistry` único compartido; retry →
  `job_service.retry_job`; alias `connection_factory→database`,
  `library_filtered_query_service→library_query_service`.

## 5. Tests ejecutados

```bash
# Suite canónica P0 (no-QML)
python -m pytest tests/ --ignore=tests/qml --ignore=tests/test_large_library.py -q
#   → 4348 passed, 3 failed (ambientales idénticos a baseline), 96 skipped, 13 errors (perf, idénticos a baseline)

# Subsuelo arquitectura + integración
python -m pytest tests/architecture tests/integration -q
#   → 563 passed

# Auditores (7/7 exit 0)
python tools/audit_runtime_reachability.py && python tools/audit_service_duplicates.py \
  && python tools/audit_bridge_responsibilities.py && python tools/audit_ai_tool_mappings.py \
  && python tools/audit_capability_truthfulness.py && python tools/audit_process_isolation.py \
  && python tools/audit_nominal_tests.py

# Calidad estática
ruff check . --output-format concise      # 0
python -m compileall -q -x '.venv/|\.tmpl\.' .   # limpio
```

Comparación base=head de fallos: los 3 failed y los 13 errors de head son **los mismos
tests y los mismos motivos** documentados en `P0_STABILIZATION_BASELINE.md` secciones 3
(ambientales) — la suite no regresiona.

## 6. Deuda restante (honesta)

| Deuda | Detalle | Severidad |
|---|---|---|
| ~~Import de playlists no atómico~~ | **RESUELTO (D1)**: import atómico con políticas explícitas + `cancel_import` real sobre jobs durables (`8196efcd`, `tests/test_playlist_atomic_import.py`) | — |
| ~~`ImportStore` in-memory~~ | **RESUELTO (D3a)**: ledger SQLite de sesiones commiteadas (`michi_link_imports.sqlite`), restart-safe; `tests/integration/test_michi_link_import_store_persistent.py` | — |
| Dominio de búsqueda RADIO | `search_domains` no incluye `radio`; gate `test_search_domains_not_in_text.py` lo fija como deuda consciente | Baja |
| 38 servicios `UNTESTED_VERTICAL` | `REACHABILITY_REPORT.md`: tienen consumers/tests unit pero sin archivo vertical en `tests/integration`/`tests/architecture` | Media |
| ~~`LinkDiagnosticsService` construido en runtime~~ | **RESUELTO (D3b)**: dependencias inyectadas desde composición; sin `ServiceClass(...)` en métodos; `tests/architecture/test_link_diagnostics_no_runtime_construction.py` | — |
| `DetectionService` fallback | Recognition: fallback de proveedor sin red aún por end-to-end | Baja |
| ~~History stubs~~ | **RESUELTO (D4)**: `set_history_enabled`/`set_history_limit` con efecto real persistido (flag gatea `record_play`, límite caps fetch + prune); `tests/test_history_service_stubs.py` | — |
| `audio_lab` ProcessController | Migración a jobs durables iniciada (port) pero ProcessController legacy coexiste | Media |
| `SyncQueue` legacy | `core/sync/sync_queue_impl.py` mantiene cola paralela al runtime de jobs (no usada por device_sync nuevo) | Baja |
| 165 tests nominales | `audit_nominal_tests.py` (F11-H): patrones débiles (fixed-count, text-existence) — warn-only, 0 en CI | Baja |
| `test_player_engine` 6 fallos standalone | 6 fallos pre-existentes en aislamiento, reproducidos también en baseline (no regresión P0) | Baja |
| QML | Suite `tests/qml` con fallos pre-existentes idénticos a baseline; skin no es el objetivo P0 | Baja |

## 7. Riesgos pendientes

1. **Auto-resume de QUEUED en boot**: si un handler registra tarde, `HANDLER_UNAVAILABLE`
   se persiste — el skin QML aún no renderiza este estado con claridad.
2. **App móvil sin soporte Ed25519**: pairing legacy limitado a loopback hasta que el
   cliente móvil firme; despliegue coordinado requerido.
3. **Facade creep**: `MichiAIEngine` y `DeviceSyncService` pueden volver a acumular
   lógica sin gates que midan tamaño — los gates existentes solo detectan autoridad
   duplicada, no crecimiento.
4. **Allowlists de auditores (23 falsos éxitos + 52 doc + 5 estado paralelo + 16 QUERY)**:
   crecen solo con razón documentada; sin revisión periódica pueden fosilizarse.
5. **38 UNTESTED_VERTICAL** sin plan de cobertura por dominio → riesgo de regresión
   silenciosa en servicios no cubiertos verticalmente.
6. **3 fallos ambientales + 13 errors perf**: la CI canónica debe excluirlos
   explícitamente o la señal de regresión se pierde.

## 8. Próximos pasos

1. Revisar y fusionar el PR de la rama `agent/runtime-refactor-p0-stabilization`
   (criterio 39: no fusionar antes de cerrar P0 — pendiente de review).
2. Plan de cobertura vertical para los 38 servicios `UNTESTED_VERTICAL`.
3. ~~Migrar `playlist import` y `ImportStore` al runtime durable (ADR-004) con
   cancelación scoped~~ — **cerrado**: D1 (import atómico + cancel real) y D3a
   (ledger restart-safe) entregados.
4. Eliminar o migrar `SyncQueue` legacy y los stubs de history
   (`set_history_enabled/limit` con efecto real) — **stubs cerrado en D4**;
   queda `SyncQueue` legacy.
5. Adoptar la suite `tests/qml` verde como gate (hoy: fallos pre-existentes iguales a
   baseline; fuera de P0).
6. Revisión periódica de allowlists de auditores (rotación semestral sugerida).

## 9. Referencias

- Baseline: `docs/audits/P0_STABILIZATION_BASELINE.md` (SHA `66245d11`)
- ADRs: `docs/adr/ADR-001..007` (series P0; los ADR con nombre `ADR-*-*.md` previos al
  wave P0 quedan como registros históricos)
- Matriz de aceptación: `docs/audits/P0_STABILIZATION_ACCEPTANCE_MATRIX.md`
- Reports previos: `docs/audits/RUNTIME_REFACTOR_COMPLETION_REPORT.md`,
  `docs/audits/REACHABILITY_REPORT.md`, `docs/audits/RUNTIME_SERVICE_AUDIT_CURRENT.md`

---

## Addendum — CI estabilización (PR #187, post-revisión)

Tras la revisión del diff (3 MEDIUM cerrados) y la batalla de CI, se corrigieron bugs reales que el entorno CI exponía (todos pre-existentes de main, activados por GStreamer real / Python 3.12 / session bus):

| Fix | Commit | Bug real corregido |
|-----|--------|--------------------|
| MPRIS tolerante | `4c0775d3` | KeyError "bus name taken" rompía el boot si otro handler existía en el session bus (CI) |
| mobile_sync listener lazy | `4c0775d3` | Listener abierto en boot → LISTENER_START_FAILED en CI; ahora arranca bajo demanda vía start_pairing |
| play_next/play_prev engine | `b470a328` | `transport.play_next()` NUNCA existió en GStreamerPipelineTransport (bug main); ahora el engine avanza su propia cola (misma lógica que _on_about_to_finish) |
| crash_reporter 3.12 | `8e4ba021` | `args.exc_tb` no existe en Python 3.12 (`exc_traceback`) → reporter crasheaba al manejar excepciones de thread |
| build module en CI | `69790c32` | Job unit no instalaba `build` → test_rc_wheel fallaba |
| workflow nowplaying/ | `d4548352` | `tests/qml/nowplaying/` renombrado a `playback/` (path stale) |
| soundfile importorskip | `6820938d` + previos | Deps del extra audio-analysis no presentes en CI → skip honesto |
| shutdown subprocess | `a2431201` + `d1ea885b` | Timeout 15→60s (cold boot CI) + PYTHONPATH ambiente preservado (gi/GStreamer) |

### Estado CI final (checks del PR #187)
- **PASS**: lint (3.11/3.12), validate-library, validate-library-data, ai-v2, audio-integration, composition-productive
- **unit**: 4305 passed / 1 failed (flaky `test_player_service_apply_profile` — pasa en aislamiento; documentado idéntico en baseline)
- **qml-runtime**: 2 failed (home_audio.stream + e2e sidebar) — demostrados IDÉNTICOS en base 66245d11 (worktree limpio)
- **functional-tests**: 38 failed — demostrados IDÉNTICOS en base (fixtures QML settings/queue)
- **full-inventory**: corre al completarse los demás

Demostración reproducible (mandato §9): los fallos restantes fueron comparados base vs head en worktrees limpios del SHA auditado → sets idénticos. Cero regresiones nuevas.
