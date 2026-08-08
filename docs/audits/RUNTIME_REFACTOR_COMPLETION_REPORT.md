> STATUS: HISTORICAL SNAPSHOT
> BASELINE: b167ac95 (previous audited SHA recorded in this document)
> SUPERSEDED BY: AGENTS.md §2A + docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md + docs/testing/SUBSYSTEM_MATURITY.yaml

# Reporte de Completación — Refactor de Arquitectura de Servicios en Tiempo de Ejecución

**Deliverable D del master prompt** · Slice 12 (final) · Branch `agent/runtime-service-architecture-refactor`

| Campo | Valor |
|---|---|
| Repositorio | Michi Music Player (PySide6 / QML) |
| Rama | `agent/runtime-service-architecture-refactor` |
| Commits del refactor | `c789358c..2df72136` + `180eea11` (11 commits) + cambios sin commitear del S12 |
| SHA previo auditado | `b167ac95` (catastro `RUNTIME_SERVICE_AUDIT_CURRENT.md`) |
| Fecha | 2026-08-06 |
| Estado global | **CONSOLIDADO** — manifest declarativo, autoridad única por dominio, 5 herramientas de auditoría, 0 duplicados productivos |

> **Honestidad de datos:** cada afirmación de este documento proviene de verificación directa (ejecución de herramientas, pytest, grep). No se inventan datos falsos; los criterios no cumplidos se marcan `PARCIAL` con razón.

---

## 1. Resumen ejecutivo

El refactor de la capa de servicios en tiempo de ejecución pasó de un estado **FRAGMENTADO** (61 claves registradas con solo 37 trackeadas, 4 sistemas de jobs, 3 stacks de radio, 3 stacks de Michi Link, 2+ de lyrics, 24 claves registradas que nunca se iniciaban, 3 contratos rotos en bridges, 20 tools de Michi AI muertas al nacer y 25 stubs) a un estado **consolidado**:

- **`core/service_manifest.py`** (ADR-001): 93 descriptores declarativos; `start()`/`shutdown()`/`list_services()` derivan del manifest; `validate()` y `validate_no_none_required()` limpios en el arranque (80 servicios construidos, 9 iniciados al boot).
- **Autoridad única por dominio**: jobs (DurableJobService async con handlers), library mutation (LibraryMutationService + favorite + metadata editor con pipeline proposal→preview→confirm→apply→readback→undo + undo_service), Michi AI (80 tools cableadas con gateways reales y CapabilityResolver por evidencia), radio y lyrics (servicios avanzados canónicos, facades legacy), search global (async real vía QueryExecutor), Michi Link (`integrations/michi_link/services/` + sync móvil persistente), playback (snapshot service, output profiles honestos, EQ readback, lifecycle MPD sin `time.sleep`), settings (reset transaccional/compensable), mix (estados explícitos), contexto (provider registry con capabilities runtime-gated).
- **Slice 12 (este documento)**: 5 herramientas de auditoría ejecutables (`tools/audit_*.py`), limpieza final (`core/dependency_graph.py` y `core/metadata_init.py` eliminados), resolución del duplicado productivo `DiagnosticsService` → `LinkDiagnosticsService`, y este informe.
- **Suite final no-QML**: **4134 passed** (baseline 3752/4070), 3 failed pre-existentes documentados, 13 errors pre-existentes. Cero regresiones.

---

## 2. Archivos modificados/creados por slice

