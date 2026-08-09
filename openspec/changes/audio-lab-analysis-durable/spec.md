# Spec: durable-audio-analysis-jobs

## ADDED Requirements

### Requirement: Handler factory is pure and stdlib-only
`make_analysis_handler(port)` in `core/jobs/handlers.py` closes over an `AudioLabPort` instance and returns a callable conforming to the `DurableJobService` handler contract `(job, ctx) -> dict`. The factory imports only from `__future__`, `logging`, and the builtins — no service construction, no `container.get`, no PySide6 (ADR-004).

JOB_TITLES must include `"analysis": "Análisis técnico"`.

#### Scenario: Handler passes through the port
- **GIVEN** a port returning `{"ok": True, "status": "completed", "features": {...}}`
- **WHEN** the handler runs with a valid payload `{"request": {"filepath": "/tracks/foo.flac"}}`
- **THEN** the handler returns the result verbatim AND reports progress 0.1 and 1.0

#### Scenario: Handler validates payload
- **GIVEN** a port is available
- **WHEN** the job payload has no `request` key, `request` is None, `filepath` is missing, empty, or non-string
- **THEN** the handler raises `RuntimeError("INVALID_PAYLOAD: ...")` BEFORE calling the port

### Requirement: Port normalizes real service status (fail-closed)
`_AnalysisPort` in `core/composition/jobs.py` wraps `AudioAnalysisService.analyze_file()` and normalises the real-service status into a durable `ok` boolean.

Only `status == "completed"` → `ok=True`. Every other value (`error`, `unsupported`, `disabled`, `unknown`, empty, or any unrecognized string) → `ok=False`.

The original `status` is preserved in the result for UI readback.

#### Scenario: Completed analysis succeeds
- **GIVEN** `AudioAnalysisService.analyze_file()` returns `{"status": "completed", "features": {...}}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": True` AND `"status": "completed"` is preserved

#### Scenario: Error analysis fails
- **GIVEN** the service returns `{"status": "error", "error": "Backend crash"}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": False`

#### Scenario: Unsupported analysis fails
- **GIVEN** the service returns `{"status": "unsupported"}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": False`

#### Scenario: Disabled analysis fails
- **GIVEN** the service returns `{"status": "disabled"}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": False`

#### Scenario: Empty status fails-closed
- **GIVEN** the service returns `{"status": ""}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": False`

#### Scenario: Unrecognized status fails-closed
- **GIVEN** the service returns `{"status": "future_unknown_status"}`
- **WHEN** the port's `analyze()` is called
- **THEN** the result contains `"ok": False`

### Requirement: Handler never reports completion before validation
The handler MUST validate `result.get("ok")` BEFORE calling `ctx.report_progress(1.0, "Analysis complete")`. A failed analysis must never be shown as 100 % complete.

#### Scenario: Failed analysis never shows completion
- **GIVEN** the port returns `{"ok": False, "status": "error"}`
- **WHEN** the handler runs
- **THEN** `ctx.report_progress(1.0, "Analysis complete")` is NEVER called

### Requirement: Bridge delegates to AudioLabJobAdapter
`AudioLabBridge.startAnalysis()` delegates exclusively to `AudioLabJobAdapter.submit_analysis()`. The bridge does NOT call `DurableJobService.create_job()` or `start_job()` directly for Analysis. The adapter owns job construction policy (type, owner, retryable, cancellable, pausable, payload shape).

If the adapter is unavailable, the bridge returns `SERVICE_UNAVAILABLE`.

#### Scenario: Adapter constructs and starts the job
- **GIVEN** `audio_lab_service.jobs` is available
- **WHEN** `bridge.startAnalysis(filepath)` is called
- **THEN** `adapter.submit_analysis(filepath)` is called AND the bridge reads back the effective state via `get_job()`

#### Scenario: Adapter unavailable
- **GIVEN** `audio_lab_service.jobs` is None
- **WHEN** `bridge.startAnalysis(filepath)` is called
- **THEN** the result is `{ok: False, error_code: SERVICE_UNAVAILABLE}`

### Requirement: Bridge reads back effective state
After delegating to the adapter, the bridge MUST call `get_job(job_id)` and return the actual durable state — never assume `running`.

#### Scenario: Capacity full → QUEUED
- **GIVEN** max_concurrent is exhausted
- **WHEN** `startAnalysis` is called
- **THEN** the result is `{ok: True, status: "queued"}` AND `error_code` is NOT `HANDLER_UNAVAILABLE`

#### Scenario: No handler → FAILED
- **GIVEN** no handler is registered for `analysis`
- **WHEN** `startAnalysis` is called
- **THEN** the result is `{ok: False, error_code: HANDLER_UNAVAILABLE}`

### Requirement: Cancel reads back effective state
`cancelJob()` MUST call `get_job()` after `cancel_job()` and return the actual state. For RUNNING jobs the state is `CANCELLING`; it is only `CANCELLED` when the durable job reaches that terminal state.

#### Scenario: Cancel RUNNING → cancelling
- **GIVEN** a durable analysis job is in RUNNING state
- **WHEN** `cancelJob(job_id)` is called
- **THEN** the returned status is `cancelling` after readback

### Requirement: Retry reads back effective state
`retryJob()` MUST call `get_job()` after `retry_job()` and return the actual state. The same `job_id` is preserved.

### Requirement: jobStatus uses single adapter projection
`jobStatus()` for Analysis jobs MUST use `AudioLabJobAdapter.get()` exclusively. The schema uses `status` (lowercase), not `state` (uppercase). No raw `DurableJobService.get_job_snapshot()` fallback for Analysis.

#### Scenario: jobStatus returns adapter schema
- **GIVEN** an analysis job exists in the adapter scope
- **WHEN** `jobStatus(job_id)` is called
- **THEN** the result contains `"status"` (lowercase) with adapter-normalized value AND `"state"` is absent

### Requirement: activeJobs filters to active states only
`activeJobs` property MUST include only jobs with states `QUEUED`, `RUNNING`, or `CANCELLING`. Terminal states (`SUCCEEDED`, `FAILED`, `CANCELLED`, `INTERRUPTED`) are excluded.

### Requirement: cleanupCompleted scoped to analysis only
`cleanupCompleted()` MUST filter for `owner=audio_lab` AND `type=analysis` AND terminal state. Jobs of other types (probe, replaygain, integrity, etc.) are never deleted in M1.1.

### Requirement: Adapter does not access private _handlers
`AudioLabJobAdapter._submit()` does NOT inspect `self._job_svc._handlers`. It calls `start_job()` unconditionally; `DurableJobService` determines the outcome (executes on handler present, fails with `HANDLER_UNAVAILABLE` on handler absent, stays QUEUED on capacity exhaustion).

### Requirement: Analysis never enters bridge local registry
`startAnalysis()` MUST route through the durable path exclusively. No entry added to `_active_jobs`, no local `threading.Thread` created.

#### Scenario: Analysis job stays out of _active_jobs
- **GIVEN** a bridge with `_active_jobs` initially empty
- **WHEN** `startAnalysis(filepath)` is called
- **THEN** `_active_jobs` remains empty (no new entries)

### Requirement: Handler registered before resume_pending_jobs
In composition, `register_production_job_handlers()` MUST run before `resume_pending_jobs()` so recovered QUEUED analysis jobs have their handler available.
