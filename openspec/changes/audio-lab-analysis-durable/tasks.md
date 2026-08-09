# Tasks: durable-audio-analysis-jobs

## Stack strategy

```
main ← #201 ← #202 ← #203
```

Linear genealogy. No duplicate commits.

## Phase 1: Foundation — PR #201

- [x] Add `AudioLabPort` protocol to `core/jobs/ports.py`
- [x] Add `make_analysis_handler(port)` factory to `core/jobs/handlers.py`
- [x] Validate payload (request dict, filepath non-empty string)
- [x] Check `result.get("ok")` — never hardcode `status == "ok"`
- [x] Report progress 1.0 ONLY after successful validation
- [x] Add `"analysis": "Análisis técnico"` to JOB_TITLES
- [x] Build `_AnalysisPort` in `core/composition/jobs.py`
- [x] Fail-closed: only `status == "completed"` → `ok=True`
- [x] Register handler before `resume_pending_jobs()`
- [x] RED/GREEN/REFACTOR: handler tests (22 tests)

## Phase 2: Bridge Lifecycle — PR #202

- [x] `startAnalysis()` delegates to `AudioLabJobAdapter.submit_analysis()`
- [x] Remove direct `create_job`/`start_job` fallback from bridge
- [x] Readback effective state on start/cancel/retry
- [x] Differentiate QUEUED (capacity) from HANDLER_UNAVAILABLE (no handler)
- [x] `cancelJob()` returns CANCELLING for RUNNING jobs, CANCELLED for QUEUED
- [x] `retryJob()` preserves same job_id, reads back state
- [x] `jobStatus()` uses adapter public projection (single schema)
- [x] `activeJobs` filters to active states only (QUEUED/RUNNING/CANCELLING)
- [x] `activeJobsMap` includes durable analysis
- [x] `cleanupCompleted()` scoped to `type=analysis` only
- [x] `dataChanged` emitted on durable completed/failed transitions
- [x] Signal re-emission filtered by owner/type
- [x] Add `get_job_snapshot()` to DurableJobService (public API)
- [x] RED/GREEN/REFACTOR: integration tests (23 tests)

## Phase 3: Adapter / Restart — PR #203

- [x] Remove `self._job_svc._handlers` access from adapter
- [x] `retryable=True` for analysis operation
- [x] Normalize state projection in `_durable_to_public`
- [x] Fix `created_at` to use `createdAt` (not `startedAt`)
- [x] Add analysis title to JobBridge `TITLE_BY_TYPE`
- [x] Restart persistence: QUEUED resumes, handler-unavailable fails
- [x] RED/GREEN/REFACTOR: adapter tests (7 tests), architecture tests (6 tests)

## Phase 4: Documentation — PR #203

- [x] `design.md`: Bridge → Adapter → DurableJobService architecture
- [x] `proposal.md`: scope, success criteria, boundaries
- [x] `spec.md`: normative requirements and scenarios
- [x] `tasks.md`: actual completion status (this file)
- [x] `verify.md`: verification evidence
- [x] `exploration.md`: marked as historical snapshot

## Phase 5: Validation

- [x] Focused tests: 69/69 PASS
- [x] T0 gate: PASS (ruff 0, compileall clean, composition smoke, gate 24/24)
- [x] Unit CI: 4400/4400 PASS
- [ ] Remote blocking CI: pending
- [ ] Ready for sequential merge: pending

## Out of scope (M1.x future)

- Integrity durable migration
- ReplayGain durable migration
- Comparison/Conversion/CD durable migration
- Removing `_active_jobs` / `_threads` entirely
- Cooperative mid-analysis cancellation
- Full inventory green