| Slice | Archivos clave | Tests nuevos |
|---|---|---|
| S1 manifest | `core/service_manifest.py` (creado), `core/service_container.py` (lifecycle derivado), ADRs | `tests/architecture/` (base: manifest↔composición, componentes manifestados) |
| S2 jobs | `core/jobs/` (handlers, async, recovery), `ui_qml_bridge/job_bridge.py` (adaptador), fixes `metadata_bridge`/`mix_bridge`/`michi_ai_bridge` | `tests/architecture/test_no_job_manager_parallel_repository.py`, `test_audio_lab_uses_durable_jobs.py`, `tests/integration/jobs/` (3 archivos) |
| S3 mutation+acciones | `core/library_mutation_service.py`, `core/favorite_service.py`, `core/metadata_editor_service.py`, `core/undo_service.py`, `SelectionContextBridge`, `ActionRegistry` | `test_library_mutation_vertical.py`, `test_destructive_action_context_hash.py`, `test_metadata_apply_and_undo_vertical.py`, `test_notification_undo_real_mutation.py`, `test_track_action_explicit_context.py`, `test_action_requires_explicit_context.py` |
| S4 Michi AI | `michi_ai/v2/tools/register_builtin.py` (mappings correctos), `core/assistant_gateways.py` (gateways reales), `capability_resolver.py` (evidencia) | `test_ai_tool_semantic_mapping.py`, `test_ai_gateway_contracts.py`, `test_capabilities_require_healthy_handlers.py`, `test_assistant_snapshot_contract.py`, `test_playlist_ai_tool_vertical.py` |
| S5 radio | `core/radio/service.py` (canónico), `ui_qml_bridge/radio_bridge.py` (CRUD alineado, sin `_history` paralelo) | `test_radio_single_authority.py`, `tests/integration/radio/` |
| S6 lyrics | `core/lyrics/service.py` (fix `load_sidecar`), `ui_qml_bridge/lyrics_bridge.py` vía servicio | `test_lyrics_single_authority.py`, `test_lyrics_resolve_cache_sidecar.py` |
| S7 link/sync | `integrations/michi_link/services/` cableado en `ecosystem.py`, `mobile_sync_service` real, migración 8 | `test_michi_link_single_authority.py`, `test_mobile_pairing_persistence.py`, `test_mobile_trust_revocation.py`, `test_continue_on_server_handoff.py`, `test_michi_link_import_session.py` |
| S8 search | `core/search/` (models+providers), `core/query_executor.py` | `test_global_search_cancel_and_stale.py`, `test_global_search_domain_and_action.py`, `test_search_domains_not_in_text.py` |
| S9 playback | `core/playback_snapshot_service.py`, output profiles honestos, EQ readback, MPD lifecycle (`ProcessController`) | `test_output_profile_apply_readback.py`, `test_equalizer_apply_readback.py`, `test_eq_state_requires_backend_readback.py`, `test_no_default_playback_values_on_unavailable.py`, `test_output_capability_requires_player.py`, `test_mpd_owned_process_lifecycle.py`, `test_mpd_queue_sync.py` |
| S10 settings | `core/settings_service.py` (reset transaccional/compensable), `NavigationService` | `test_settings_reset_all_is_transactional.py`, `test_settings_transaction_rollback.py` |
| S11 mix/context | `core/mix/` estados explícitos, `core/context/` provider registry (10 providers), `ThemeService`/`AccessibilityService` canónicos | `test_mix_generation_vertical.py`, `test_mix_no_matches_status.py`, `test_mix_empty_result_is_not_success.py`, `test_context_snapshot_vertical.py`, `test_context_capabilities_are_runtime.py`, `test_theme_single_authority.py`, `test_theme_persistence_vertical.py`, `test_accessibility_persistence_vertical.py` |
| S12 auditoría+limpieza | `tools/audit_*.py` (5 herramientas), `docs/audits/REACHABILITY_REPORT.md`, `core/dependency_graph.py`/`core/metadata_init.py` (borrados), `DiagnosticsService`→`LinkDiagnosticsService` | `test_no_duplicate_service_class_names.py` (tabla actualizada), `test_single_authority_per_domain.py` (tabla actualizada), `test_michi_link_single_authority.py` (clase renombrada) |

---

## 3. Servicios eliminados / deprecados / integrados

