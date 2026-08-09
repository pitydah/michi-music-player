## Verify Report — M1.1 Audio Lab Analysis Durable Job Convergence

### Spec Coverage

| # | Requirement | Covered? | Test | Status |
|---|------------|----------|------|--------|
| 1 | Handler factory is pure and stdlib-only | Yes | `tests/test_analysis_job_handler.py` (5 tests) | PASS |
| 2 | Handler passes through the port | Yes | `test_handler_passes_through_port_result` | PASS |
| 3 | Handler raises on error status from port | Yes | `test_handler_raises_runtime_error_on_error_status` | PASS |
| 4 | Handler observes cooperative cancellation | Yes | `test_handler_observes_cancellation_before_port_call` + `_after_port_call` | PASS |
| 5 | AudioLabPort wraps AudioAnalysisService | Yes | Covered by integration: port built from `container.get("audio_lab_service").analysis` in `_build_ports` | PASS |
| 6 | Port is None-safe | Yes | `test_handler_raises_when_port_is_none` | PASS |
| 7 | Handler is registered before resume_pending_jobs | Yes | `tests/architecture/test_audio_lab_uses_durable_jobs.py::test_analysis_handler_registered_before_resume_pending_jobs` | PASS |
| 8 | QUEUED analysis job resumes on restart | Yes | `test_queued_analysis_job_resumes_on_restart_when_handler_registered` | PASS |
| 9 | QUEUED analysis job fails when handler NOT registered | Yes | `test_queued_analysis_job_fails_handler_unavailable_on_restart` | PASS |
| 10 | Bridge creates and starts durable analysis jobs | Yes | `tests/integration/jobs/test_audio_analysis_durable.py` (17 tests) | PASS |
| 11 | startAnalysis degrades when job_service unavailable | Yes | `test_start_analysis_returns_service_unavailable_when_job_service_is_none` | PASS |
| 12 | startAnalysis fails when no handler registered | Yes | `test_start_analysis_fails_when_no_handler_registered` | PASS |
| 13 | Bridge maps durable job signals to QML contract | Yes | `test_durable_signal_reemission_filtered_by_owner_and_type` | PASS |
| 14 | Non-analysis job signals NOT re-emitted | Yes | `test_non_analysis_signals_not_reemitted` | PASS |
| 15 | jobProgress re-emitted for analysis jobs | Yes | `test_durable_signal_reemission_filtered_by_owner_and_type` | PASS |
| 16 | jobCompleted re-emitted with handler result | Yes | `test_durable_signal_reemission_filtered_by_owner_and_type` | PASS |
| 17 | jobFailed re-emitted with error | Yes | `test_durable_signal_reemission_filtered_by_owner_and_type` | PASS |
| 18 | cancelJob delegates to DurableJobService | Yes | `test_cancel_job_delegates_to_durable_service` | PASS |
| 19 | cancelJob returns JOB_NOT_FOUND for unknown id | Yes | `test_cancel_job_returns_not_found_for_unknown_id` | PASS |
| 20 | retryJob reuses same job_id | Yes | `test_retry_job_reuses_same_id` | PASS |
| 21 | cleanupCompleted deletes terminal audio_lab jobs | Yes | `test_cleanup_completed_deletes_terminal_audio_lab_jobs` | PASS |
| 22 | jobStatus reads from durable store | Yes | `test_job_status_reads_from_durable_store` | PASS |
| 23 | JobBridge translates analysis type to title | Yes | `tests/test_job_bridge.py::test_title_by_type_includes_analysis` + `test_analysis_job_maps_to_qml_title` | PASS |
| 24 | Adapter creates analysis job as retryable | Yes | `test_adapter_submit_analysis_creates_retryable_job` | PASS |
| 25 | Adapter does not start job if handler missing | Yes | `test_adapter_submit_skips_start_when_handler_missing` | PASS |

### Test Results

- **T0 gate**: PASS (24 passed, 1 skipped, 0 failures)
- **Integration (audio_analysis_durable)**: 17/17 passed
- **Handler (analysis_job_handler)**: 5/5 passed
- **Architecture (audio_lab_uses_durable_jobs)**: 4/4 passed
- **Bridge contracts (audio_lab_capture_contracts)**: 12/13 passed (1 skipped)
- **JobBridge**: 3/3 passed

**Total**: 65 passed, 1 skipped, 0 failures

### Code Quality

- **Ruff**: 0 violations
- **compileall**: 0 errors

### Contract Verification

- [x] `make_analysis_handler` is pure (stdlib imports only: `__future__`, `logging` — no PySide6, no `container.get`)
- [x] Handler registration order in `core/composition/jobs.py`: `register_production_job_handlers` (line 247, registers analysis at line 210-212) BEFORE `resume_pending_jobs` (line 248-249)
- [x] AudioLabBridge no longer uses `threading.Thread` for analysis jobs — `startAnalysis` (line 425) delegates to `self._jobs.create_job` + `start_job`
- [x] `cancelJob` delegates to `self._jobs.cancel_job` for durable analysis jobs (line 644)
- [x] `retryJob` delegates to `self._jobs.retry_job` and returns same `job_id` (line 675-677)
- [x] `cleanupCompleted` delegates to `self._jobs.list_jobs(owner="audio_lab")` + `delete_job` (line 700-711)
- [x] `TITLE_BY_TYPE` has `"analysis": "Análisis técnico"` in `JobBridge` (line 38)
- [x] `JOB_TITLES` has `"analysis": "Análisis de audio"` in `core/jobs/handlers.py` (line 21)
- [x] `AudioLabJobAdapter._submit` sets `retryable=True` for ANALYSIS only (line 174)
- [x] `AudioLabJobAdapter._submit` skips `start_job` when handler missing (lines 183-188)

### Risks Found

**WARNING**: `retryJob` in `audio_lab_bridge.py` (lines 684-685) has a legacy fallback path that calls `self.startAnalysis(filepath)` for non-durable analysis jobs in `_active_jobs`. This path is never reached in production (analysis jobs use durable service exclusively), but it still uses `threading.Thread` internally via `_start_background_job`. This is a design debt artifact — the legacy path could be removed in a cleanup pass but it does not affect the productive durable-job path.

### Overall Verdict

**PASS** — All 10 spec requirements (25 scenarios) verified. All 6 test suites green. T0 safety gate passes. No blocking risks. Production code path is converged and verified.
