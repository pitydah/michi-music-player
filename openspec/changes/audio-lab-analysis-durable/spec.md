# Spec: durable-audio-analysis-jobs

## ADDED Requirements

### Requirement: Handler factory is pure and stdlib-only
`make_analysis_handler(port)` in `core/jobs/handlers.py` closes over an `AudioLabPort` instance and returns a callable conforming to the `DurableJobService` handler contract `(job, ctx) -> dict`. The factory imports only from `__future__`, `logging`, and the builtins — no service construction, no `container.get`, no PySide6 (ADR-004).

JOB_TITLES must include `"analysis": "Análisis de audio"`.

#### Scenario: Handler passes through the port
- **GIVEN** a registered `make_analysis_handler(port)` where `port.analyze` returns `{"status": "ok", "features": {...}}`
- **WHEN** a job with `payload={"request": {"filepath": "/tracks/foo.flac"}}` is started
- **THEN** the handler calls `port.analyze("/tracks/foo.flac", ctx)`, reports progress at 0.1 and 1.0, and returns the port's result dict verbatim — the job is marked SUCCEEDED

#### Scenario: Handler raises on error status from port
- **GIVEN** `port.analyze` returns `{"status": "error", "error": "Unsupported codec"}`
- **WHEN** the handler runs
- **THEN** it raises `RuntimeError("Unsupported codec")` — the job is marked FAILED

#### Scenario: Handler observes cooperative cancellation
- **GIVEN** the job is CANCELLING and the handler calls `ctx.token.raise_if_cancelled()` before calling the port
- **WHEN** the cancellation token has been requested
- **THEN** a `CancelledError` propagates, the handle returns, and the job transitions to CANCELLED

### Requirement: AudioLabPort wraps AudioAnalysisService
An `_AnalysisPort` adapter in `core/composition/jobs.py` conforms to `core.jobs.ports.AudioLabPort` and delegates `analyze(filepath, ctx)` to `AudioAnalysisService.analyze_file(filepath)`. The port introduces no business logic — it is a ctx-shaped call adapter only. The port is built from `container.get("audio_lab_service").analysis`.

#### Scenario: Port delegates to the composed service
- **GIVEN** the container provides `audio_lab_service.analysis` as an `AudioAnalysisService` instance
- **WHEN** `_AnalysisPort.analyze("/tracks/foo.flac", ctx)` is called
- **THEN** it returns the result of `audio_lab_service.analysis.analyze_file("/tracks/foo.flac")` verbatim

#### Scenario: Port is None-safe
- **GIVEN** `container.get("audio_lab_service")` returns None (test/minimal bootstrap)
- **WHEN** `_build_ports` builds the analysis port
- **THEN** the port is None; `make_analysis_handler(None)` produces a handler that raises `RuntimeError("AudioLabService unavailable")` at invocation

### Requirement: Handler is registered before resume_pending_jobs
`register_production_job_handlers` in `core/composition/jobs.py` registers `"analysis"` with `make_analysis_handler(analysis_port)` BEFORE `build()` calls `resume_pending_jobs()`. The order is guaranteed by the existing control flow: `register_production_job_handlers` runs first, then `resume_pending_jobs` (line 214 of `core/composition/jobs.py`). The analysis port must be built in `_build_ports` so it is available for registration.

#### Scenario: Handler is registered before resume
- **GIVEN** the Jobs composition builder runs
- **WHEN** `register_production_job_handlers` executes
- **THEN** `job_service.register_handler("analysis", ...)` is called with the analysis handler, AND `job_service._handlers` contains `"analysis"` before `resume_pending_jobs()` is called

#### Scenario: QUEUED analysis job resumes on restart when handler is registered
- **GIVEN** a QUEUED `analysis` job persisted in `durable_jobs.db` from a previous process
- **WHEN** the application boots and `resume_pending_jobs()` runs AFTER handler registration
- **THEN** the job is started (not failed with `HANDLER_UNAVAILABLE`)

#### Scenario: QUEUED analysis job fails when handler is NOT registered
- **GIVEN** a QUEUED `analysis` job persisted but `"analysis"` is NOT in `_handlers`
- **WHEN** `resume_pending_jobs()` runs
- **THEN** the job is marked FAILED with message `"HANDLER_UNAVAILABLE: analysis"`