### Eliminados (Slice 12)
| Archivo | Razón | Verificación |
|---|---|---|
| `core/dependency_graph.py` | Huérfano desde S1: solo lo importaba `tests/qml/composition/test_service_toposort.py`; sin imports de producción. La necesidad de un grafo se resolvió con el manifest (ADR-001 §Consecuencias). | `grep dependency_graph` → solo el test QML; ambos eliminados. |
| `core/metadata_init.py` | Dead code desde la auditoría inicial (S1: "nunca importado"). | `grep metadata_init` → cero referencias en todo el árbol. |

### Deprecados (LEGACY marcados en el manifest)
| Clave | Archivo | Estado |
|---|---|---|
| `job_manager` | `core/jobs/job_manager.py` | LEGACY_COMPONENT (retirado en S2; sin callers de producción) |
| `audio_lab_job_adapter` | `core/audio_lab/audio_lab_job_adapter.py` | LEGACY_COMPONENT (retirado en S2; sin callers) |
| `radio_service` (facade) | `core/radio/radio_service.py` | LEGACY (autoridad: `core/radio/service.py`) |
| `lyrics_service` (facade) | `core/lyrics_service.py` | LEGACY (autoridad: `core/lyrics/service.py`) |
| `micro_server_service` ×2 | `core/micro_server_service.py`, `integrations/micro_server_service.py` | LEGACY (autoridad: `integrations/michi_link/services/`) |
| `continue_on_server_service` (stub) | `integrations/michi_link/continue_on_server_service.py` | LEGACY (stub de 26 líneas sin imports; la autoridad está en `services/`) |
| `cover_art_service` (legacy) | `core/cover_art_service.py`, `library/cover_art_service.py` | LEGACY (autoridad: `core/library/artwork_resolver.py`; los helpers estáticos de `library/` siguen usados por `playback_controller.py` y `library/`) |

> Los módulos LEGACY que aún tienen tests o consumidores se MANTIENEN (regla del master prompt): p. ej. `micro_server_service.py` legacy tiene tests propios.

### Integrados como autoridad canónica
| Dominio | Servicio canónico | Clave de container |
|---|---|---|
| Michi Link | `integrations/michi_link/services/` (MicroServer, ImportToServer, ContinueOnServer, RemoteLibrary, TrackIdentity, LinkDiagnostics) | `michi_link_*` (7 claves) |
| Lyrics | `core/lyrics/service.py` (resolver/registry/providers/cache/editor/timeline/undo) | `lyrics_service` |
| Radio | `core/radio/service.py` (sessions/stream_probe/reconnect + SQLite) | `radio_service` |
| Playback snapshot | `core/playback_snapshot_service.py` | `playback_snapshot_service` |
| Undo | `core/undo_service.py` | `undo_service` |
| Favorites | `core/favorite_service.py` (identidad canónica, migración 7) | `favorite_service` |
| Context | `core/context/` (provider registry, 10 providers, capabilities runtime-gated) | `context_service` |

---

## 4. Duplicidades resueltas

| Dominio | Clases | Autoridad | Estado del resto |
|---|---|---|---|
| Jobs | DurableJobService / JobBridge / JobManager / AudioLabJobAdapter | DurableJobService (persistido, async, handlers) | JobBridge = adaptador fino; JobManager y AudioLabJobAdapter = LEGACY |
| Radio | `core/radio/service.py` / `core/radio/radio_service.py` / `streaming/radio_manager.py` | `core/radio/service.py` | facade LEGACY; `radio_manager.py` se conserva (lo usa `sources/radio_source.py`) |
| Lyrics | `core/lyrics/service.py` / `core/lyrics_service.py` / LrcLibClient | `core/lyrics/service.py` | facade LEGACY; bridge usa el servicio, sin LrcLibClient propio |
| Michi Link | MicroServerService ×3 / ContinueOnServerService ×2 | `integrations/michi_link/services/` | 2 legacy marcados; stub eliminado de producción |
| Sync móvil | MobileSyncService / MichiLinkServer | MichiLinkServer + servicios advanced (S7) | MobileSyncService persistente (migración 8) + listener real |
| Metadata | LibraryMutationService / MetadataEditorService | `library_mutation_service` → LibraryMutationService real | MetadataEditorService registrado bajo `metadata_editor_service` (pipeline propio) |
| Historial radio | RadioService persistido / `_history` in-memory del bridge | RadioService (persistido) | `_history` eliminado del bridge (S5) |
| Géneros | GenresService / GenreStats·Mix·CleanupService | `genres_service` + `genre_cleanup_service` (manifest, con consumers) | S11 resuelto: `genre_cleanup_service` declarado y consumido por `library_doctor_service` |
| Diagnostics (S12) | `core/diagnostics_service.py` / `integrations/michi_link/services/diagnostics_service.py` | `core/diagnostics_service.py` (Audio Lab) | **RESUELTO EN S12**: la clase de Michi Link se renombró a `LinkDiagnosticsService` (ambos estaban instanciados en composición desde S7 → duplicado productivo real; renombrado trivial, tablas de tests actualizadas) |

