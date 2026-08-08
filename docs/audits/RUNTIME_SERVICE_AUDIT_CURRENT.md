> STATUS: HISTORICAL SNAPSHOT
> BASELINE: b167ac95 (SHA auditado recorded in this document)
> SUPERSEDED BY: AGENTS.md §2A + docs/testing/DEVELOPMENT_CONVERGENCE_MODE.md + docs/testing/SUBSYSTEM_MATURITY.yaml

# Catastro Inicial Actualizado — Auditoría de Servicios en Tiempo de Ejecución (Runtime Service Architecture)

**Deliverable:** "Catastro inicial actualizado" — primera ola del refactor de arquitectura de servicios.

| Campo | Valor |
|---|---|
| Repositorio | Michi Music Player (PySide6 / QML) |
| SHA auditado | `b167ac95fa89689644508633cfecfc08f777a469` |
| HEAD actual (auditoría) | `4ea914f5e100b3c9019fadf956182b0455c8bba6` |
| Fecha de auditoría | 2026-08-05 |
| Método | Inspección de composición + verificación de llamadas + spot-checks con grep |
| Estado global | **FRAGMENTADO** — 4 sistemas de jobs, 3 stacks de radio, 3 stacks de Michi Link, 2+ de lyrics, 24 claves registradas que nunca se inician, 3 contratos rotos en bridges |

> **Honestidad de datos:** cada afirmación de este documento proviene de verificación directa (grep) o de los hechos base verificados del prompt maestro. Donde no hay dato, se escribe `unknown` o una estimación marcada como tal. **No se inventan datos falsos.**

---

## 1. Resumen ejecutivo

La capa de servicios en tiempo de ejecución está **fragmentada y con contratos rotos**. El contenedor (`core/service_container.py`) registra **61 claves** vía los builders de composición (`core/composition/{infrastructure,playback,library,audio_lab,ecosystem,settings,intelligence}.py` + `core/application_bootstrap.py`), pero solo **37 nombres** están trackeados en listas estáticas (`_required_names()` 28 + `_optional_names()` 8 + `_capability_gated_names()` {michi_ai_service}). `start()` itera solo esas 37; `shutdown()`/`cancel_all()` iteran todas; `list_services()` muestra solo 37. Resultado: **24 claves registradas que NUNCA se inician** (repositorios, servicios de librería, snapcast, sync móvil, cd_ripper, navigation_service, etc.).

Principales hallazgos:

- **4 sistemas de jobs paralelos**: DurableJobService (persistido, pero 0 handlers en producción y ejecución síncrona), JobBridge (lo que las pantallas usan de verdad), JobManager (solo usado por una ruta de diagnóstico sin callers), AudioLabJobAdapter (sin callers). **3 llamadas de bridge a APIs inexistentes** (`metadata_bridge` → `job_service.create/get/update`; `mix_bridge` → `cancel_all(owner=...)`; `michi_ai_bridge` → `cancel_job`).
- **Michi AI**: 80 tools definidas; **20 muertas al nacer** por mapeos `getattr` incorrectos (`"playlist"`/`"device"` vs campos `playlists`/`devices`), **25 stubs** de gateways de producción, solo **35** llegan a operaciones reales. `process_message` devuelve `ok:True` aunque la tool falle.
- **Radio ×3, Lyrics ×2+, Michi Link ×3** (MicroServerService duplicado 3 veces, ContinueOnServerService 2 veces). El bridge de radio tiene bugs concretos (`removeStation` → AttributeError; `_is_playing` prematuro) y CRUD silenciosamente `NOT_IMPLEMENTED` por desalineación de API.
- **Huérfanos**: `core/dependency_graph.py` (legacy, solo lo usa su propio test), `core/metadata_init.py` (dead code), `core/lyrics/service.py` (avanzado, sin uso; con bug `load_sidecar` que ESCRIBE un documento vacío), servicios avanzados de `integrations/michi_link/services/` (~1750 líneas sin cablear), `LibraryMutationService` (clase real sin uso; la clave `library_mutation_service` está ligada a `MetadataEditorService`).
- **Bridges con SQL** y **bridges construyendo servicios como fallback** (playlists, history, job, library_doctor, lyrics): violación sistemática de la separación bridge/servicio.
- `core/service_manifest.py` **no existe**. No hay `tests/architecture/`.

La primera ola del refactor (S1 manifest, S2 jobs, S3 mutation+action context, S4 Michi AI) ataca exactamente los puntos de mayor riesgo.

---

## 2. Alcance y método

| Ítem | Valor |
|---|---|
| SHA auditado | `b167ac95fa89689644508633cfecfc08f777a469` |
| HEAD actual al momento de auditar | `4ea914f5e100b3c9019fadf956182b0455c8bba6` |
| Delta entre ambos | 1 commit propio: `fix(mix): detalle, generador, reglas y resultado funcionales` |
| PR #184 `agent/implement-real-mix-services` | **Revisado — NO integrar.** Su diff está SUPERSEDED por trabajo ya mergeado a main (Mix pages + presentation provider). |
| PR #185 `agent/fix-test-isolation-gates` | **Revisado — fuera de alcance** de esta ola (aislamiento de tests). |

**Método empleado:**
1. Verificación del árbol git (HEAD, log, delta vs SHA auditado).
2. Lectura de `core/service_container.py` (listas `_required_names`, `_optional_names`, `_capability_gated_names`).
3. Inventario de registros por módulo de composición (`grep container.register` en los 7 builders + bootstrap).
4. Verificación de llamadas de bridges contra APIs reales de servicios (job, mix, michi_ai, radio, lyrics).
5. Verificación de wiring de Michi AI (gateways, capability resolver, tool_definitions).
6. Inventario de sistemas duplicados (jobs, radio, lyrics, Michi Link, metadata).
7. Baseline de tests: `3752 passed`, `3 failed`, `13 errors` (fallas pre-existentes documentadas en §10).

---

## 3. Diferencias respecto del SHA auditado

Único delta entre `b167ac95` y `4ea914f5`:

| Commit | Contenido | Impacto en auditoría |
|---|---|---|
| `4ea914f5` `fix(mix): detalle, generador, reglas y resultado funcionales` | Mix pages funcionales (detalle, generador, reglas, resultado) + `PresentationPreviewProvider` en `tools/presentation_preview/provider.py` | Clase nueva de solo lectura (adapters demo); no cambia composición ni contratos de servicios. |

**Conclusión:** los hechos verificados sobre el SHA auditado siguen vigentes en HEAD; el catastro de este documento es el estado actual.

---

## 4. Servicios canónicos

Leyenda de estados: `PRODUCTIVE` = operativo y usado · `DEGRADED` = operativo con defectos · `ORPHAN` = clase real sin uso en producción · `STUB` = implementación de relleno · `CONTRACT_MISMATCH` = la clave liga a la clase equivocada · `UNREACHABLE` = registrado pero nunca iniciado por el contenedor · `DUPLICATE` = duplicado de otro componente · `LEGACY` = obsoleto, reemplazado.

### 4.1 Los 37 servicios trackeados (28 required + 8 optional + 1 capability-gated)

