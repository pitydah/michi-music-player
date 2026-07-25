# CORE CONTRACT FREEZE — Michi Music Player

**SHA:** `9fb25a7c90b213921632fd426ce5fbdf0ccb6ef4`
**Branch:** `michi-core-convergence`
**Date:** 2026-07-14
**Status:** FROZEN — no structural changes without review

---

## Frozen Interfaces

### Service Names (full list)
Required: connection_factory, worker_manager, query_executor, job_service, event_bus, settings_coordinator, settings_service, library_query_service, library_sources_service, library_mutation_service, playlist_service, history_query_service, global_search_service, mix_query_service, track_action_service, playback_service, queue_service, metadata_service

Optional: theme_service, accessibility_service, audio_lab_service, smart_tagging_service, library_doctor_service, device_sync_service, connection_service, home_audio_service, diagnostics_service, notification_service, action_registry

### Constructor Signatures
ServiceContainer.register(name, service, required=None, dependencies=()) — frozen
ApplicationBootstrap.build().start().create_bridges().register_context(engine).load_qml(engine) — frozen
AppBridge.shutdown() — idempotent 14+ step execution — frozen
JobService.submit/cancel/status/list_active/list_by_type — frozen

### Context Registration API
ContextRegistrar.register(name, obj) with duplicate-type-warning — frozen
QML_CONTEXT_BINDINGS dict maps qml_name → bridge_key — frozen

### Launcher Names
michi.app_launcher, michi.qml_app, michi.widgets_app, michi.verify_app — frozen

### Protocols (core/protocols/)
JobServiceProtocol, ActionRegistryProtocol, ConfirmationServiceProtocol, NavigationProtocol,
PlaybackServiceProtocol, QueueServiceProtocol, DeviceSyncServiceProtocol, AudioLabServiceProtocol,
MixServiceProtocol, GlobalSearchServiceProtocol, NotificationServiceProtocol, MichiAIServiceProtocol — frozen

### OperationResult (core/result.py)
OperationResult(ok, code, message, data, warnings, partial, retryable).to_dict(), .from_legacy_dict() — frozen

## Documented Incompatibilities
- AppBridge.shutdown is now idempotent with 14+ tracked steps (was simple iteration)
- core/result.py OperationResult added; legacy core/results.py OperationResult retained for backwards compat
- core/protocols/ added; existing core/interfaces.py ABCs retained
- QueueService now exclusively owns queue content, index, navigation, repeat,
  shuffle, backend progression reconciliation, and session restoration.
- PlayerService remains the transport/audio facade and backend synchronization
  adapter; production ingress must not call its legacy queue methods directly.

---

## 1. Launcher Ownership

| Module | File | Responsibility |
|---|---|---|
| `michi.app_launcher` | `michi/app_launcher.py` | Reads `MICHI_UI` env var, dispatches to QML. Single entry point. |
| `michi.qml_app` | `michi/qml_app.py` | Owns `QGuiApplication` lifecycle for QML mode. |
| `michi.verify_app` | `michi/verify_app.py` | Verification harness (exit-code based). |

**Rule:** Only `app_launcher.launch()` decides the UI mode. No other code reads `MICHI_UI`.

---

## 2. ApplicationBootstrap Responsibility

**File:** `core/application_bootstrap.py`

Single productive startup sequence for QML application. Orchestrates in order:

1. Infrastructure composition registers settings, persistence, database, and workers.
2. Playback composition registers PlayerService and QueueService.
3. Library, Audio Lab, ecosystem, and settings compositions register their domains.
4. Intelligence composition registers the action registry and Michi AI gateways.
5. `container.start()` transitions services to READY/DEGRADED.
6. `QueueService.restore()` restores the canonical session without autoplay.
7. `create_bridges()` creates observers after queue restoration.
8. `register_context()` publishes bridge instances through `QML_CONTEXT_BINDINGS`.

**Rule:** Bootstrap does NOT create windows, QML engines, or Qt event loops. It only populates the container. The caller (`michi.qml_app` or `main.py`) owns the Qt event loop and engine.

---

## 3. ServiceContainer Responsibility

**File:** `core/service_container.py` (class `ServiceRegistry`)

Typed service registry with lifecycle and capability tracking.