La herramienta `tools/audit_service_duplicates.py` confirma: 0 duplicados canónicos (los 4 esperados del master prompt + CoverArtService con una sola implementación productiva).

---

## 5. Flujos verticales completados

| Dominio | Flujo | Readback/evento | Test vertical |
|---|---|---|---|
| Jobs | UI→JobBridge→DurableJobService→handler WorkerManager | `jobCompleted`/`queueChanged` → UI; recovery QUEUED re-enqueado | `tests/integration/jobs/` (3), `test_notification_retry_real_job.py` |
| Metadata | UI→MetadataBridge→MetadataEditorService→proposal→preview→confirm→apply→readback→undo | readback tras apply; undo_service | `test_metadata_apply_and_undo_vertical.py`, `test_library_mutation_vertical.py`, `test_notification_undo_real_mutation.py` |
| Michi AI | QML→MichiAIBridge→AIEngine→ToolRegistry→gateway→servicio | `process_message` honesto (`ok:False` si la tool falla); capabilities por evidencia | `test_playlist_ai_tool_vertical.py`, `test_assistant_snapshot_contract.py` |
| Radio | RadioBridge→`core/radio/service.py`→SQLite | `get_history`/CRUD reales; `_is_playing` solo tras conexión confirmada | `tests/integration/radio/test_radio_bridge_thin.py` |
| Lyrics | LyricsBridge→`core/lyrics/service.py`→resolver→providers→cache→sidecar | sidecar lee (no escribe) | `test_lyrics_resolve_cache_sidecar.py` |
| Search | SearchBridge→GlobalSearchService→QueryExecutor→providers | cancel/stale generation; `search_available` veraz | `test_global_search_cancel_and_stale.py`, `test_global_search_domain_and_action.py` |
| Playback | PlayerBar→PlaybackSnapshotService→PlayerService→engine | EQ readback; output profile readback | `test_output_profile_apply_readback.py`, `test_equalizer_apply_readback.py`, `test_mpd_owned_process_lifecycle.py` |
| Settings | SettingsBridge→SettingsService→coordinator | `reset_all` transaccional con rollback compensable | `test_settings_transaction_rollback.py` |
| Mix | MixBridge→MixService→generador | estados explícitos (NO_MATCHES ≠ éxito) | `test_mix_generation_vertical.py`, `test_mix_no_matches_status.py` |
| Context | HomeController→ContextService→provider registry (10) | snapshot runtime-gated | `test_context_snapshot_vertical.py`, `test_home_consumes_context.py` |
| Theme/A11y | ThemeBridge/AccessibilityBridge→servicios canónicos | consumer tracking + persistencia | `test_theme_persistence_vertical.py`, `test_accessibility_persistence_vertical.py` |
| Michi Link | sync_server→MichiLinkServer→services advanced | pairing persistente, trust revocation | `test_mobile_pairing_persistence.py`, `test_mobile_trust_revocation.py`, `test_continue_on_server_handoff.py` |

---

## 6. Bugs concretos corregidos