### Requirement: Bridge creates and starts durable analysis jobs
`AudioLabBridge.startAnalysis(filepath)` no longer spawns a raw `threading.Thread`. Instead, when `self._jobs` (DurableJobService) is available, it calls:
1. `create_job("analysis", owner="audio_lab", payload={"request": {"filepath": fp}}, cancellable=True, pausable=False, retryable=True)`
2. `start_job(job_id)`

It returns `_JobStartResult(ok=True, job_id=job_id, status="running")` on success. The local `_active_jobs` dict and `_threads` dict are no longer used for analysis jobs.

#### Scenario: startAnalysis creates and starts a durable job
- **GIVEN** `self._jobs` is a DurableJobService with the analysis handler registered
- **WHEN** `startAnalysis("/tracks/foo.flac")` is called
- **THEN** a durable job of type `"analysis"` with owner `"audio_lab"` and payload `{"request": {"filepath": "/tracks/foo.flac"}}` is created, started, and the returned dict has `ok=True` with the job_id

#### Scenario: startAnalysis degrades when job_service is unavailable
- **GIVEN** `self._jobs` is None
- **WHEN** `startAnalysis("/tracks/foo.flac")` is called
- **THEN** the result is `_JobStartResult({"ok": False, "error": "SERVICE_UNAVAILABLE", "error_code": "SERVICE_UNAVAILABLE"})`

#### Scenario: startAnalysis fails when no handler is registered
- **GIVEN** `self._jobs` has no handler for `"analysis"`
- **WHEN** `startAnalysis("/tracks/foo.flac")` is called
- **THEN** `start_job` returns False, and the returned dict has `ok=False, error="No handler for type: analysis"` — the job is marked FAILED

### Requirement: Bridge maps durable job signals to its own QML contract
`AudioLabBridge` subscribes to `DurableJobService` signals and re-emits its own `jobProgress`, `jobCompleted`, and `jobFailed` for `analysis` jobs (owner `"audio_lab"`, filtered). The bridge does NOT re-emit signals for non-analysis jobs (conversion, replaygain, integrity, comparison, CD rip, recording split — those remain on `_start_background_job`).

#### Scenario: jobProgress is re-emitted for analysis jobs
- **GIVEN** the bridge subscribes to `job_service.jobProgress`
- **WHEN** a durable `analysis` job owned by `"audio_lab"` reports progress 0.45
- **THEN** `AudioLabBridge.jobProgress` is emitted with `(job_id, "analysis", 0.45)`

#### Scenario: jobCompleted is re-emitted with the handler result
- **GIVEN** the bridge subscribes to `job_service.jobCompleted`
- **WHEN** an `analysis` job owned by `"audio_lab"` completes with result `{"status": "ok", "features": {...}}`
- **THEN** `AudioLabBridge.jobCompleted` is emitted with `(job_id, "analysis", result_dict)`

#### Scenario: jobFailed is re-emitted with the error
- **GIVEN** the bridge subscribes to `job_service.jobFailed`
- **WHEN** an `analysis` job owned by `"audio_lab"` fails with error `"Unsupported codec"`
- **THEN** `AudioLabBridge.jobFailed` is emitted with `(job_id, "Unsupported codec")`

#### Scenario: Non-analysis job signals are NOT re-emitted
- **GIVEN** the bridge subscribes to `job_service.jobProgress`/`jobCompleted`/`jobFailed`
- **WHEN** a `conversion` or `replaygain` job (still on `_start_background_job`) emits through the local path
- **THEN** the bridge does NOT emit a duplicate through the durable signal path (no double-emission)

### Requirement: cancelJob, retryJob, cleanupCompleted delegate to DurableJobService
`AudioLabBridge.cancelJob(job_id)` delegates to `self._jobs.cancel_job(job_id)`. `retryJob(job_id)` delegates to `self._jobs.retry_job(job_id)` (same ID, not a new job). `cleanupCompleted()` deletes terminal `audio_lab`-owned jobs via `self._jobs.delete_job(job_id)`. `jobStatus(job_id)` reads from `self._jobs.get_job(job_id)`. `activeJobs` (property) returns `self._jobs.list_jobs(owner="audio_lab")`.