| Clave | Clase | Archivo | Estado |
|---|---|---|---|
| database | DatabaseManager (nominal) | `core/...` (infrastructure.py:26) | PRODUCTIVE |
| connection_factory | (mismo objeto que database) | infrastructure.py:27 | PRODUCTIVE |
| worker_manager | WorkerManager | `core/worker_manager.py:197` | PRODUCTIVE (1 escritura de `_callbacks` fuera de lock; menor) |
| query_executor | QueryExecutor | `core/query_executor.py:73` | PRODUCTIVE (fallback síncrono sin worker, líneas 184-186) |
| job_service | DurableJobService | `core/jobs/job_service.py` | DEGRADED (0 handlers en producción, ejecución síncrona, recuperación de restart incompleta) |
| event_bus | EventBus (nominal) | infrastructure.py:48 | PRODUCTIVE |
| settings_coordinator | SettingsRuntimeCoordinator | `core/settings_runtime_coordinator.py:49` | PRODUCTIVE |
| settings_service | SettingsService | `core/settings_service.py` | PRODUCTIVE (`reset_all` sin transacción, líneas 76+) |
| library_query_service | LibraryQueryService | `core/library/library_query_service.py` | PRODUCTIVE |
| library_sources_service | LibrarySourcesService | `core/library_sources_service.py` | PRODUCTIVE |
| library_mutation_service | **MetadataEditorService** (mal binding) | `core/metadata_editor_service.py` vía `core/composition/library.py:38` | CONTRACT_MISMATCH |
| playlist_service | PlaylistService | `core/playlist_service.py` | PRODUCTIVE |
| history_query_service | HistoryQueryService | `core/history_query_service.py` | PRODUCTIVE |
| global_search_service | GlobalSearchService | `core/global_search_service.py:114` | DEGRADED (pseudo-async QTimer, errores FTS tragados) |
| mix_query_service | (clase nominal, sin verificar) | intelligence.py:30 | PRODUCTIVE (ver nota Mix) |
| mix_service | (clase nominal, sin verificar) | intelligence.py:31 | DEGRADED (`ok:True` con gateways stub) |
| track_action_service | TrackActionService | `core/track_action_service.py` | PRODUCTIVE |
| playback_service | PlayerService | `audio/player_service.py` | PRODUCTIVE |
| queue_service | QueueService | `core/queue_service.py` | PRODUCTIVE |
| metadata_service | MetadataService (sin args) | `core/metadata_service.py` vía `library.py:53` | PRODUCTIVE |
| process_controller | ProcessController | infrastructure.py:45 | PRODUCTIVE |
| runtime_persistence | RuntimePersistence | infrastructure.py:43 | PRODUCTIVE |
| theme_service | BackgroundThemeService | settings.py:36 | PRODUCTIVE |
| accessibility_service | AccessibilityService | settings.py:43 | PRODUCTIVE |
| action_registry | ActionRegistry | `ui_qml_bridge/action_registry.py:37` | PRODUCTIVE |
| confirmation_service | ConfirmationService | `core/confirmation_service.py` | PRODUCTIVE |
| notification_service | NotificationService | `core/notification_service.py` | PRODUCTIVE |
| diagnostics_service | DiagnosticsService (nominal) | `core/audio_lab/diagnostics_service.py` | PRODUCTIVE (su ruta analyse_directory_job no tiene callers) |
| audio_lab_service | AudioLabService | `core/audio_lab/audio_lab_service.py` | PRODUCTIVE |
| smart_tagging_service | SmartTaggingService | `core/smart_tagging_service.py` | PRODUCTIVE |
| library_doctor_service | LibraryDoctorService | `core/...` (library.py:57) | PRODUCTIVE |
| device_sync_service | DeviceSyncService | ecosystem.py:101 | PRODUCTIVE (nominal) |
| connection_service | (clase no verificada) | ecosystem.py:38 | PRODUCTIVE (nominal) |
| home_audio_service | (clase no verificada) | ecosystem.py:92 | PRODUCTIVE (nominal) |
| radio_service | RadioService | `core/radio/radio_service.py` | DEGRADED (bridge con API desalineada → CRUD NOT_IMPLEMENTED) |
| lyrics_service | LyricsService (legacy nominal) | `core/lyrics_service.py` | DEGRADED (producción usa legacy; el bridge salva por su cuenta) |
| michi_ai_service | MichiAIEngine | `core/ai_engine.py:22` (composición `core/assistant_initializer.py`) | DEGRADED (20 tools muertas, 25 stubs, `ok:True` engañoso) |

### 4.2 Las 24 claves registradas pero NUNCA iniciadas

Estado global: **UNREACHABLE** (el contenedor las registra pero `start()` no las recorre; varias tienen lifecycle propio que nadie invoca).

| Clave | Clase | Construido en | Nota |
|---|---|---|---|
| settings_manager | (QSettings wrapper) | infrastructure.py:22 | Pasivo por diseño; no requiere start |
| paths | (path resolver) | infrastructure.py:23 | Pasivo por diseño |
| read_connection_factory | ReadConnectionFactory | infrastructure.py:33 | Pasivo por diseño |
| writer_coordinator | WriterCoordinator | infrastructure.py:34 | Pasivo por diseño |
| track_repository | TrackRepository | infrastructure.py:39 | Pasivo; consumidores vía query service |
| album_repository | AlbumRepository | infrastructure.py:40 | Pasivo |
| artist_repository | ArtistRepository | infrastructure.py:41 | Pasivo |
| library_filtered_query_service | LibraryFilteredQueryService (alias del mismo objeto que library_query_service) | library.py:35 | Alias; nunca iniciado |
| collection_service | CollectionService | library.py:36 | Nunca iniciado |
| folder_tree_model | FolderTreeModel | library.py:37 | Nunca iniciado |
| library_service | LibraryService (tiene shutdown) | library.py:39 | Nunca iniciado |
| recognition_service | RecognitionService (tiene start + shutdown) | library.py:66 | **Nunca iniciado** |
| artwork_service | CoverArtService (tiene shutdown) | library.py:76 | Nunca iniciado |
| songs_service | SongsService (tiene shutdown) | library.py:83 | Nunca iniciado |
| track_service | TrackService (tiene shutdown) | library.py:90 | Nunca iniciado |
| genres_service | GenresService (tiene shutdown) | library.py:97 | Nunca iniciado |
| folder_service | FolderService (tiene shutdown) | library.py:104 | Nunca iniciado |
| mpris_adapter | MPRIS adapter (nominal) | playback.py:51 | Nunca iniciado |
| snapcast_control | SnapcastJsonRpcClient | ecosystem.py:60 | Nunca iniciado |
| snapserver_manager | SnapServerManager (tiene start/stop) | ecosystem.py:49 | **Nunca iniciado** |
| device_registry | DeviceRegistry | `core/sync/device_registry.py:49` (ecosystem.py:102) | Nunca iniciado |
| mobile_sync_service | MobileSyncService | `core/mobile_sync_service.py` (ecosystem.py:109) | Nunca iniciado; sin listener real |
| cd_ripper_service | CDRipperService (tiene cancel/shutdown) | `core/audio_lab/cd_ripper_service.py` (audio_lab.py:35) | **Nunca iniciado** |
| navigation_service | NavigationService | `core/application_bootstrap.py:89` | Nunca iniciado |

> ⚠️ **IMPORTANTE:** la mayoría de estas claves son repositorios/objetos pasivos que funcionan sin `start()`; el problema no es su existencia sino que **no hay manifest** que distinga "pasivo por diseño" de "se olvidó cablear" (ej. `recognition_service`, `snapserver_manager`, `cd_ripper_service`, `library_service` tienen lifecycle real que nadie invoca).

### 4.3 Clases/archivos de nivel registro (fuera del contenedor)