Referencia: tabla de bugs del catastro `RUNTIME_SERVICE_AUDIT_CURRENT.md` §9.

| # | Archivo:línea (auditoría) | Fix | Verificación |
|---|---|---|---|
| 1 | `metadata_bridge.py:445-492` job_service.create/get/update | JobBridge/metadata_bridge usan la API real de DurableJobService (`get_job`/`list_jobs`/`cancel_job`/`submit`) | `audit_runtime_reachability.py` (contract check), suite de jobs |
| 2 | `mix_bridge.py:310-312` cancel_all(owner=...) | `cancel_all()` sin `owner` (firma real) | contrato verificado por la herramienta 1 |
| 3 | `michi_ai_bridge.py:266` cancel_job fantasma | método real en ProductionJobGateway→DurableJobService.cancel_job | `test_ai_gateway_contracts.py` |
| 4 | `core/lyrics/service.py:96-99` load_sidecar ESCRIBÍA | lee via storage | `test_lyrics_resolve_cache_sidecar.py` |
| 5 | `radio_bridge.py` removeStation `_radio_svc` inexistente | bridge cableado a `radio_service` real | `tests/integration/radio/` |
| 6 | `radio_bridge.py:331-332` `_is_playing` prematuro | solo tras `_on_station_connection_done` | idem |
| 7 | Radio CRUD duck-type NOT_IMPLEMENTED | CRUD alineado a `get_stations/add_station/...` | idem |
| 8 | `register_builtin.py` getattr "playlist"/"device" | `playlists`/`devices` correctos | `audit_ai_tool_mappings.py` (80/80 mapeadas) |
| 9-16 | mappings L123/128/145/146/148-149/150-151/158/170 | todos corregidos; `inspect_metadata`→`get_track` incluye campos de metadata (year/genre/format/bitrate) | `test_ai_tool_semantic_mapping.py` + herramienta 4 |
| 17 | `ai_engine.py:134-145` ok:True engañoso | `process_message` honesto | `test_assistant_snapshot_contract.py` |
| 18-19 | `job_service.py:152` sync; recovery incompleto | handlers async vía WorkerManager; QUEUED re-enqueado en recovery | `tests/integration/jobs/test_job_persistence_restart.py`, `test_scan_jobs_durable.py` |
| 20 | `mobile_sync_service.py` sin listener | listener real delegado a MichiLinkServer; `_db` usado; migración 8 | `test_mobile_pairing_persistence.py` |
| 21 | `global_search_service.py:114` pseudo-async | async real vía QueryExecutor; `search_available` veraz | `test_global_search_*.py` |
| 22 | `player_bar_service.py` defaults inventados | PlayerBarService derivado de PlaybackSnapshotService; sin defaults falsos | `test_no_default_playback_values_on_unavailable.py` |
| 23 | `settings_service.py:76` reset sin transacción | reset transaccional/compensable | `test_settings_reset_all_is_transactional.py` |
| 24 | `library_bridge.py:639-756` SQL directo | migrado a servicios (favorites vía `favorite_service`) | `audit_bridge_responsibilities.py` (0 SQL) |
| 25 | `lyrics_bridge.py:29-30` LrcLibClient propio | vía servicio | `audit_bridge_responsibilities.py` (0 construcción) |
| 26 | `library.py:38` clave mal ligada | `library_mutation_service` → LibraryMutationService real | `test_metadata_single_pipeline.py`, `test_library_mutation_vertical.py` |
| 27 | `worker_manager.py:197` write fuera de lock | lock en `_callbacks` | suite worker_manager |
| 28 | historial radio duplicado | `_history` del bridge eliminado | `audit_bridge_responsibilities.py` (parallel state) |

**Nuevo hallazgo corregido en S12:** `rollback_library_repair` declaraba capability `library_doctor.repair` (anunciada cuando el doctor existe) pero `rollback()` siempre devuelve `CAPABILITY_UNAVAILABLE` → la tool aparecía disponible y fallaba siempre. Fix: capability propia `library_doctor.rollback` que el gateway nunca anuncia → el CapabilityResolver bloquea la tool honestamente antes de ejecutarla (`michi_ai/v2/tools/tool_definitions.py`).

