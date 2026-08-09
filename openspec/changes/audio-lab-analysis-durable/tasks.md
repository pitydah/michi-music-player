# Tasks: M1.1 Audio Lab Analysis Durable Job Convergence

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | 420–550 |
| 400-line budget risk | Medium |
| Chained PRs recommended | Yes |
| Chain strategy | pending |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: pending
400-line budget risk: Medium

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | Handler + port + registration (foundation) | PR 1 | `pytest tests/test_analysis_job_handler.py -q` | N/A (pure logic, no runtime UI) | Remove handler registration + `_AnalysisPort`; restore prior `ports.py` |
| 2 | Bridge lifecycle (start/cancel/retry/cleanup) | PR 2 | `pytest tests/integration/jobs/test_audio_analysis_durable.py -q` | `python main.py` → Audio Lab → Analysis → verify Jobs view | Revert bridge methods to `_start_background_job` path |
| 3 | Adapter + JobBridge + restart + gate | PR 3 | `scripts/test_gate.sh` | `python main.py` → start analysis → kill → restart → job resumes | Revert adapter `retryable` + `TITLE_BY_TYPE` entry |

---

## Phase 1: Handler + Port + Registration (Foundation)

- [ ] 1.1 Narrow `AudioLabPort` in `core/jobs/ports.py` to `analyze(filepath, ctx)` only (remove `probe`). Lines: ~5.
  - Covers: Handler factory is pure and stdlib-only.
- [ ] 1.2 Write RED tests in `tests/test_analysis_job_handler.py`: payload passthrough, error→RuntimeError, cancellation, None-port. Lines: ~120.
  - Covers: Handler passes through the port; Handler raises on error status; Handler observes cooperative cancellation.
- [ ] 1.3 Implement `make_analysis_handler(port)` in `core/jobs/handlers.py` + add `"analysis": "Análisis de audio"` to `JOB_TITLES`. Lines: ~35.
  - Covers: Handler factory is pure and stdlib-only; JOB_TITLES.
- [ ] 1.4 Build `_AnalysisPort` in `core/composition/jobs.py` → `_build_ports`, wrapping `container.get("audio_lab_service").analysis`. Lines: ~15.
  - Covers: AudioLabPort wraps AudioAnalysisService; Port is None-safe.
- [ ] 1.5 Register `"analysis"` handler in `register_production_job_handlers` using `make_analysis_handler(ports["analysis"])`. Lines: ~5.
  - Covers: Handler is registered before resume_pending_jobs.
- [ ] 1.6 RED test in `tests/architecture/test_audio_lab_uses_durable_jobs.py`: handler registered before resume. Lines: ~40.
  - Covers: Handler is registered before resume.

## Phase 2: Bridge Lifecycle

- [ ] 2.1 Write RED tests in `tests/integration/jobs/test_audio_analysis_durable.py`: startAnalysis creates+starts durable job, SERVICE_UNAVAILABLE degradation, no-handler failure. Lines: ~100.
  - Covers: startAnalysis creates and starts a durable job; startAnalysis degrades; startAnalysis fails when no handler.
- [ ] 2.2 Implement `startAnalysis` in `ui_qml_bridge/audio_lab_bridge.py`: `create_job` + `start_job` on DurableJobService. Lines: ~20.
  - Covers: Bridge creates and starts durable analysis jobs.
- [ ] 2.3 Wire durable signal re-emission: subscribe to `job_service.jobProgress/jobCompleted/jobFailed`, filter `owner="audio_lab"` + `type="analysis"`, re-emit bridge signals. Lines: ~25.
  - Covers: jobProgress/jobCompleted/jobFailed re-emitted; Non-analysis signals NOT re-emitted.
- [ ] 2.4 Implement `cancelJob` → `cancel_job`, `retryJob` → `retry_job` (same-ID), `cleanupCompleted` → `delete_job` (owner-filtered), `jobStatus` → `get_job`. Lines: ~50.
  - Covers: cancelJob/retryJob/cleanupCompleted/jobStatus; JOB_NOT_FOUND.
- [ ] 2.5 GREEN: make phase 2 tests pass. REFACTOR: extract signal wiring into `_wire_durable_signals`. Lines: ~10.

## Phase 3: Adapter + JobBridge

- [x] 3.1 Fix `AudioLabJobAdapter._submit`: `retryable=True` for analysis jobs; add handler pre-check (log warning, skip `start_job` if handler missing). Lines: ~12.
  - Covers: Adapter creates analysis job as retryable; Adapter does not start if handler missing.
- [x] 3.2 Add `"analysis": "Análisis técnico"` to `JobBridge.TITLE_BY_TYPE`. Lines: ~1.
  - Covers: JobBridge translates analysis type to title.

## Phase 4: Restart Persistence

- [x] 4.1 Write RED test: QUEUED analysis job survives restart (recovered with original payload). Lines: ~60.
  - Covers: QUEUED analysis job resumes on restart; QUEUED fails when handler NOT registered.
- [x] 4.2 Verify `resume_pending_jobs` restores analysis jobs after handler registration (composition order already correct at line 213→214). Lines: ~0 (verification only).

## Phase 5: Productive Path

- [x] 5.1 Update existing tests to durable contract: `tests/qml/audio_lab/test_audio_lab_completo.py`, `tests/qml/audio_lab/test_audio_negative.py`, `tests/test_audio_lab_capture_contracts.py`. Lines: ~100.
- [x] 5.2 Run `scripts/test_gate.sh` (T0 blocking) and fix any failures. Lines: ~20 (defensive).