- **Registration:** `register(name, service)` — stores reference
- **Retrieval:** `get(name)` — returns reference or `None`
- **Priority classification:** REQUIRED, OPTIONAL, DEFERRED (defined in `_required_names()`, `_optional_names()`, `_deferred_names()`)
- **Capability:** `is_capable(name)` — `False` if required service is missing/failed
- **Health:** `health()` — state + service count + failures
- **Lifecycle:** `start()` → READY/DEGRADED; `shutdown()` → STOPPING → STOPPED
- **Failure reporting:** `report_failure(name, error)` — logs ERROR for REQUIRED services

**Required services:** connection_factory, worker_manager, query_executor, job_service, event_bus, settings_coordinator, settings_service, library_query_service, library_sources_service, library_mutation_service, playlist_service, history_query_service, global_search_service, mix_query_service, track_action_service, playback_service, queue_service, metadata_service

**Contract:** Container NEVER creates services itself (except `ensure_device_sync_service` as lazy fallback). All services must be registered before `start()`.

---

## 4. BridgeFactory Responsibility

**File:** `ui_qml_bridge/bridge_factory.py`

Creates bridge objects exactly once. Does NOT open databases, construct backends, or start services.

- Receives `ServiceBundle` (extracted from `ServiceContainer`)
- Creates bridges in 5 phases:
  - **Phase 0:** Settings migrations
  - **Phase B:** Fundamental bridges (navigation, app, theme, notification, accessibility, app_state, route_registry, action_registry, capability, playlists, selection_context, job)
  - **Phase C:** Domain bridges (library, playback, nowplaying, queue, history, mix, lyrics, global_search, settings, output_profiles, eq, connections, home_audio, devices, radio, library_sources, home)
  - **Phase D:** Advanced tools (audio_lab, metadata, smart_tagging, disc_lab, library_doctor, michi_ai, diagnostics, runtime_quality, physical_audio, command_palette, cover_provider, desktop, page_state)
  - **Phase E:** Wiring assertions (`_assert_wiring`) + action handler binding
- Capability tracking: `_capabilities[bridge_name]` = all required services exist

**Rule:** Bridges never import core services directly. All dependencies injected via `ServiceBundle`.

---

## 5. ContextRegistrar Responsibility

**File:** `ui_qml_bridge/context_registrar.py`

Registers QML context properties on `QQmlApplicationEngine`. Detects duplicate registrations with type mismatch.

- `register(name, obj)` — sets `engine.rootContext().setContextProperty(name, obj)`
- Duplicate detection: logs warning if same name re-registered with different type
- `audit()` returns total count, names, and duplicates list

**Rule:** Only `ApplicationBootstrap._register_contexts()` and the QML app runner call `ContextRegistrar`. Bridges do NOT register themselves.

---

## 6. JobService Responsibility

**File:** `core/job_service.py`

Thread-safe job tracker for background operations (device sync, etc.).

- `create(kind, meta)` → returns `Job` with unique ID
- `update(job_id, status, progress, error)` → mutable lifecycle
- `cancel(job_id)` → sets CANCELLED
- Event callbacks via `on(event, cb)` / `off(event, cb)`
- Status enum: `JobStatus(QUEUED, RUNNING, COMPLETED, FAILED, CANCELLED)`

**Note:** A second `JobStatus` enum exists in `core/jobs/job_types.py` with different values (`PENDING, RUNNING, PAUSED, COMPLETED, FAILED, CANCELLED`). These are separate systems (legacy tracker vs unified job system) and are NOT reconciled.

---

## 7. ProcessController Responsibility

**File:** `core/process_controller.py`

Async controller for external processes (FFmpeg, FFprobe, integrity checks, Disc Lab). Thread-safe, never blocks UI thread.

- `start(cmd, args, cwd, env)` → launches async subprocess, returns `ManagedProcess`
- `terminate(pid)` / `kill(pid)` / `timeout(pid, seconds)` — lifecycle control
- `cleanup(pid)` — kills and removes from tracking
- Stderr collection via background asyncio task

**Rule:** No `subprocess.run()` in Qt slots or QML slots. Always go through `ProcessController`.

---

## 8. RuntimePersistence Responsibility

**File:** `core/runtime_persistence.py`

Atomic, crash-safe JSON persistence for runtime state. 7 domains:

| Domain | Data Class | File |
|---|---|---|
| queue | Canonical QueueService snapshot dict | `queue_state.json` |
| page_state | `PersistedPageState` | `page_state.json` |
| jobs | `PersistedJob` | `jobs.json` |
| notifications | `PersistedNotification` | `notifications.json` |
| connection_profiles | `ConnectionProfileData` | `connection_profiles.json` |
| device_profiles | `DeviceProfileData` | `device_profiles.json` |
| audio_lab_profiles | `AudioLabProfileData` | `audio_lab_profiles.json` |

**Write strategy:** temp → fsync → atomic rename. Never writes partially.
**Schema versioning:** `_migrate()` / `_rollback()` with per-version migrators in `_MIGRATORS` / `_ROLLBACKS`.

The queue snapshot preserves effective item order, current index, repeat,
shuffle, stable entry tokens, original pre-shuffle token order, context, and
revision. Stable tokens preserve duplicate entries. Bootstrap restores it after
service startup and before bridge creation; synchronization never autoplays.

---

## 8.1 Queue Authority

**File:** `core/queue_service.py`

- All queue mutations are transactional and roll back domain/backend state on
  synchronization failure.
- Backend progression is accepted only when index, filepath, and revision match
  the canonical state.
- Repeat and shuffle are domain state, not backend-owned state.
- Queue observers receive canonical snapshots from QueueService directly.
- PlayerService owns pause, resume, stop, seek, volume, and backend execution.
- Physical queue implementation is restricted to PlayerService and
  `audio/backends/`.
- The dependency edge is `queue_service -> playback_service`; the reverse edge
  is forbidden.
- `tests/test_queue_ingress_architecture.py` rejects new production bypasses.

---

## 9. Shutdown Order

**File:** `core/shutdown_manager.py`

Reverse-registration-order execution. `ShutdownManager` holds a list of `(name, stop_fn)` tuples.

1. `register(name, stop_fn)` — appends to list
2. `shutdown()` — iterates in **reverse** order, calling each `stop_fn`
3. Errors are logged, never re-raised

**Actual order depends on registration order in callers.** Known stop/shutdown methods by component:

| Component | Method |
|---|---|
| `ServiceContainer` | `shutdown()` — clears failures, sets STOPPED |
| `WorkerManager` | `shutdown(timeout_ms=2000)` |
| `QueryExecutor` | `shutdown(timeout_ms=2000)` |
| `JobService` | `shutdown()` |
| `QueueService` | `shutdown()` |
| `QueueBridge` | `shutdown()` |
| `ConfirmationService` | `shutdown()` |
| `LyricsService` | `shutdown()` |
| `RadioService` | `stop()` |
| `RadioSession` | `stop()` |
| `PeriodicAnalyzer` | `stop()` |
| `ConnectionFactory` | `close_all()` |
| `ProcessController` | `cleanup(pid)` (per process) |
| `DiagnosticsService` | `close()` |
| `ContextRepository` | `close()` |
| `JobPersistence` | `close()` |

**Rule:** Bridges shutdown first (disconnect QML), then domain services (flush queues), then repositories (close DB), then worker pool (drain & join).

---

## 10. Thread Ownership

| Thread | Owned By | Purpose |
|---|---|---|
| Main (Qt) | `QGuiApplication` | UI loop, signals, QML engine |
| Worker pool | `WorkerManager` (`core/worker_manager.py`) | CPU-bound tasks (scanning, metadata extraction) |
| DB thread | `QThread` / `ThreadPoolExecutor` (via `QueryExecutor`) | SQLite reads/writes (WAL mode) |
| Async I/O | `asyncio` event loop | `ProcessController` subprocess management |
| Audio pipeline | GStreamer internal threads | Audio decode, playback, DSP |
| MPD service | Managed by `mpd_service_manager.py` | External MPD daemon lifecycle |

---

## 11. Database Ownership

**File:** `core/library_db.py` / `core/connection_factory.py`

- **Single writer:** SQLite WAL mode allows concurrent reads, single writer
- **Connection factory:** `ConnectionFactory` (`core/connection_factory.py`) provides connection references
- **Reader access:** Multiple services read via `connection_factory.get_connection()`
- **Write access:** Only through repositories (`TrackRepository`, `AlbumRepository`, `ArtistRepository`, etc.)
- **Migrations:** `core/settings_migrations.py:migrate_all()` runs at startup before any service

