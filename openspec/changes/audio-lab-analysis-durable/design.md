# Design: M1.1 Audio Lab Analysis Durable Job Convergence

## Technical Approach

Converge only `analysis` onto the canonical durable path:

```text
AudioAnalysisPage.qml
  → AudioLabBridge
  → AudioLabJobAdapter        ← sole Analysis job construction authority
  → DurableJobService         ← sole execution/state/persistence authority
  → make_analysis_handler(AudioLabPort)
  → _AnalysisPort
  → AudioAnalysisService.analyze_file()

JobBridge → DurableJobService (unified visibility)
```

Composition owns service lookup and port construction. Local execution remains for conversion, ReplayGain, integrity, comparison, CD rip, and marker splitting.

## Architecture Decisions

| Choice | Rejected | Rationale |
|---|---|---|
| Bridge delegates through AudioLabJobAdapter | Bridge creates durable jobs directly | Single orchestration surface; adapter owns job construction policy. |
| Pure `make_analysis_handler(port)` | Handler service lookup | Preserves ADR-004 and stdlib-only imports. |
| Register before `resume_pending_jobs()` | Lazy registration | Prevents recovered jobs failing `HANDLER_UNAVAILABLE`. |
| Native `retry_job(id)` | Replacement job | Preserves ID and original payload. |
| Cancellation checks around analysis | Mid-call interruption | `analyze_file()` is synchronous and not safely interruptible. |
| `_AnalysisPort` fail-closed: only `completed` → ok=True | Permissive NOT-in-failure-set | Prevents unrecognized/future statuses from being treated as success. |

## Data and Signal Flow

```text
startAnalysis(filepath)
  → bridge delegates to AudioLabJobAdapter.submit_analysis(filepath)
  → adapter creates job (owner="audio_lab", type="analysis",
      retryable=True, cancellable=True, pausable=False)
  → adapter calls DurableJobService.start_job(job_id)
  → handler: validate payload → cancel checkpoint → port.analyze()
  → validate result.ok BEFORE progress 1.0
  → if ok=False → FAILED; otherwise → progress 1.0 → SUCCEEDED
  → bridge reads back effective state via get_job()
  → returns {ok, job_id, status} with real state (QUEUED/RUNNING/SUCCEEDED/FAILED)
```

```text
jobProgress(id, value)  → filter owner/type → jobProgress(id, "analysis", value) + dataChanged
jobCompleted(id, result)→ filter owner/type → jobCompleted(id, "analysis", result) + dataChanged
jobFailed(id, error)    → filter owner/type → jobFailed(id, error) + dataChanged
```

Each callback reads `get_job(id)` and accepts only `owner="audio_lab"`, `type="analysis"`; unrelated durable jobs cannot double-emit.

## Interfaces and Data Contracts

```python
class AudioLabPort(Protocol):
    def analyze(self, filepath: str, ctx: Any | None = None) -> dict[str, Any]: ...

def make_analysis_handler(port: AudioLabPort | None) -> Callable[..., dict]: ...
```

- Payload: `{"request": {"filepath": str}}`. Handler validates request presence and filepath non-empty.
- Success contract: `_AnalysisPort` normalizes `AudioAnalysisService` statuses:
  - `"completed"` → `ok=True` (the ONLY success status)
  - `"error"`, `"unsupported"`, `"disabled"`, `"unknown"`, empty, or any unrecognized → `ok=False`
- Handler checks `result.get("ok")` exclusively — never hardcodes `status == "ok"`.
- Progress: `report_progress(1.0, "Analysis complete")` ONLY after successful validation.
  Never emit 100 % for a failed result.
- Bridge start: returns `{ok, job_id, status}` with readback state; QML reads `result.job_id`.
- Cancel: readback after `cancel_job()` — `CANCELLING` for RUNNING jobs, `CANCELLED` for QUEUED.
- Retry: same job_id, readback after `retry_job()`.
- jobStatus: uses `AudioLabJobAdapter.get()` projection (single schema).
- activeJobs: only active states (QUEUED, RUNNING, CANCELLING).
- cleanupCompleted: `owner="audio_lab"` + `type="analysis"` + terminal only.
- Title: `"analysis": "Análisis técnico"` (handler, adapter, JobBridge — unified).
- Analysis NEVER enters `bridge._active_jobs` or creates local `threading.Thread`.

## Diff Surface

| File | Action | Change |
|---|---|---|
| `core/jobs/handlers.py` | Modify | Add analysis handler, payload validation, progress-after-validation, JOB_TITLES. |
| `core/jobs/ports.py` | Modify | AudioLabPort protocol. |
| `core/composition/jobs.py` | Modify | Fail-closed `_AnalysisPort`; register before resume. |
| `core/jobs/job_service.py` | Modify | Add public `get_job_snapshot()`. |
| `ui_qml_bridge/audio_lab_bridge.py` | Modify | Delegate to adapter; readback; active-state projection; signals + dataChanged. |
| `core/audio_lab/audio_lab_job_adapter.py` | Modify | Remove `_handlers` access; retryable=True for analysis; state normalization; created_at fix. |
| `ui_qml_bridge/job_bridge.py` | Modify | Add analysis title. |
| `tests/test_analysis_job_handler.py` | Add | Handler/port/progress/payload/cancellation contracts. |
| `tests/architecture/test_audio_lab_uses_durable_jobs.py` | Modify | Registration, adapter delegation, local registry/thread invariants. |
| `tests/integration/jobs/test_audio_analysis_durable.py` | Add | Recovery, signals (positive + negative), capacity, cancel CANCELLING, retry, cleanup. |

No files are deleted.

## Risks

Cancellation is delayed during synchronous analysis. Shared worker capacity can queue analysis. Lifecycle routing must retain local fallback for out-of-scope types to avoid conversion/ReplayGain regressions.