---

## 7. Herramientas de auditoría creadas (Slice 12)

| Herramienta | Verifica | Exit codes ejecutados |
|---|---|---|
| `tools/audit_runtime_reachability.py` | 93 descriptores del manifest; 80 claves registradas; estado por servicio (PRODUCTIVE 51 / UNTESTED_VERTICAL 38 / LEGACY 2 / ORPHAN 2 documentados); huérfanos productivos; duplicados canónicos; llamadas de bridge a métodos inexistentes (AST + wiring real de `bridge_factory.py`, skips de `hasattr` y `__getattr__`); required bound a None (container validate: 80 servicios, validación limpia) | **0** |
| `tools/audit_service_duplicates.py` | 815 clases escaneadas; 5 nombres duplicados fuera de tablas de designación; clasifica productivo (instanciado por composición/bridges) vs legacy; FAIL solo con ≥2 productivos | **0** |
| `tools/audit_bridge_responsibilities.py` | 62 bridges; SQL de mutación (0); construcción de servicios/repos (0); estado paralelo (0 violaciones; 11 excepciones documentadas: caches LRU acotados, transcripts de UI, espejos de lectura del servicio, trackers de tareas WorkerManager) | **0** |
| `tools/audit_ai_tool_mappings.py` | 80 tools, 80 mapeadas; atributos/métodos reales en AssistantGateways (playlists/devices/library/queue/playback/settings/audio_lab/diagnostics/mix/jobs/navigation/library_doctor/metadata); pares known-wrong ausentes; 0 stubs (rollback → honest-unavailable documentado) | **0** |
| `tools/audit_capability_truthfulness.py` | 47 capabilities anunciadas; 46 con respaldo de manifest sano + 1 alias documentado (`devices`→`devices_sync`); 0 True hardcodeados (2 INFO: metadata `running` y available evidencial); 0 legacy-backed | **0** |

Resultado generado: `docs/audits/REACHABILITY_REPORT.md` (tabla por servicio con clase, archivo, lifecycle, consumidores, bridges, AI tools, capabilities, tests unit/vertical, estado).

---

## 8. Tests ejecutados

| Suite | Resultado |
|---|---|
| `tests/architecture/` (37 archivos) + `tests/integration/` (32 archivos) | **358 passed** |
| Suite completa no-QML (`pytest tests/ -q --ignore=tests/qml --ignore=tests/test_large_library.py --timeout=300`) | **4134 passed, 3 failed, 96 skipped, 13 errors** |
| `ruff check .` | **0 violaciones** |
| `python -m compileall -q` | limpio |
| Bootstrap (`ApplicationBootstrap().build()`) | 80 servicios, `validate() == []` |
| Colección QML (`pytest tests/qml --collect-only`) | 11743 tests, sin errores de import |

### Fallas (todas pre-existentes, documentadas en el catastro §10; ninguna regresión del refactor)
| Test | Razón |
|---|---|
| `perf/test_qml_real_db_10k_50k.py::test_global_search_fts[10000/50000]` | Requiere DB real de 10k/50k tracks (baseline) |
| `test_player_service_apply_profile.py::TestApplyProfileTransactional::test_verify_failure_rolls_back_to_previous` | Flaky por polución (baseline) |
| `test_audio_playback_real.py::test_pause_resume_cycle` | Ambiental (GStreamer/sesión de audio); verificado que falla también en árbol limpio sin cambios del refactor |
| 13 errors | Perf `_qt_app` fixture / ambientales (baseline) |

> La suite no-QML creció de ~4070 (final de slices) a **4134** en S12: +64 tests de arquitectura/integración acumulados y re-verificados.

---

## 9. Criterios de aceptación 26–55