| Componente | Archivo | Estado |
|---|---|---|
| LibraryMutationService (clase real) | `core/library_mutation_service.py` | ORPHAN (solo su unit test la usa) |
| core/service_manifest.py | — (NO EXISTE) | FALTA — entregable S1 |
| DependencyGraph | `core/dependency_graph.py` | LEGACY (solo lo usa su propio test; nombres desincronizados) |
| core/metadata_init.py | — | DEAD CODE |
| JobBridge | `ui_qml_bridge/job_bridge.py` | DUPLICATE (sistema de jobs #2; de facto el productivo para scans) |
| JobManager | `core/jobs/job_manager.py` | ORPHAN (solo `diagnostics_service.py:730-808`, sin callers) |
| AudioLabJobAdapter | `core/audio_lab/audio_lab_job_adapter.py` | ORPHAN (sin callers) |
| Advanced RadioService | `core/radio/service.py` | ORPHAN (sessions/stream_probe/reconnect sin uso) |
| Advanced LyricsService | `core/lyrics/service.py` | ORPHAN (con bug confirmado, ver §9) |
| Advanced Michi Link services | `integrations/michi_link/services/` (~1750 líneas) | ORPHAN (no cableados; ecosystem.py registra MichiLinkClient) |
| PlayerBarService | `core/player_bar_service.py:9` | ORPHAN (no registrado; inventa defaults volume=75/stopped/0.0) |
| KnowledgeBrokerService | `integrations/knowledge_broker/service.py:27` | UNVERIFIED (uso en producción no verificado) |

---

## 5. Componentes sin sufijo `Service`

Clasificación propuesta (taxonomía de la ampliación): `managed_service` · `domain_service` · `application_service` · `passive_repository` · `state_store` · `executor` · `process_manager` · `UI_adapter` · `registry` · `factory` · `external_resource` · `legacy_component`.

| Componente | Archivo | Clasificación propuesta | Racional |
|---|---|---|---|
| WorkerManager | `core/worker_manager.py:197` | executor (managed) | Única instancia productiva; mayormente thread-safe; ejecuta jobs vía ThreadPool |
| QueryExecutor | `core/query_executor.py:73` | executor | Fallback síncrono sin worker (184-186); generations/supersede/cancel por owner; errores sqlite tipados |
| JobManager | `core/jobs/job_manager.py` | legacy_component | Repositorio propio (job_queue.db) sin DI; cancelación falsa; sin callers reales |
| JobBridge | `ui_qml_bridge/job_bridge.py` | UI_adapter | Registro propio `_jobs` (cap 200); delega en WorkerManager; fallback síncrono; de facto el sistema de scans |
| AudioLabJobAdapter | `core/audio_lab/audio_lab_job_adapter.py` | UI_adapter | Registro in-memory; WorkerManager-backed; `submit_*` sin callers |
| ActionRegistry | `ui_qml_bridge/action_registry.py:37` | registry | Registrado como `action_registry` (required) |
| ActionRegistryBinder | `ui_qml_bridge/action_registry_binder.py:30` | factory/binder | Vincula acciones a widgets/bridges |
| SelectionContextBridge | `ui_qml_bridge/selection_context_bridge.py:12` | state_store / UI_adapter | Estado de selección compartido QML↔Python |
| BridgeFactory | `ui_qml_bridge/bridge_factory.py:35` | factory | Construye bridges con inyección de servicios |
| DeviceRegistry | `core/sync/device_registry.py:49` | registry | Registrado (`device_registry`) pero nunca iniciado |
| MpdServiceManager | `audio/mpd/mpd_service_manager.py:28` | process_manager | Gestiona daemon MPD |
| SnapserverManager | `integrations/snapcast/snapserver_manager.py` | process_manager | start/stop de snapserver; nunca iniciado por contenedor |
| SnapcastControl | `integrations/snapcast/...` (SnapcastJsonRpcClient) | external_resource | Cliente JSON-RPC de Snapcast |
| SettingsRuntimeCoordinator | `core/settings_runtime_coordinator.py:49` | domain_service (coordinator) | Registrado como `settings_coordinator` |
| HybridAudioManager | `audio/backends/hybrid_audio_manager.py:52` | application_service | Orquestador GStreamer/MPD dentro de PlayerService (no registrado en contenedor) |
| PageStateStore | `ui_qml_bridge/page_state_store.py:8` | state_store | Estado de páginas QML |
| KnowledgeBrokerService | `integrations/knowledge_broker/service.py:27` | domain_service | Uso en producción no verificado |
| ProviderManager | `recognition/provider_manager.py:35` | registry | Gestor de proveedores de reconocimiento (Shazam/AudD/AcoustID) |
| QueryExecutor (listado 2º en ampliación) | `core/query_executor.py:73` | executor | Idem fila anterior (duplicado de enumeración en el prompt; única entidad) |

---

## 6. Tabla maestro del catastro ampliado

> **Nota:** catastro reconstruido desde datos verificados = **61 claves registradas** + **19 componentes standalone** = 80 filas. Celdas con `unknown` = no verificado. `—` = no aplica. `vertical_test`: archivo de test si existe/verificado, si no `unknown` (no se inventan nombres).

Abreviaturas: `ctor` = construido por · `SvcCont` = ServiceContainer · `WkMgr` = WorkerManager · `impl.` = implementation.

### 6.1 Infraestructura (20)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| settings_manager | passive_repository | core | infrastructure.py:22 | settings_manager | none | none | SvcCont (tracking: NO) | — (pasivo) | — | none | none | none | QSettings | none | QSettings file | none | servicios | none | settings | none | UNREACHABLE (pasivo OK) | S1 (manifest: marcar pasivo) | unknown |
| paths | passive_repository | core | infrastructure.py:23 | paths | none | none | SvcCont (NO) | — | — | none | none | none | XDG dirs | none | none | none | muchos | none | path resolution | none | UNREACHABLE (pasivo OK) | S1 | unknown |
| database | managed_service | core | infrastructure.py:26 | database | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite WAL | db file | none | db file | none | todos | none | db handle | none | PRODUCTIVE | — | unknown |
| connection_factory | managed_service | core | infrastructure.py:27 | connection_factory | none | = database | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | — | none | servicios | none | conexiones | none | PRODUCTIVE | — | unknown |
| read_connection_factory | passive_repository | core | infrastructure.py:33 | read_connection_factory | none | dp | SvcCont (NO) | — | — | none | none | SQLite RO | db file | none | none | none | services | none | conexiones RO | none | UNREACHABLE (pasivo) | S1 | unknown |
| writer_coordinator | managed_service | core | infrastructure.py:34 | writer_coordinator | none | dp | SvcCont (NO) | — | — | none | none | SQLite | db file | none | none | cola de escritura | servicios | none | escritura coordinada | none | UNREACHABLE | S1/S2 | unknown |
| track_repository | passive_repository | library | infrastructure.py:39 | track_repository | none | db | SvcCont (NO) | — | — | none | none | SQLite | — | none | none | none | query services | none | CRUD tracks | none | UNREACHABLE (pasivo) | S1 | unknown |
| album_repository | passive_repository | library | infrastructure.py:40 | album_repository | none | db | SvcCont (NO) | — | — | none | none | SQLite | — | none | none | none | query services | none | CRUD albums | none | UNREACHABLE (pasivo) | S1 | unknown |
| artist_repository | passive_repository | library | infrastructure.py:41 | artist_repository | none | db | SvcCont (NO) | — | — | none | none | SQLite | — | none | none | none | query services | none | CRUD artists | none | UNREACHABLE (pasivo) | S1 | unknown |
| runtime_persistence | managed_service | core | infrastructure.py:43 | runtime_persistence | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | estado de runtime | runtime | shell | none | persistencia sesión | none | PRODUCTIVE | — | unknown |
| process_controller | process_manager | core | infrastructure.py:45 | process_controller | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | possible subprocesses (unknown) | none | none | unknown | none | procesos | services | none | control procesos | none | PRODUCTIVE | — | unknown |
| event_bus | managed_service | core | infrastructure.py:48 | event_bus | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | events | todos | none | pub/sub | none | PRODUCTIVE | — | unknown |
| worker_manager | executor | core | infrastructure.py:52 | worker_manager | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | ThreadPool | none | none | none | none | none | workers/callbacks | jobs, bridges, services | job_bridge | ejecución jobs | none | PRODUCTIVE (1 write sin lock) | S2 (lock `_callbacks`) | unknown |
| query_executor | executor | core | infrastructure.py:53 | query_executor | none | wm | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | ThreadPool (vía wm) | none | SQLite | — | none | none | none | servicios | none | queries async + fallback sync (184-186) | none | PRODUCTIVE | — | unknown |
| job_service | managed_service | core/jobs | infrastructure.py:55 | job_service | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none (sync inline) | none | durable_jobs.db | db file | none | durable_jobs.db | handlers (0) | metadata_bridge (roto) | none | jobs durable | JobBridge/JobManager/AudioLabJobAdapter | DEGRADED | S2 | unknown |
| confirmation_service | managed_service | core | infrastructure.py:56 | confirmation_service | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | none | inteligencia/UI | none | confirmaciones | none | PRODUCTIVE | — | unknown |
| settings_coordinator | domain_service | core | infrastructure.py:61 | settings_coordinator | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | QSettings | none | QSettings | settings | settings_service | none | coordinación settings | none | PRODUCTIVE | — | unknown |
| settings_service | managed_service | core | infrastructure.py:62 | settings_service | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | QSettings | none | QSettings | settings | bridges | settings_bridge | get/set/open/reset_all | none | PRODUCTIVE (reset_all no transaccional) | S10 | unknown |
| theme_service | managed_service | core | settings.py:36 | theme_service | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | theme | UI | none | theming | none | PRODUCTIVE | — | unknown |
| accessibility_service | managed_service | core | settings.py:43 | accessibility_service | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | accesibilidad | UI | none | accesibilidad | none | PRODUCTIVE | — | unknown |

### 6.2 Librería (20)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| library_sources_service | managed_service | library | library.py:31 | library_sources_service | none | (sources) | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite (vía queries) | root paths | none | carpeta escaneada | roots | índice, folder_tree | library_bridge | fuentes | none | PRODUCTIVE | — | unknown |
| library_query_service | managed_service | library | library.py:34 | library_query_service | none | db/cf | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite (FTS5) | — | none | — | none | muchos servicios | library_bridge | queries biblioteca | library_filtered_query_service (alias) | PRODUCTIVE | — | unknown |
| library_filtered_query_service | managed_service | library | library.py:35 | library_filtered_query_service (alias) | none | = lqs | SvcCont (NO) | — | — | none | none | SQLite | — | none | — | none | filtra clientes | library_bridge | queries filtradas | library_query_service (mismo objeto) | UNREACHABLE (alias) | S1 (documentar alias) | unknown |
| collection_service | managed_service | library | library.py:36 | collection_service | none | db, lqs | SvcCont (NO) | — | — | unknown | none | SQLite | — | none | none | colecciones | unknown | library_bridge | colecciones | none | UNREACHABLE | S1 | unknown |
| folder_tree_model | state_store | library | library.py:37 | folder_tree_model | none | sources_svc | SvcCont (NO) | — | — | none | none | none | root paths | none | none | árbol | folder UI | folder_bridge | árbol carpetas | none | UNREACHABLE | S1 | unknown |
| library_mutation_service | managed_service | library | library.py:38 (mal bound) | library_mutation_service | none | db | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | files | none | none | none | editores | metadata_bridge | edición metadatos | LibraryMutationService (clase real, sin bound) | CONTRACT_MISMATCH | S3 | unknown |
| library_service | managed_service | library | library.py:39 | library_service | none | db, wm, lqs | SvcCont (NO) | — | tiene shutdown (nunca llamado) | unknown | none | SQLite | files | none | — | — | indexer/UI | library_bridge | escaneo/índice | none | UNREACHABLE | S1/S2 | unknown |
| playlist_service | managed_service | library | library.py:41 | playlist_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | playlists | none | UI, playlists_bridge | playlists_bridge | CRUD playlists | none | PRODUCTIVE | — | unknown |
| track_action_service | managed_service | library | library.py:43 | track_action_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | files | none | — | — | UI | none | acciones tracks | none | PRODUCTIVE | S3 (contexto de acciones) | unknown |
| history_query_service | managed_service | library | library.py:51 | history_query_service | none | cf | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | historial | — | UI, history_bridge | history_bridge | historial | none | PRODUCTIVE | — | unknown |
| global_search_service | managed_service | library | library.py:52 | global_search_service | none | db_path | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none (QTimer 0) | none | SQLite FTS5 | — | none | — | — | search UI | search bridge | búsqueda global | none | DEGRADED (pseudo-async, FTS silenciado) | S8 | unknown |
| metadata_service | managed_service | library | library.py:53 | metadata_service | none | (sin args) | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | files | none | — | — | metadata UI | metadata_bridge | metadatos | none | PRODUCTIVE | — | unknown |
| library_doctor_service | managed_service | library | library.py:57 | library_doctor_service | none | db | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite | files | none | — | — | doctor UI | library_doctor_bridge | diagnóstico librería | LibraryDoctorScanRepository (fallback bridge) | PRODUCTIVE | — | unknown |
| recognition_service | managed_service | recognition | library.py:66 | recognition_service | none | unknown | SvcCont (NO) | tiene start (nunca llamado) | tiene shutdown (nunca llamado) | unknown | none | none | audio capture | HTTP (Shazam/AudD/AcoustID) | — | — | IdentifierController | — | identificación | ProviderManager | UNREACHABLE | S1 | unknown |
| smart_tagging_service | managed_service | library | library.py:69 | smart_tagging_service | none | unknown | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite | — | none | — | — | tagging UI | none | tag inteligente | none | PRODUCTIVE | — | unknown |
| artwork_service | managed_service | library | library.py:76 | artwork_service | none | db | SvcCont (NO) | — | tiene shutdown (nunca llamado) | unknown | none | SQLite | carátulas | none | carátulas | — | UI | library_bridge | carátulas | none | UNREACHABLE | S1 | unknown |
| songs_service | managed_service | library | library.py:83 | songs_service | none | db, lqs | SvcCont (NO) | — | shutdown nunca llamado | unknown | none | SQLite | — | none | — | — | UI | none | canciones | none | UNREACHABLE | S1 | unknown |
| track_service | managed_service | library | library.py:90 | track_service | none | db | SvcCont (NO) | — | shutdown nunca llamado | unknown | none | SQLite | — | none | — | — | UI | none | tracks | none | UNREACHABLE | S1 | unknown |
| genres_service | managed_service | library | library.py:97 | genres_service | none | db | SvcCont (NO) | — | shutdown nunca llamado | unknown | none | SQLite | — | none | — | — | UI | none | géneros | GenreStatsService (advanced) | UNREACHABLE | S1/S11 | unknown |
| folder_service | managed_service | library | library.py:104 | folder_service | none | db, wm | SvcCont (NO) | — | shutdown nunca llamado | unknown | none | SQLite | files | none | — | — | folder UI | folder_bridge | carpetas | none | UNREACHABLE | S1 | unknown |

### 6.3 Playback (4)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| queue_service | managed_service | playback | playback.py:33 | queue_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | cola (persistida, nominal) | — | UI, PlayerService | now_playing_bridge | cola | none | PRODUCTIVE | — | unknown |
| playback_service | managed_service | playback | playback.py:34 | playback_service | none | GStreamerEngine, HybridAudioManager | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | QThread (engine) | none (GStreamer in-process) | none | files/streams | streams | — | estado playback | UI, MPRIS, home | playback_bridge, mpris | play/pause/seek/EQ/DSP | none | PRODUCTIVE | — | unknown |
| notification_service | managed_service | playback | playback.py:35 | notification_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | notificaciones | UI | none | notificaciones | none | PRODUCTIVE | — | unknown |
| mpris_adapter | UI_adapter | playback | playback.py:51 | mpris_adapter | none | playback_service | SvcCont (NO) | — | — | none | none | none | none | D-Bus | none | — | desktop | none | MPRIS | none | UNREACHABLE | S1 | unknown |

### 6.4 Inteligencia (4)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| action_registry | registry | inteligencia | intelligence.py:14 | action_registry | none | none | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | none | none | none | none | acciones | UI/bridges | ActionRegistryBinder | registro de acciones | none | PRODUCTIVE | S3 (contexto de acción) | unknown |
| mix_query_service | managed_service | inteligencia | intelligence.py:30 | mix_query_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | — | — | mix UI | mix_bridge | queries mix | none | PRODUCTIVE (nominal) | — | unknown |
| mix_service | managed_service | inteligencia | intelligence.py:31 | mix_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | — | none | mixes (persistidos, nominal) | — | mix UI | mix_bridge | crear/editar mix | ProductionMixGateway (stubs) | DEGRADED (ok:True con gateways stub) | S4 (gateways mix) | unknown |
| michi_ai_service | managed_service | inteligencia | `core/assistant_initializer.py` (create_assistant_composition) | michi_ai_service | none | gateways | SvcCont (sí, capability-gated) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite (vía gateways) | files (vía gateways) | HTTP (vía tools) | — | conversación | michi_ai_bridge | michi_ai_bridge | 80 tools (35 reales / 25 stubs / 20 muertas) | none | DEGRADED | S4 | unknown |

### 6.5 Ecosistema (9)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| connection_service | managed_service | integraciones | ecosystem.py:38 | connection_service | none | unknown | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | none | none | LAN (nominal) | — | conexiones | conexiones_bridge | conexiones_bridge | conexiones | none | PRODUCTIVE (nominal) | — | unknown |
| snapcast_control | external_resource | snapcast | ecosystem.py:60 | snapcast_control | none | unknown | SvcCont (NO) | — | — | unknown | none | none | none | JSON-RPC Snapcast | — | — | home_audio | none | control Snapcast | none | UNREACHABLE | S1 | unknown |
| snapserver_manager | process_manager | snapcast | ecosystem.py:49 | snapserver_manager | none | unknown | SvcCont (NO) | tiene start/stop (nunca llamado) | — | unknown | sí (daemon) | none | none | localhost | — | — | home_audio | none | gestionar snapserver | none | UNREACHABLE | S1 | unknown |
| home_audio_service | managed_service | integraciones | ecosystem.py:92 | home_audio_service | none | snapserver_manager, snapcast_control | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | none | none | LAN | — | — | home_audio_bridge | home_audio_bridge | Home Audio | none | PRODUCTIVE (nominal) | — | unknown |
| device_sync_service | managed_service | sync | ecosystem.py:101 | device_sync_service | none | none | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | none | none | TCP (nominal) | — | — | sync UI | sync_bridge | sync móvil | MobileSyncService | PRODUCTIVE (nominal) | S7 | unknown |
| device_registry | registry | sync | ecosystem.py:102 | device_registry | none | none | SvcCont (NO) | — | — | none | none | none | none | none | none | dispositivos | sync | none | registro dispositivos | none | UNREACHABLE | S1 | unknown |
| mobile_sync_service | managed_service | sync | ecosystem.py:109 | mobile_sync_service | none | _db (nunca usado) | SvcCont (NO) | — | — | unknown | none | NONE (db inyectado sin uso) | none | NO escucha puertos (solo attr server_port) | none | `_paired_devices`/`_active_sessions` | sync | none | sync móvil | MichiLinkServer (listener real) | UNREACHABLE | S7 | unknown |
| radio_service | managed_service | radio | ecosystem.py:121 | radio_service | none | event_bus | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite (historial) | — | streams | historial (persistido) | — | radio_bridge | radio_bridge | estaciones + historial | AdvancedRadioService (`core/radio/service.py`), RadioManager (legacy) | DEGRADED (bridge API desalineada) | S5 | unknown |
| lyrics_service | managed_service | lyrics | ecosystem.py:131 | lyrics_service | none | unknown | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | none | none | HTTP (LRCLIB) | — | — | lyrics_bridge (lo elude) | lyrics_bridge | letras | AdvancedLyricsService (`core/lyrics/service.py`), LrcLibClient directo | DEGRADED (producción usa legacy; bridge salva) | S6 | unknown |

### 6.6 Audio Lab (3)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| audio_lab_service | managed_service | audio_lab | audio_lab.py:22 | audio_lab_service | none | unknown | SvcCont (sí, optional) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite | files | none | — | — | audio_lab UI | audio_lab_bridge | diagnóstico/lab | none | PRODUCTIVE | — | unknown |
| diagnostics_service | managed_service | audio_lab | audio_lab.py:29 | diagnostics_service | none | unknown | SvcCont (sí) | SvcCont.start | SvcCont.shutdown | unknown | none | SQLite | files | none | — | — | audio_lab | audio_lab_bridge | diagnóstico | none | PRODUCTIVE (usa JobManager en analyse_directory_job, sin callers) | S2 | unknown |
| cd_ripper_service | managed_service | audio_lab | audio_lab.py:35 | cd_ripper_service | none | unknown | SvcCont (NO) | — | tiene cancel/shutdown (nunca llamado) | unknown | posible (ripping) | none | CD | none | — | — | UI | none | ripping CD | none | UNREACHABLE | S1 | unknown |

### 6.7 Application (1)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| navigation_service | application_service | shell | `core/application_bootstrap.py:89` | navigation_service | none | none | SvcCont (NO) | — | — | none | none | none | none | none | none | navegación | shell/UI | NavigationBridge | rutas/navegación | none | UNREACHABLE (pasivo por uso directo) | S1 (manifest) | unknown |

### 6.8 Standalone (19, no registrados en el contenedor)

| component | classification | canonical_owner | constructed_by | registered_key | deps_declared | deps_injected | lifecycle_owner | starts | shutdowns | threads | subprocesses | db_access | fs_access | net_access | persistent_state | in_memory_state | consumers | bridge | capabilities | duplicate_of | status | migration_action | vertical_test |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| JobBridge | UI_adapter | ui_qml_bridge | job_bridge.py | — | wm, servicios | adapters | bridge (QML) | QML init | — | ThreadPool vía WkMgr | none | none | files (scans) | none | none | `_jobs` cap 200 | scans UI | job_bridge | library_scan/all, metadata_scan, doctor_scan, history_export | DurableJobService / JobManager / AudioLabJobAdapter | PRODUCTIVE (de facto para scans) — DUPLICATE | S2 (migrar a DurableJobService) | unknown |
| JobManager | legacy_component | core/jobs | job_manager.py | — | none | propio JobRepository (job_queue.db, sin DI) | self | directo | directo | none (fallback sync) | none | job_queue.db | — | none | job_queue.db | `_active`/`_handlers` | diagnostics_service (ruta sin callers) | none | jobs con cancelación falsa | DurableJobService / JobBridge / AudioLabJobAdapter | ORPHAN | S2 (retirar) | unknown |
| AudioLabJobAdapter | UI_adapter | core/audio_lab | audio_lab_job_adapter.py | — | WkMgr | wm | self | directo | directo | ThreadPool vía WkMgr | none | none | files | none | none | registro in-memory | AudioLabBridge (que además mantiene su propio `_active_jobs`) | audio_lab_bridge | submit_* sin callers | JobBridge / DurableJobService | ORPHAN | S2 (retirar) | unknown |
| ActionRegistryBinder | factory | ui_qml_bridge | action_registry_binder.py:30 | — | action_registry | ar | bridge (QML) | QML init | — | none | none | none | none | none | none | bindings | widgets/bridges | none | vincula acciones | none | PRODUCTIVE | S3 | unknown |
| SelectionContextBridge | state_store | ui_qml_bridge | selection_context_bridge.py:12 | — | none | none | bridge (QML) | QML init | — | none | none | none | none | none | none | selección | UI | none | contexto selección | none | PRODUCTIVE | S3 | unknown |
| BridgeFactory | factory | ui_qml_bridge | bridge_factory.py:35 | — | servicios | services | bridge (QML) | QML init | — | none | none | none | none | none | none | bridges | shell | none | construye bridges | none | PRODUCTIVE | — | unknown |
| PageStateStore | state_store | ui_qml_bridge | page_state_store.py:8 | — | none | none | bridge (QML) | QML init | — | none | none | none | none | none | none | estado páginas | shell | none | estado de páginas | none | PRODUCTIVE | — | unknown |
| HybridAudioManager | application_service | audio | hybrid_audio_manager.py:52 | — | backends | GStreamerBackend, MpdBackend | PlayerService | con PlayerService | con PlayerService | none | posible (MPD) | none | none | MPD socket | — | backend activo | PlayerService | playback_bridge | backend GStreamer/MPD | none | PRODUCTIVE | — | unknown |
| LibraryMutationService | managed_service | core | library_mutation_service.py (clase) | — (no bound) | — | — | nadie | — | — | unknown | none | SQLite | files | none | — | — | nadie (solo tests) | — | mutación segura librería | MetadataEditorService (bound bajo `library_mutation_service`) | ORPHAN | S3 (bound correcto) | tests unitarios propios |
| ProviderManager | registry | recognition | provider_manager.py:35 | — | proveedores | shazam/audd/acoustid | DetectionService | directo | directo | unknown | none | none | none | HTTP | — | — | DetectionService | — | reconocimiento | none | PRODUCTIVE | — | unknown |
| KnowledgeBrokerService | domain_service | integraciones | integrations/knowledge_broker/service.py:27 | — | unknown | unknown | unknown | unknown | unknown | unknown | none | unknown | unknown | unknown | unknown | unknown | unknown | unknown | conocimiento AI | none | UNVERIFIED | S4 (verificar wiring) | unknown |
| PresentationPreviewProvider | UI_adapter | tools | tools/presentation_preview/provider.py:12 | — | none | none | callers directos | directo | — | none | none | none | none | none | none | adapters demo read-only | Mix/UI demo | none | preview datos demo | none | PRODUCTIVE (tools, read-only) | — | unknown |
| MichiLinkServer | application_service | sync | integrations/michi_link/server.py:35 | — | none | none | sync_server | directo | directo | unknown | none | SQLite (vía servicios) | none | TCP (listener real) | — | sesiones | sync_server | none | servidor sync móvil | MobileSyncService (que no escucha) | PRODUCTIVE | S7 | unknown |
| LrcLibClient | external_resource | lyrics | lyrics/lrclib_client.py:24 | — | none | none | lyrics legacy | directo | — | unknown | none | none | none | HTTP LRCLIB | none | none | lyrics_service legacy, lyrics_bridge:29-30 | lyrics_bridge | cliente LRCLIB | AdvancedProviders (core/lyrics) | PRODUCTIVE (ruta legacy) | S6 | unknown |
| MpdServiceManager | process_manager | audio/mpd | mpd_service_manager.py:28 | — | none | none | MpdBackend | directo | directo | unknown | sí (daemon MPD) | none | none | TCP 6600 | none | estado MPD | MpdBackend | — | gestión daemon MPD | none | PRODUCTIVE | — | unknown |
| GenreStatsService | managed_service | core/genre | (módulo core/genre/) | — | none | unknown | nadie | — | — | unknown | none | SQLite | — | none | none | none | tests | — | estadísticas género | GenresService (genres_service key) | ORPHAN (test-only) | S11 | unknown |
| GenreMixService | managed_service | core/genre | (módulo core/genre/) | — | none | unknown | nadie | — | — | unknown | none | SQLite | — | none | none | none | tests | — | mixes por género | MixService (parcial) | ORPHAN (test-only) | S11 | unknown |
| GenreCleanupService | managed_service | core/genre | (módulo core/genre/) | — | none | unknown | nadie | — | — | unknown | none | SQLite | — | none | none | none | tests | — | limpieza géneros | none | ORPHAN (test-only) | S11 | unknown |
| PlayerBarService | managed_service | core | player_bar_service.py:9 | — (NO registrado) | none | player (injectable) | nadie | — | — | none | none | none | none | none | none | defaults inventados (volume 75, stopped, 0.0) | player bar UI | none | estado player bar | playback_service (fuente real) | ORPHAN / DEGRADED (defaults falsos) | S9 | unknown |
| MetadataEditorService | managed_service | core | metadata_editor_service.py | (bajo `library_mutation_service`) | none | db | SvcCont (sí, vía key ajena) | SvcCont.start | SvcCont.shutdown | none | none | SQLite | files | none | none | none | metadata_bridge | metadata_bridge | edición metadatos | LibraryMutationService (clase canónica no bound) | CONTRACT_MISMATCH (clave equivocada) | S3 | unknown |

---

## 7. Contratos rotos

| Contrato | Dónde | Síntoma | Gravedad |
|---|---|---|---|
| `DurableJobService.create/get/update` | `ui_qml_bridge/metadata_bridge.py:445-492` | Métodos NO EXISTEN en `core/jobs/job_service.py` → `AttributeError` si `_js` presente; el flujo se enmascara porque `_js` suele ser None | ALTA (explotaría en cuanto se inyecte job_service) |
| `DurableJobService.cancel_all(owner=...)` | `ui_qml_bridge/mix_bridge.py:310-312` | `cancel_all()` NO acepta `owner` → `TypeError` tragado por `suppress` (cancelación nunca ocurre) | ALTA (fallo silencioso) |
| `DurableJobService.cancel_job` | `ui_qml_bridge/michi_ai_bridge.py:266` | Método inexistente → código muerto (nunca disparado) | MEDIA (dead code) |
| API de RadioService vs expectativas del bridge | `ui_qml_bridge/radio_bridge.py` (duck-type `get_all/add/update`) | El bridge duck-typea una API inexistente; el RadioService real expone `get_stations/add_station/edit_station/favorite_station/delete_station` → CRUD silenciosamente `NOT_IMPLEMENTED` | ALTA (funcionalidad muda) |
| `self._radio_svc` en removeStation | `ui_qml_bridge/radio_bridge.py` | Atributo nunca asignado → `AttributeError` en remover estación | ALTA (crash) |
| `process_message` honestidad | `core/ai_engine.py:134-145` | Devuelve `"ok": True` aunque la tool haya fallado | ALTA (mentira en el contrato de resultado) |
| `load_sidecar` lectura | `core/lyrics/service.py:96-99` | Llama a `self._storage.save_sidecar` (ESCRIBE doc vacío) en vez de leer | ALTA (corrupción de datos; clase huérfana hoy) |
| Gateway mappings de Michi AI | `michi_ai/v2/tools/register_builtin.py` (`getattr(gateways, "playlist"/"device")`) | `AssistantGateways` expone `playlists`/`devices` → 20 tools devuelven CAPABILITY_UNAVAILABLE incondicional | ALTA (20 tools muertas) |
| Mappings tool→método equivocado | `register_builtin.py` L123/128/145/146/148-149/150-151/158/170 | draft_playlist→list_playlists, delete_playlist→create_playlist, apply_library_repair→list_recent, inspect_metadata→get_track (solo id/title/artist), suggest_metadata_changes→find_metadata_gaps (siempre `gaps:[]`), scan_library_health→diagnostics.get_diagnostics estático "operational", restore_setting→suggest_change stub, get_sync_status→device.diagnose_ecosystem | ALTA (herramientas hacen otra cosa) |
| `health()` de PlayerBarService | `core/player_bar_service.py` | `{available: player is not None}` + defaults inventados volume=75/state stopped/position 0.0 cuando no hay player | MEDIA (datos falsos en UI) |
| `CapabilityResolver.register_from_gateways` | `michi_ai/v2/intent/capability_resolver.py` | Marca disponible si el OBJETO gateway existe, no si sus métodos funcionan | MEDIA (capacidades ilusorias) |
| `reset_all()` | `core/settings_service.py:76` | Sin transacción; `{"ok": not errors, "errors": errors}` semántica parcial | MEDIA |
| `search_async()` | `core/global_search_service.py:114` | QTimer.singleShot(0) = pseudo-async en UI thread; errores FTS tragados; acciones sobre selección global, no sobre el resultado explícito | MEDIA |
| `start_job()` | `core/jobs/job_service.py:152` | Ejecuta el handler inline (síncrono) en el thread del caller | ALTA (bloqueo UI si se usa) |
| Recuperación de restart | `core/jobs/job_service.py` | RUNNING→INTERRUPTED; QUEUED nunca se re-enquea | MEDIA (jobs perdidos) |
| Bridge construyendo servicios | `playlists_bridge.py:46-51`, `history_bridge.py:34`, `job_bridge.py:148-163`, `library_doctor_bridge.py:135,315`, `lyrics_bridge.py:29-30` | Bridges crean servicios/repos como fallback → bypass de la composición y del DI | MEDIA (violación de arquitectura) |
| SQL directo en bridge | `ui_qml_bridge/library_bridge.py:639-756` | INSERT/DELETE/SELECT a `self._db.conn` (favorites bulk + `_tracks_for_bulk`) | MEDIA (violación de capas) |

---

## 8. Duplicidades

| Dominio | Clases duplicadas | Archivos | Autoridad elegida |
|---|---|---|---|
| Jobs | DurableJobService / JobBridge / JobManager / AudioLabJobAdapter | `core/jobs/job_service.py` · `ui_qml_bridge/job_bridge.py` · `core/jobs/job_manager.py` · `core/audio_lab/audio_lab_job_adapter.py` | **DurableJobService** (persistido, con estado; S2 le agrega handlers y async) |
| Radio | RadioService (prod) / AdvancedService / RadioManager (legacy) | `core/radio/radio_service.py` · `core/radio/service.py` · `streaming/radio_manager.py` | **`core/radio/service.py`** (advanced: sessions, stream_probe, reconnect) — S5 |
| Lyrics | LyricsService legacy (+ LrcLibClient) / AdvancedLyricsService (+ lyrics_storage_service) | `core/lyrics_service.py` + `lyrics/lrclib_client.py` · `core/lyrics/service.py` + `core/lyrics/lyrics_storage_service.py` | **`core/lyrics/service.py`** (resolver/registry/providers/cache/editor/timeline/undo/attribution) — S6 (previa fix de load_sidecar) |
| Michi Link | MicroServerService ×3 · ContinueOnServerService ×2 | `core/micro_server_service.py` (urllib) · `integrations/micro_server_service.py` (requests) · `integrations/michi_link/micro_server_client.py` + `import_client.py` + `continue_on_server_service.py` (stub 26 líneas, importado en ningún lado) | **`integrations/michi_link/services/`** (~1750 líneas) — S7 |
| Sync móvil | MobileSyncService (no escucha) / MichiLinkServer (listener real) | `core/mobile_sync_service.py` · `integrations/michi_link/server.py` (importado por `sync/sync_server.py`) | **MichiLinkServer** + servicios advanced — S7 |
| Metadata | MetadataEditorService / LibraryMutationService | `core/metadata_editor_service.py` · `core/library_mutation_service.py` | **LibraryMutationService** — S3 |
| Historial radio | `RadioService.get_history` persistido / `_history` in-memory (cap 50) del bridge | `core/radio/radio_service.py` · `ui_qml_bridge/radio_bridge.py` | **RadioService** (persistido) — S5 |
| Jobs en Audio Lab | AudioLabJobAdapter / `_active_jobs` de AudioLabBridge | `core/audio_lab/audio_lab_job_adapter.py` · `ui_qml_bridge/audio_lab_bridge.py` | **JobBridge→DurableJobService** (S2) |
| Géneros | GenresService (prod) / GenreStatsService·GenreMixService·GenreCleanupService | `core/...` (library.py:97) · `core/genre/` | Decisión S11 (exponer o retirar) |
| Carátulas | CoverArtService (key `artwork_service`) / metadata enrichments | `core/...` (library.py:76) | key canónica `artwork_service` — S1 |

---

## 9. Bugs concretos confirmados

| # | Archivo:línea | Descripción |
|---|---|---|
| 1 | `ui_qml_bridge/metadata_bridge.py:445-492` | Llama `job_service.create/get/update` — no existen en DurableJobService → AttributeError |
| 2 | `ui_qml_bridge/mix_bridge.py:310-312` | `cancel_all(owner="mix_bridge")` — DurableJobService.cancel_all() no acepta owner → TypeError suprimido |
| 3 | `ui_qml_bridge/michi_ai_bridge.py:266` | `cancel_job(self._current_task_id)` — método inexistente (dead code) |
| 4 | `core/lyrics/service.py:96-99` | `load_sidecar()` llama `self._storage.save_sidecar(...)` → ESCRIBE documento vacío en lugar de leer |
| 5 | `ui_qml_bridge/radio_bridge.py` (removeStation) | Referencia `self._radio_svc`, atributo nunca asignado → AttributeError |
| 6 | `ui_qml_bridge/radio_bridge.py:331-332` | `_is_playing = True` ANTES de confirmar conexión; hook `_on_station_connection_done` nunca conectado |
| 7 | `ui_qml_bridge/radio_bridge.py` (CRUD) | Duck-type `get_all/add/update` vs API real `get_stations/add_station/edit_station/favorite_station/delete_station` → NOT_IMPLEMENTED silencioso |
| 8 | `michi_ai/v2/tools/register_builtin.py` | `getattr(gateways, "playlist")`/`"device"` — AssistantGateways expone `playlists`/`devices` → 20 tools CAPABILITY_UNAVAILABLE |
| 9 | `register_builtin.py:123` | `draft_playlist` → `("playlist", "list_playlists")` (método equivocado) |
| 10 | `register_builtin.py:128` | `delete_playlist` → `("playlist", "create_playlist")` |
| 11 | `register_builtin.py:145` | `inspect_metadata` → `("library", "get_track")` (solo id/title/artist) |
| 12 | `register_builtin.py:146` | `suggest_metadata_changes` → `find_metadata_gaps` (siempre `gaps:[]`) |
| 13 | `register_builtin.py:148-149` | `scan_library_health`/`preview_library_repair` → `diagnostics.get_diagnostics` estático "operational" |
| 14 | `register_builtin.py:150-151` | `apply_library_repair`/`rollback_library_repair` → `("library", "list_recent")` |
| 15 | `register_builtin.py:158` | `get_sync_status` → `device.diagnose_ecosystem` |
| 16 | `register_builtin.py:170` | `restore_setting` → `settings.suggest_change` (stub) |
| 17 | `core/ai_engine.py:134-145` | `process_message` devuelve `ok:True` incluso cuando la tool falla |
| 18 | `core/jobs/job_service.py:152` | `start_job` ejecuta `_execute_handler` inline (síncrono, thread del caller) |
| 19 | `core/jobs/job_service.py` (restart) | Recuperación solo flipea RUNNING→INTERRUPTED; QUEUED nunca re-enqueado |
| 20 | `core/mobile_sync_service.py` | `_db` inyectado nunca usado; no escucha puerto (solo attr `server_port`); QR devuelve `""` si qrcode no instalado |
| 21 | `core/global_search_service.py:114` | `search_async` con QTimer.singleShot(0) = pseudo-async en UI thread; errores FTS tragados |
| 22 | `core/player_bar_service.py` | Defaults inventados (volume=75, state='stopped', position=0.0) cuando player no disponible; `health()` solo `{available: player is not None}` |
| 23 | `core/settings_service.py:76` | `reset_all` per-key sin transacción, semántica `{ok, errors}` parcial |
| 24 | `ui_qml_bridge/library_bridge.py:639-756` | SQL directo (INSERT/DELETE/SELECT) en el bridge — violación de capas (favorites bulk) |
| 25 | `ui_qml_bridge/lyrics_bridge.py:29-30` | Construye su propio LrcLibClient; guarda vía módulo-level `core/lyrics/lyrics_storage_service.py:5` — elude lyrics_service |
| 26 | `core/composition/library.py:38` | Clave `library_mutation_service` ligada a `MetadataEditorService`, no a `LibraryMutationService` |
| 27 | `core/worker_manager.py:197` | Escritura de `_callbacks` fuera del lock (1 punto; thread-safety incompleta) |
| 28 | `core/radio/radio_service.py` + bridge | Historial duplicado: persistido en servicio vs `_history` in-memory (cap 50) en bridge |

---

## 10. Riesgos y decisiones

### Riesgos

| Riesgo | Detalle | Mitigación |
|---|---|---|
| Migración de jobs (S2) | JobBridge es lo que las pantallas de scan usan HOY (library_scan, library_scan_all, metadata_scan, doctor_scan, history_export). Mover a DurableJobService sin romper esos flujos es delicado: DurableJobService hoy tiene 0 handlers, ejecución síncrona y recuperación incompleta. | S2 en dos pasos: (a) handlers reales + ejecución async + recovery en DurableJobService con tests; (b) JobBridge pasa a ser adaptador fino sobre DurableJobService. Nunca al revés. |
| Migración radio (S5) | `core/radio/service.py` (advanced) nunca corrió en producción; sesiones/stream_probe/reconnect son código no probado en vivo. | Primero fix de los bugs del bridge (removeStation, _is_playing, CRUD), después migración con feature flag. |
| Migración lyrics (S6) | `core/lyrics/service.py` tiene bug confirmado (`load_sidecar` escribe). El bridge hoy salva vía módulo-level `lyrics_storage_service`. | Fix de `load_sidecar` ANTES de migrar; tests de regresión de sidecar como gate. |
| PR #184 | Diff superseded por main; integrarlo reintroduciría código viejo de mix. | NO integrar. Marcado como superseded. |
| PR #185 | Aislamiento de tests; fuera de alcance de esta ola. | Dejar abierto; no bloquear slices. |
| Suite de tests pre-existente | Baseline: 3752 passed, 3 failed, 13 errors (perf FTS requiere DB real 10k/50k; `test_player_service_apply_profile` flaky por polución; perf `_qt_app` fixture ausente). | No es regresión de esta ola; los slices deben dejar la suite AL MENOS en baseline. Ningún slice puede empeorarlo. |
| `list_services` incompleto | Muestra solo 37 de 61; diagnósticos futuros usarán datos falsos. | S1: manifest como única fuente; `list_services` pasa a derivar del manifest. |
| Servicios con lifecycle fantasma | `recognition_service`, `snapserver_manager`, `cd_ripper_service`, `library_service` tienen start/shutdown que NADIE llama. | S1: el manifest declara lifecycle_owner explícito; los que deban iniciarse se cablean, los demás se marcan. |

### Decisiones tomadas en esta auditoría

1. **Autoridad de jobs → DurableJobService** (persistido, con máquina de estados); JobManager y AudioLabJobAdapter se retiran; JobBridge queda como adaptador.
2. **Autoridad de radio → `core/radio/service.py`** (advanced); `streaming/radio_manager.py` legacy se retira tras S5.
3. **Autoridad de lyrics → `core/lyrics/service.py`** (advanced) previa corrección de `load_sidecar`.
4. **Autoridad de Michi Link → `integrations/michi_link/services/`**; las 2 variantes legacy (`core/micro_server_service.py`, `integrations/micro_server_service.py`) se retiran; `integrations/michi_link/continue_on_server_service.py` (stub importado en ningún lado) se elimina.
5. **Clave `library_mutation_service` → LibraryMutationService** (S3); MetadataEditorService se re-registra bajo su propia clave si hace falta.
6. **SQL fuera de bridges** (S3): library_bridge migra a servicios.
7. **Primera ola = S1..S4** (manifest, jobs, mutation+action context, Michi AI) — los puntos de mayor riesgo operativo.
8. **No inventar estado de servicios**: cualquier duda pendiente se documenta como `unknown` en el catastro.

---

## 11. Plan de migración por slices

> Primera ola: **S1, S2, S3, S4**. Cada slice es un cambio autocontenido con entregable, criterios de aceptación y tests.

### S1 — Service Manifest
- **Entregables**: `core/service_manifest.py` (inventario canónico de las 61 claves + standalone: clasificación, lifecycle_owner, constructed_by, estado); validador manifest↔composición; `list_services()` derivado del manifest; tests/architecture/ (base).
- **Criterios**: manifest coincide con las 61 claves registradas; validación en CI (test de arquitectura); ruff 0; suite en baseline.

### S2 — Unificación de jobs
- **Entregables**: handlers reales en DurableJobService (library_scan, library_scan_all, metadata_scan, doctor_scan, history_export); ejecución async (ThreadPoolExecutor) fuera del thread del caller; recovery de restart con re-enqueue de QUEUED; JobBridge como adaptador sobre DurableJobService; fix de `metadata_bridge.py:445-492`, `mix_bridge.py:310-312`, `michi_ai_bridge.py:266`; retiro de JobManager y AudioLabJobAdapter; lock de `_callbacks` en WorkerManager.
- **Criterios**: flujos de scan de producción pasan con la misma API observable; cancelación real funciona; tests de jobs nuevos (async, recovery, cancel); suite en baseline.

### S3 — Mutation + Action Context
- **Entregables**: `library_mutation_service` bound a `LibraryMutationService`; acciones con contexto de selección explícito (SelectionContextBridge + ActionRegistry); SQL de `library_bridge.py:639-756` migrado a servicios; eliminación de construcción de servicios en bridges (playlists, history, library_doctor, lyrics).
- **Criterios**: edición de metadatos vía servicio real; favoritos sin SQL en bridge; test de arquitectura "no SQL en bridges" y "no service construction en bridges".

### S4 — Michi AI
- **Entregables**: fix de `register_builtin.py` (mapeos `playlists`/`devices` y L123/128/145/146/148-149/150-151/158/170); CapabilityResolver por salud de método (no por existencia de objeto); `process_message` con resultado honesto (`ok:False` si la tool falla); decisión revive/retira de las 20 tools muertas; verificación de wiring de KnowledgeBrokerService.
- **Criterios**: 80 tools con mappings correctos; tools de playlists/device dejan de devolver CAPABILITY_UNAVAILABLE incondicional; tests de herramientas con gateways mock; suite en baseline.

### S5 — Radio
- **Entregables**: fix `removeStation` (AttributeError), fix `_is_playing` prematuro (conectar `_on_station_connection_done`), CRUD alineado a la API real de RadioService; migración a `core/radio/service.py`; retiro de `streaming/radio_manager.py`; historial único persistido.
- **Criterios**: remover/editar/favorito de estaciones funcionando; historial persistido sin duplicado en memoria; tests de radio_bridge con RadioService mock.

### S6 — Lyrics
- **Entregables**: fix `load_sidecar` (`core/lyrics/service.py:96-99` — leer, no escribir); migración de producción a `core/lyrics/service.py`; `lyrics_bridge` vía servicio (sin LrcLibClient propio ni storage módulo-level).
- **Criterios**: sidecar lee correctamente; letras vía resolver/providers/cache; test de regresión de sidecar.

### S7 — Mobile Sync + Michi Link
- **Entregables**: consolidación de los 3 stacks en `integrations/michi_link/services/`; `mobile_sync_service` real (usa `_db`, delega listener en MichiLinkServer) o retirado en favor de `device_sync_service`; eliminación de `core/micro_server_service.py`, `integrations/micro_server_service.py`, stub `continue_on_server_service.py`.
- **Criterios**: una sola clase `MicroServerService`; sync móvil funcional vía server real; QR con fallback visible si falta qrcode.

### S8 — Global Search
- **Entregables**: `search_async` fuera del UI thread (WorkerManager/ThreadPool); errores FTS visibles (event_bus/log); acciones sobre referencias explícitas de resultado.
- **Criterios**: búsqueda no bloquea UI; errores FTS reportados; tests de búsqueda async.

### S9 — Player Bar
- **Entregables**: `PlayerBarService` registrado en composición; defaults derivados del estado real de `playback_service`; `health()` honesto.
- **Criterios**: sin valores inventados; test de estado sin player.

### S10 — Settings
- **Entregables**: `reset_all` transaccional; semántica clara de error; coordinación con SettingsRuntimeCoordinator.
- **Criterios**: reset atómico (o rollback documentado); tests de reset.

### S11 — Géneros
- **Entregables**: decisión documentada: exponer GenreStatsService/GenreMixService/GenreCleanupService vía composición/bridge o retirarlos.
- **Criterios**: sin ORPHAN test-only; test de arquitectura de cobertura.

### S12 — Tests de arquitectura
- **Entregables**: `tests/architecture/` con reglas: manifest↔composición, no SQL en bridges, no construcción de servicios en bridges, no componentes no manifestados, claves trackeadas == manifest.
- **Criterios**: suite de arquitectura verde; integrada al pipeline.

### S13 — Limpieza
- **Entregables**: eliminación de `core/dependency_graph.py`, `core/metadata_init.py`, servicios retirados en S2/S5/S6/S7, código test-only no decidido en S11.
- **Criterios**: 0 huérfanos; 0 duplicados; suite verde.

---

## 12. Criterios de aceptación

Estado global: **PENDIENTE** (ninguno implementado aún). Numeración continúa desde el master prompt (26–55).

| # | Criterio | Estado |
|---|---|---|
| 26 | `core/service_manifest.py` existe y lista las 61 claves registradas + componentes standalone con clasificación | PENDIENTE |
| 27 | Toda clave registrada tiene entrada de lifecycle en el manifest (lifecycle_owner, starts, shutdowns) | PENDIENTE |
| 28 | `start()`/`shutdown()`/`cancel_all()` iteran solo componentes manifest-trackeados (o el manifest es la única fuente de verdad) | PENDIENTE |
| 29 | `list_services()` refleja el manifest completo (no solo 37 de 61) | PENDIENTE |
| 30 | Existe UNA autoridad de jobs (DurableJobService); JobManager y AudioLabJobAdapter retirados | PENDIENTE |
| 31 | `metadata_bridge` usa la API real de job_service (create/get/update existentes o llamadas corregidas) | PENDIENTE |
| 32 | `mix_bridge.cancel_all(owner=...)` funciona (firma corregida o API correcta) | PENDIENTE |
| 33 | `michi_ai_bridge` cancelación de tarea funciona (sin método fantasma) | PENDIENTE |
| 34 | `DurableJobService.start_job` no bloquea el thread del caller (async documentado) | PENDIENTE |
| 35 | Recovery de restart re-enquea jobs QUEUED (no solo RUNNING→INTERRUPTED) | PENDIENTE |
| 36 | Clave `library_mutation_service` bound a `LibraryMutationService` real | PENDIENTE |
| 37 | Cero SQL directo en bridges (library_bridge migrado) | PENDIENTE |
| 38 | Cero construcción de servicios/repos en bridges como fallback | PENDIENTE |
| 39 | `radio_bridge.removeStation` sin AttributeError | PENDIENTE |
| 40 | Estado de reproducción de radio solo se marca tras conexión confirmada (`_on_station_connection_done` conectado) | PENDIENTE |
| 41 | `load_sidecar` de `core/lyrics/service.py` LEE en vez de escribir | PENDIENTE |
| 42 | Una sola pila de lyrics en producción (`core/lyrics/service.py`) | PENDIENTE |
| 43 | Las 80 tools de Michi AI tienen mappings correctos (playlists/devices y L123/128/145/146/148-149/150-151/158/170 corregidos) | PENDIENTE |
| 44 | CapabilityResolver evalúa salud de métodos, no existencia de objeto gateway | PENDIENTE |
| 45 | `process_message` devuelve resultado honesto (`ok:False` si la tool falla) | PENDIENTE |
| 46 | `mobile_sync_service` usa `_db` y/o delega el listener real (MichiLinkServer); QR sin qrcode es explícito | PENDIENTE |
| 47 | Una sola pila de Michi Link (`integrations/michi_link/services/`); 2 legacy retirados; stub `continue_on_server_service.py` eliminado | PENDIENTE |
| 48 | `global_search_service.search_async` no corre en UI thread; errores FTS visibles | PENDIENTE |
| 49 | `PlayerBarService` sin defaults inventados (deriva de playback_service) y registrado en composición | PENDIENTE |
| 50 | `settings_service.reset_all` transaccional (o rollback documentado) | PENDIENTE |
| 51 | Servicios de género avanzados expuestos o retirados (sin ORPHAN test-only) | PENDIENTE |
| 52 | `core/dependency_graph.py` eliminado | PENDIENTE |
| 53 | `core/metadata_init.py` eliminado | PENDIENTE |
| 54 | `tests/architecture/` en CI (manifest↔composición, sin SQL/construcción en bridges, componentes manifestados) | PENDIENTE |
| 55 | Suite completa: baseline 3752 passed mantenido; 3 failed + 13 errors pre-existentes documentados y en curso de resolución sin regresión | PENDIENTE |