**Rule:** No raw SQL outside repository classes. No direct `sqlite3.connect()` bypassing `connection_factory`.

---

## 12. QObject Ownership

- **Bridges** (`BridgeFactory`, each bridge instance): created once, owned by `BridgeFactory._bridges` dict
- **Context properties** (`ContextRegistrar`): references only, ownership retained by `BridgeFactory`
- **QML engine** (`QQmlApplicationEngine`): owned by the QML app runner (`michi.qml_app`)
- **Signal connections:** Bridges emit signals. QML engine connects via context properties.
- **Lifetime:** All QObjects created during bootstrap must outlive the shutdown sequence.

---

## 13. Startup Flow — Textual Diagram

```
michi.app_launcher.launch()
│
├─ MICHI_UI="qml" ───────────────────────────────────────┐
│   michi.qml_app.run_qml()                               │
│   ├─ QGuiApplication(...)                               │
│   ├─ ApplicationBootstrap()                             │
│   │   ├─ ServiceRegistry()           [empty container]  │
│   │   ├─ run()                                          │
│   │   │   ├─ _build_config()         [settings_manager] │
│   │   │   ├─ _open_database()         [connection_factory]│
│   │   │   ├─ _build_repositories()    [track/album/artist]│
│   │   │   ├─ _build_workers()         [wm, qe, job_svc]  │
│   │   │   ├─ _build_settings()        [coordinator, svc] │
│   │   │   ├─ _build_domain_services() [15+ services]     │
│   │   │   ├─ _build_action_registry() [play/pause/next…] │
│   │   │   ├─ _build_bridges()                             │
│   │   │   │   └─ create_all_bridges(container)            │
│   │   │   │       ├─ ServiceBundle(container extracts)    │
│   │   │   │       └─ BridgeFactory(services).create_all() │
│   │   │   │           ├─ Phase 0: settings migrations     │
│   │   │   │           ├─ Phase B: fundamental bridges     │
│   │   │   │           ├─ Phase C: domain bridges          │
│   │   │   │           ├─ Phase D: advanced tool bridges   │
│   │   │   │           └─ Phase E: assert_wiring + bind    │
│   │   │   ├─ _register_contexts()    [QML context props]  │
│   │   │   └─ container.start()       [READY/DEGRADED]    │
│   │   └─ [container is populated, bridges ready]         │
│   ├─ QQmlApplicationEngine(ui_qml/main.qml)              │
│   ├─ ContextRegistrar(engine).register_dict(bindings)    │
│   ├─ engine.load()                                       │
│   └─ app.exec()                    [event loop]          │
│                                                          │
│ [only QML mode is supported]                             │
│                                                          │
```

---

## Appendix A: Detected Anomalies (JA Audit)

### ruff errors
- `tests/qml/composition/test_no_private_patching.py:37` — invalid-syntax (Unexpected indentation)
- `tests/qml/composition/test_no_private_patching.py:40` — invalid-syntax (Expected a statement)

### compileall errors
- `tests/qml/composition/test_no_private_patching.py` — IndentationError (line 37)

### Duplicate classes
| Class | File 1 | File 2 | Notes |
|---|---|---|---|
| `JobStatus` | `core/job_service.py:12` | `core/jobs/job_types.py:10` | Different enum values (QUEUED vs PENDING, no PAUSED in job_service) |
| `Clock` | `core/radio/interfaces.py:47` | `core/lyrics/interfaces.py:62` | Same Protocol, lyrics has fewer methods (no `utc_now`) |
| `NetworkStatus` | `core/radio/interfaces.py:47` | `core/lyrics/interfaces.py:67` | Same Protocol, identical signatures |

### Empty test files (only `__init__.py`)
- `tests/qml/composition/__init__.py`
- `tests/qml/runtime/__init__.py`

### Backups/artifacts
- No `.bak`, `.orig`, `.rej` files found
- `__pycache__` directories present (standard Python cache — excluded from versioning)

### Incompatible constructors
- No incompatible `__init__` signatures detected across duplicate classes
- `Clock` in `lyrics/interfaces.py` lacks `utc_now()` — potential Protocol conformance issue