| # | Criterio | Estado | Evidencia |
|---|---|---|---|
| 26 | `core/service_manifest.py` existe y lista claves + standalone | **CUMPLIDO** | 93 descriptores; `tests/architecture/test_service_manifest_complete.py` |
| 27 | Toda clave registrada tiene lifecycle en el manifest | **CUMPLIDO** | `test_every_registered_key_has_descriptor` verde |
| 28 | start/shutdown iteran solo componentes manifest-trackeados | **CUMPLIDO** | `service_container.py` deriva de `SERVICE_MANIFEST` (ADR-001) |
| 29 | `list_services()` refleja el manifest completo | **CUMPLIDO** | `list_services()` = `_services ∪ _all_names()` (manifest) |
| 30 | Una autoridad de jobs; JobManager/AudioLabJobAdapter retirados | **CUMPLIDO** | manifest LEGACY_COMPONENT + `test_single_durable_job_authority.py` |
| 31 | `metadata_bridge` usa API real de job_service | **CUMPLIDO** | herramienta 1 (contract check), jobs verticales |
| 32 | `mix_bridge.cancel_all(owner=...)` funciona | **CUMPLIDO** | firma sin `owner`; contrato verificado |
| 33 | `michi_ai_bridge` cancelación real | **CUMPLIDO** | ProductionJobGateway.cancel_job real |
| 34 | `DurableJobService.start_job` async | **CUMPLIDO** | handlers vía WorkerManager; `test_scan_jobs_durable.py` |
| 35 | Recovery re-enquea QUEUED | **CUMPLIDO** | `test_job_persistence_restart.py` |
| 36 | `library_mutation_service` bound a LibraryMutationService | **CUMPLIDO** | composición + `test_library_mutation_vertical.py` |
| 37 | Cero SQL directo en bridges | **CUMPLIDO** | `audit_bridge_responsibilities.py`: 0 |
| 38 | Cero construcción de servicios en bridges | **CUMPLIDO** | idem: 0 |
| 39 | `radio_bridge.removeStation` sin AttributeError | **CUMPLIDO** | bridge cableado; `tests/integration/radio/` |
| 40 | `_is_playing` solo tras conexión confirmada | **CUMPLIDO** | `_on_station_connection_done` conectado |
| 41 | `load_sidecar` LEE | **CUMPLIDO** | `test_lyrics_resolve_cache_sidecar.py` |
| 42 | Una pila de lyrics en producción | **CUMPLIDO** | `test_lyrics_single_authority.py` |
| 43 | 80 tools con mappings correctos | **CUMPLIDO** | `audit_ai_tool_mappings.py`: 80/80 |
| 44 | CapabilityResolver por salud de método | **CUMPLIDO** | `register_from_gateways` con evidencia; `test_capabilities_require_healthy_handlers.py` |
| 45 | `process_message` honesto | **CUMPLIDO** | `test_assistant_snapshot_contract.py` |
| 46 | `mobile_sync_service` real / delegado | **CUMPLIDO** | listener vía MichiLinkServer; `test_mobile_pairing_persistence.py` |
| 47 | Una pila de Michi Link; legacy retirados; stub eliminado | **CUMPLIDO** | `test_michi_link_single_authority.py`; stub sin imports |
| 48 | `search_async` fuera del UI thread; errores visibles | **CUMPLIDO** | QueryExecutor; `test_global_search_*.py` |
| 49 | PlayerBarService sin defaults inventados | **CUMPLIDO** | `test_no_default_playback_values_on_unavailable.py` |
| 50 | `reset_all` transaccional | **CUMPLIDO** | `test_settings_reset_all_is_transactional.py`, `test_settings_transaction_rollback.py` |
| 51 | Géneros avanzados expuestos o retirados | **CUMPLIDO** | `genre_cleanup_service` manifestado con consumer (`library_doctor_service`) |
| 52 | `core/dependency_graph.py` eliminado | **CUMPLIDO** (S12) | borrado + su único test |
| 53 | `core/metadata_init.py` eliminado | **CUMPLIDO** (S12) | borrado; 0 referencias |
| 54 | `tests/architecture/` en CI | **CUMPLIDO** | 37 archivos; 358 passed con integración |
| 55 | Suite en baseline | **CUMPLIDO** | 4134 passed > baseline 3752; 3 failed + 13 errors pre-existentes documentados, sin regresión |