#### Scenario: cancelJob delegates to DurableJobService
- **GIVEN** `self._jobs` is available and job_id `"abc123"` exists in RUNNING state
- **WHEN** `cancelJob("abc123")` is called
- **THEN** `self._jobs.cancel_job("abc123")` is called and returns `True`; the bridge returns `{"ok": True, "job_id": "abc123", "status": "cancelled"}`

#### Scenario: cancelJob returns JOB_NOT_FOUND for unknown job_id
- **GIVEN** `self._jobs` is available and job_id `"nonexistent"` does not exist
- **WHEN** `cancelJob("nonexistent")` is called
- **THEN** `get_job` returns None; the bridge returns `{"ok": False, "error": "JOB_NOT_FOUND", "error_code": "JOB_NOT_FOUND"}`

#### Scenario: retryJob reuses the same job_id
- **GIVEN** `self._jobs` is available and job_id `"abc123"` is FAILED with `retryable=True`
- **WHEN** `retryJob("abc123")` is called
- **THEN** `self._jobs.retry_job("abc123")` is called; the job is re-queued with the SAME id; the result dict contains `job_id: "abc123"` (NOT `new_job_id`)

#### Scenario: cleanupCompleted deletes terminal audio_lab jobs
- **GIVEN** two terminal `audio_lab`-owned jobs and one terminal `device_sync`-owned job
- **WHEN** `cleanupCompleted()` is called
- **THEN** only the two `audio_lab` jobs are deleted; `{"ok": True, "cleaned": 2}` is returned

#### Scenario: jobStatus reads from durable store
- **GIVEN** `self._jobs` is available and has job `"abc123"` in state SUCCEEDED
- **WHEN** `jobStatus("abc123")` is called
- **THEN** the result includes `state: "SUCCEEDED"` (from the durable job, not `_active_jobs`)

### Requirement: Unified Jobs visibility shows analysis title
`JobBridge.TITLE_BY_TYPE` maps `"analysis"` to `"Análisis técnico"` so that analysis jobs listed in the generic Jobs view display the correct Spanish label.

#### Scenario: JobBridge translates analysis type to title
- **GIVEN** a durable job with `type: "analysis"` and no explicit `title` in payload
- **WHEN** `JobBridge._job_to_qml()` maps it
- **THEN** the QML dict has `"title": "Análisis técnico"`

### Requirement: Adapter alignment — retryable and handler pre-check
`AudioLabJobAdapter._submit` sets `retryable=True` when creating `analysis` jobs (currently hard-coded `False`). Before calling `start_job`, the adapter validates the handler is registered: if `job.type not in self._job_svc._handlers`, it logs a warning and returns early (the job stays QUEUED but not started — the bridge will start it after registration).

#### Scenario: Adapter creates analysis job as retryable
- **GIVEN** `AudioLabJobAdapter._submit` is called with operation `ANALYSIS`
- **WHEN** a durable job is created via `job_svc.create_job`
- **THEN** `retryable=True` is passed

#### Scenario: Adapter does not start job if handler is missing
- **GIVEN** `job_svc._handlers` does NOT contain `"analysis"`
- **WHEN** `_submit` calls `start_job`
- **THEN** it logs a warning and does NOT call `start_job` — the job remains QUEUED

### Requirement: Cooperative cancellation between handler progress steps
The analysis handler calls `ctx.token.raise_if_cancelled()` at the following checkpoints: before calling `port.analyze()`, and after `port.analyze()` returns. Cancellation is NOT instantaneous — `AudioAnalysisService.analyze_file()` is synchronous and cannot be interrupted mid-call. The cancellation is observed at the next checkpoint after the CANCELLING state is set.

#### Scenario: Cancellation before port call is immediate
- **GIVEN** a RUNNING analysis job and the handler is about to call `port.analyze()`
- **WHEN** `cancel_job` is called, transitioning state to CANCELLING, and the handler reaches `ctx.token.raise_if_cancelled()`
- **THEN** `CancelledError` is raised; the handler returns; the job transitions to CANCELLED

#### Scenario: Cancellation during port call is delayed
- **GIVEN** a RUNNING analysis job and `port.analyze()` is executing (may take 10-30s for large files)
- **WHEN** `cancel_job` is called during the port call
- **THEN** the handler does NOT observe cancellation until `port.analyze()` returns and the post-call checkpoint runs — the job transitions to CANCELLED after the port call completes
