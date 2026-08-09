# Design: M1.1 Audio Lab Analysis Durable Job Convergence

## Technical Approach

Converge only `analysis` onto the canonical durable path:

```text
AudioAnalysisPage.qml -> AudioLabBridge -> DurableJobService
  -> make_analysis_handler(AudioLabPort) -> _AnalysisPort
  -> AudioAnalysisService.analyze_file()

AudioLabJobAdapter ---------------------> DurableJobService (aligned, not delegated)
JobBridge ------------------------------> DurableJobService (unified visibility)
```

Composition owns service lookup and port construction. Local execution remains for conversion, ReplayGain, integrity, comparison, CD rip, and marker splitting.

## Architecture Decisions

| Choice | Rejected | Rationale |
|---|---|---|
| Bridge calls `DurableJobService` directly | Delegate through adapter | Avoids an orphaned mapping layer while preserving QML signals. |
| Pure `make_analysis_handler(port)` | Handler service lookup | Preserves ADR-004 and stdlib-only imports. |
| Register before `resume_pending_jobs()` | Lazy registration | Prevents recovered jobs failing `HANDLER_UNAVAILABLE`. |
| Native `retry_job(id)` | Replacement job | Preserves ID and original payload. |
| Cancellation checks around analysis | Mid-call interruption | `analyze_file()` is synchronous and not safely interruptible. |

## Data and Signal Flow

```text
startAnalysis(filepath)
 -> create_job("analysis", owner="audio_lab",
      payload={"request": {"filepath": filepath}},
      cancellable=True, pausable=False, retryable=True)
 -> start_job(id)
 -> progress .1 -> cancel check -> port.analyze
 -> cancel check -> result/error mapping -> progress 1.0
 -> persisted SUCCEEDED | FAILED | CANCELLED
```

```text
jobProgress(id, value)  -> filter owner/type -> jobProgress(id, "analysis", value)
jobCompleted(id, result)-> filter owner/type -> jobCompleted(id, "analysis", result)
jobFailed(id, error)    -> filter owner/type -> jobFailed(id, error)
```

Each callback reads `get_job(id)` and accepts only `owner="audio_lab"`, `type="analysis"`; unrelated durable jobs cannot double-emit.

## Interfaces and Data Contracts

```python
class AudioLabPort(Protocol):
    def analyze(self, filepath: str, ctx: Any | None = None) -> dict[str, Any]: ...

def make_analysis_handler(port: AudioLabPort | None) -> Callable[..., dict]: ...
```

- Payload: `{"request": {"filepath": str}}`.
- Success: analyzer result dict returned verbatim and persisted as `job.result`.
- `status="error"`: raise `RuntimeError(result["error"])`; missing port: `RuntimeError("AudioLabService unavailable")`.
- Bridge start: `{ok, job_id, status}`; QML reads string `result.job_id`.
- Adapter states: `QUEUED->queued`, `RUNNING->running`, `CANCELLING->cancel_requested`, `CANCELLED->cancelled`, `SUCCEEDED/PARTIAL_SUCCESS->completed`, `FAILED->failed`, `INTERRUPTED->interrupted`; non-pausable Audio Lab paused states map to `queued` defensively.
- Titles: handler `"analysis": "Análisis de audio"`; `JobBridge` `"analysis": "Análisis técnico"`.

## Diff Surface

| File | Action | Change |
|---|---|---|
| `core/jobs/handlers.py` | Modify | Add title and pure analysis handler. |
| `core/jobs/ports.py` | Modify | Narrow reserved port to analysis. |
| `core/composition/jobs.py` | Modify | Add None-safe `_AnalysisPort`; register before resume. |
| `ui_qml_bridge/audio_lab_bridge.py` | Modify | Durable analysis start/signals/lifecycle; retain local out-of-scope execution. |
| `core/audio_lab/audio_lab_job_adapter.py` | Modify | Analysis retryable, handler guard, state mapping. |
| `ui_qml_bridge/job_bridge.py` | Modify | Add analysis title. |
| `ui_qml/pages/audio_lab/AudioAnalysisPage.qml` | Modify | Consume map-shaped start result. |
| `tests/test_analysis_job_handler.py` | Add | Handler/error/progress/cancellation contracts. |
| `tests/architecture/test_audio_lab_uses_durable_jobs.py` | Modify | Registration and adapter alignment. |
| `tests/integration/jobs/test_audio_analysis_durable.py` | Add | Recovery, signals, retry, cancel, cleanup. |
| `tests/qml/audio_lab/test_audio_lab_completo.py` | Modify | Durable lifecycle expectations. |
| `tests/qml/audio_lab/test_audio_negative.py` | Modify | Degraded/not-found/start failure. |
| `tests/test_audio_lab_capture_contracts.py` | Modify | Map result and durable visibility. |

No files are deleted.

## Ordering and Strict TDD Slices

1. **Handler/port** — RED payload, progress, error, unavailable, and cancellation tests; GREEN factory/protocol; REFACTOR; run focused + ADR-004 tests.
2. **Composition/recovery** — RED registration-before-resume and original-payload restart tests; GREEN port/registration; REFACTOR.
3. **Bridge vertical slice** — RED start and filtered signal tests; GREEN durable submission/re-emission plus QML `job_id`; REFACTOR; exercise productive path.
4. **Lifecycle** — RED cancel, same-ID retry, status, visibility, cleanup; GREEN delegation; REFACTOR without migrating other operations.
5. **Adapter/Jobs** — RED retryable, missing-handler, state, title; GREEN alignment; REFACTOR constants.
6. **Checkpoint** — focused tests, `scripts/test_gate.sh` (T0 blocking), relevant T2/QML tests; report PASS/PARTIAL/FAIL.

Handler registration must land before bridge activation. Rollback is per slice, but registration and bridge activation revert together.

## Testing Approach

Use `tmp_path` SQLite, real `DurableJobService`, fake ports, and `WorkerManager` only for cancellation/restart integration. Assert exact payloads/signals, owner/type filtering, same ID and original payload on retry, and no non-analysis duplicates. Final evidence must exercise composition -> bridge -> handler -> analyzer fake -> persisted terminal job; mock-only evidence is insufficient.

## Threat Matrix

N/A — no routing, shell, subprocess, VCS automation, executable classification, or process-integration boundary.

## Risks

Cancellation is delayed during synchronous analysis. Shared worker capacity can queue analysis. Lifecycle routing must retain local fallback for out-of-scope types to avoid conversion/ReplayGain regressions.