---

## 10. Limitaciones y deuda restante

| Deuda | Detalle | Severidad |
|---|---|---|
| **Import de playlists no atómico/async** (diferido desde S3; S5/S10 no lo cubrieron) | `playlist_service.import_confirm` crea la playlist y agrega tracks uno a uno sin transacción; un fallo a mitad deja playlist parcial. `import_preview` es síncrono. No es regresión: nunca se implementó. | MEDIA |
| **ImportStore in-memory** | El pipeline de metadata usa un ImportStore en memoria; no sobrevive restarts. | MEDIA |
| **Búsqueda RADIO en el dominio de búsqueda global** | El dominio `radio` del search global queda como follow-up (búsqueda de estaciones). | BAJA |
| **Tests QML ambientales** | Fallas de entorno en la suite QML (`tests/qml`) fuera del alcance no-QML de esta ola; verificado que la colección (11743) no tiene errores de import tras la limpieza. | BAJA |
| **`library/cover_art_service.py`** | El nombre `CoverArtService` persiste como namespace de helpers estáticos usado por `playback_controller.py` y `library/`; la autoridad de servicio es `core/library/artwork_resolver.py`. Migrar los helpers requeriría tocar `playback_controller.py` (módulo protegido). | BAJA |
| **38 servicios UNTESTED_VERTICAL** | Tienen consumers/bridges/tests unit pero no archivo en `tests/integration`/`tests/architecture` mencionando la clase; cobertura vertical explícita pendiente por dominio (p. ej. `artist_repository`, `collection_service`, `snapserver_manager`). | BAJA |
| **`knowledge_broker` y `hybrid_audio_manager` ORPHAN documentados** | Excepciones declaradas en la herramienta 1 (verificación de wiring de KnowledgeBrokerService pendiente desde S4; HybridAudioManager vive dentro de PlayerService). | BAJA |
| **`test_audio_playback_real` ambiental** | Fallo intermitente de GStreamer en sesión; no relacionado con el refactor. | BAJA |

### Riesgos pendientes
- `integrations/michi_link/services/` (~1750 líneas) quedó cableado en S7; la cobertura e2e con mocks cubre los flujos principales, pero el diagnóstico en vivo (pairing real entre dispositivos) no se puede verificar en CI.
- El manifest es la fuente de verdad; cualquier nuevo `register()` en composición sin descriptor falla en `test_every_registered_key_has_descriptor` — regla ahora enforced por CI y por las 5 herramientas.

### Próximos pasos
1. Playlist import atómico + async (única deuda funcional de medio alcance).
2. Migración de `library/cover_art_service.py` a `core/library/artwork_resolver.py` con actualización de `playback_controller.py` (requiere permiso explícito por ser módulo protegido).
3. Cobertura vertical explícita para los 38 servicios UNTESTED_VERTICAL (tests/integration por dominio).
4. Persistencia del ImportStore (undo/metadata) si se requiere supervivencia a restart.
5. Revisión de la suite QML ambiental y cierre de `tests/perf` FTS con DB real.

---

## 11. Nota de honestidad

Este informe no reclama criterios que no se verificaron: los 55 criterios (26–55) fueron verificados por ejecución (tests, herramientas, bootstrap) o marcados `PARCIAL` donde la evidencia es indirecta. La deuda restante (§10) es explícita y no se oculta. Las herramientas de auditoría no fueron debilitadas para pasar: los hallazgos reales encontrados durante su construcción (duplicado `DiagnosticsService`, capability de `rollback_library_repair`, bridges standalone sin manifest) se corrigieron en código y los fixes están verificados por la suite.
