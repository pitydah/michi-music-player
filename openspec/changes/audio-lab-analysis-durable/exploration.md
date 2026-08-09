# Exploration: audio-lab-analysis-durable (M1.1 — converge Audio Lab Analysis on DurableJobService)

Baseline: 2332a45c (main). Read-only exploration; no production code/tests modified.

## Current State

### 1. AudioLabBridge (ui_qml_bridge/audio_lab_bridge.py, 945 lines)
- **Local registry**: `_active_jobs: dict[str, dict]`, `_threads: dict[str, threading.Thread]`, `_lock = threading.RLock()` (lines 67-73). Raw `threading.Thread` + daemon runner — violates AGENTS.md (no threading.Thread; use QThread/ThreadPoolExecutor).
- **`_start_background_job(job_type, run_fn, *, filepath, prefix)`** (lines 168-217): creates job_id `{prefix or type}_{uuid}`, registers in `_active_jobs` with status "running"/progress 0.0, spawns a thread, `_finish_job`/`_fail_job` on completion. NOT durable, NOT cancellable cooperatively.
- **Workflows using local registry**: `startAnalysis` (393-399, prefix "analysis"), `startReplayGain` (500-517, "rg"), `startIntegrity` (549-556, "integrity"), `startComparison` (586-596, "compare"), `startConversion` (415-439, "conv"), `ripCDTrack` (779-795, "cdtrack"), `ripFullCD` (797-814, "cdfull"), `splitByMarkers` (917-927, "split").
- **Job API slots**: `cancelJob` (598-619; calls `getattr(self._jobs, "cancel")` with suppress — note `_jobs.cancel` does NOT exist on DurableJobService; it has `cancel_job`), `retryJob` (621-641; creates a NEW job via startAnalysis/startReplayGain/startIntegrity, returns `new_job_id`; "NOT_FAILED" for unknown), `cleanupCompleted` (643-654; pops terminal jobs), `jobStatus` (656-660; from `_active_jobs`, JOB_NOT_FOUND otherwise), `activeJobs` property (260-263), `activeJobsMap` (662-667).
- **Signals**: `jobProgress(str, str, float)`, `jobCompleted(str, str, object)`, `jobFailed(str, str)` (35-39) — job_id, job_type, payload. `jobServiceAvailable` property (245-247) = `self._jobs is not None`.
- **Synchronous analysis slots** (not in M1.1 scope): `analyzeFile` (364-372), `previewAnalysis` (374-381), `validateAnalysis` (383-390) — call `module.analyze_file` directly.
- **Composed in** `ui_qml_bridge/bridge_factory.py:522-532`; context binding `context_bindings.py:97` (`audioLabBridge`: required `audio_lab_service`, optional `job_service`).

### 2. QML consumption contract (ui_qml/pages/audio_lab/AudioAnalysisPage.qml)
- `_startAnalysis()` (49-70): `labService.startAnalysis(filepath)`, gate `typeof jobId === "string" && jobId.length > 0` (line 64) — startAnalysis is `@Slot(str, result=dict)` so PySide6 returns QVariantMap; the string-check is a latent integration risk for the durable migration.
- Consumes ONLY `onJobCompleted(jobId, jobType, result)` and `onJobFailed(jobId, error)` (33-47); NO onJobProgress handler. `_cancelAnalysis` (72-78) calls `labService.cancelJob(id)`.
- AudioBatchJobsPage.qml / AudioJobDetail.qml / JobsPage.qml use a DIFFERENT bridge `jobBridge` (ui_qml_bridge/job_bridge.py).

### 3. JobBridge canonical pattern (ui_qml_bridge/job_bridge.py, 262 lines)
- Thin view over DurableJobService: connects jobCreated/jobStarted/jobProgress/jobCancelled/jobCompleted/jobFailed/queueChanged → re-emits `jobsChanged` (65-71). No internal registry; `jobs` = `_js.list_jobs(limit=200)` mapped via `QML_STATE_MAP` (24-35, 94-98). cancelJob/retryJob delegate to `_js.cancel_job`/`_js.retry_job` with read-back state (212-240). clearCompleted/clearFailed use `delete_job` (242-262). **This is the pattern M1.1 must follow.**

### 4. AudioLabJobAdapter (core/audio_lab/audio_lab_job_adapter.py, 354 lines)
- **Durable path** `_submit` (164-234): with `_job_svc` → `create_job(operation.value, owner="audio_lab", payload={"request": request, "title": title}, cancellable=True, pausable=False, retryable=False)` + `start_job(job_id)` (173-183). **retryable=False + pausable=False** block durable retry/pause.
- `submit_analysis(filepath)` exists (71-79): op ANALYSIS ("analysis"), payload {"filepath"}, calls `self._analysis.analyze_file(filepath)`.
- `_durable_to_public` (311-344): status = `str(state).lower()` (NOT through QML_STATE_MAP → SUCCEEDED becomes "succeeded" not "completed").
- `_DURABLE_TITLES` (26-32) has ANALYSIS → "Análisis técnico".
- **GAP**: durable path is ORPHANED (bridge never calls adapter.submit_*; only tests) and BROKEN in production — `start_job` fails with "No handler for type: analysis" because no handler is registered (§6). In-memory WM path (191-234) is test/backcompat only.

### 5. AudioLabService (core/audio_lab/audio_lab_service.py, 346 lines)
- Composed in core/composition/audio_lab.py:16-23 with `job_service=container.get("job_service")`; `setup()` (97-143) builds modules incl. `AudioAnalysisService` + `AudioLabJobAdapter(db, wm, job_service=..., probe/analysis/...=...)` (128-140). Module properties: `analysis`, `conversion`, `replaygain`, `integrity`, `comparison`, `jobs` (= adapter).
- `AudioAnalysisService` (core/audio_lab/audio_analysis_service.py, 160 lines): `analyze_file(filepath) -> dict` (50-83) — synchronous, NO ctx param, NOT cancellation-aware. Result: `{filepath, status, error, explanation, features{...}, codec, format, sample_rate, bit_depth, channels, bitrate, duration, loudness, peak, clipping, silence, checksum, decode_status, track_key}`; status ∈ {"ok","error","unsupported","disabled","unknown"}. **`AudioLabAnalysisService` does NOT exist** — class name is `AudioAnalysisService`.

### 6. DurableJobService (core/jobs/job_service.py, 662 lines; re-exported as JobService in core/job_service.py)
- Public API: `create_job(job_type, owner="", payload=None, total=0, cancellable=True, pausable=True, retryable=True) -> str` (199-221); `start_job(job_id) -> bool` (223-243); `pause_job`/`resume_job` (334-355); `cancel_job(job_id) -> bool` (357-379); `retry_job(job_id) -> bool` (381-407, **same id**: FAILED/INTERRUPTED/CANCELLED → QUEUED with ORIGINAL payload → start_job); `get_job(job_id)` (445); `list_jobs(state, job_type, owner, limit=100)` (448-460); `delete_job(job_id)` (508-516, terminal only); `process_queue` (465-474); `cancel_owner`/`cancel_scope` (485-506); `register_handler` (196-197); `resume_pending_jobs` (174-194).
- States (39-49): QUEUED, RUNNING, PAUSING, PAUSED, CANCELLING, CANCELLED, SUCCEEDED, PARTIAL_SUCCESS, FAILED, INTERRUPTED. Restart: RUNNING→INTERRUPTED, CANCELLING→CANCELLED (139-172); `resume_pending_jobs` FAILs handler-less QUEUED jobs with `HANDLER_UNAVAILABLE` (190-192).
- Signals: jobCreated(str), jobStarted(str), jobProgress(str,float), jobPaused, jobResumed, jobCancelled(str), jobCompleted(str, object), jobFailed(str,str), queueChanged(int).
- TaskContext: `raise_if_cancelled()` (CancelledError), `report_progress(percent, message)`, legacy `progress_cb(current, total, message)`; `_SyncContext` (81-103) for the no-WM path.
- Result contract (`_finalize_handler_result` 312-332): dict with `partial` → PARTIAL_SUCCESS; dict → SUCCEEDED; exception → FAILED; CANCELLING → CANCELLED.
- Owner/type conventions: owners "audio_lab", "device_sync", "history_bridge", "job_bridge", "jobs"; types library_scan, library_scan_all, metadata_scan, metadata_batch, doctor_scan, doctor_repair, history_export, mix_generate, device_sync, device_transfer, playlist_import.

### 7. Handlers + registration
- core/jobs/handlers.py (330 lines): PURE factories `make_*_handler(port)`; JOB_TITLES (20-31) lacks "analysis". Pattern: `ctx.report_progress(0.1,...)` → `ctx.token.raise_if_cancelled()` → port call → raise_if_cancelled → `report_progress(1.0)` → return result; RuntimeError on None port/error; `result["partial"]=True` for partial (e.g., make_mix_generate_handler 211-238, make_playlist_import_handler 241-272).
- `register_production_job_handlers(job_service, container)` in core/composition/jobs.py:162-204 — registers 11 types, NO audio lab. `_build_ports` (126-159) builds ports from composed services. Composition order (core/application_bootstrap.py): audio_lab (line 86) BEFORE jobs (line 100) — an analysis port can close over `container.get("audio_lab_service").analysis`.
- `AudioLabPort` protocol EXISTS in core/jobs/ports.py:113-128 — "reserved — Fase Audio Lab", `probe(filepath, ctx)` + `analyze(filepath, ctx)`.
- Gate `tests/architecture/test_handlers_no_service_construction.py`: handlers.py imports only stdlib; no service construction/container.get in handlers (ADR-004).

### 8. Job types & enums
- `AudioLabOperation.ANALYSIS = "analysis"` (core/audio_lab/audio_lab_contracts.py:11-22). AudioLabJobStatus (25-32): queued/running/cancel_requested/cancelled/completed/failed/interrupted. No durable "analysis" type registered anywhere; core/jobs/job_types.py JobType is LEGACY vocabulary.

### 9. Test inventory (scope)
- EXISTS: tests/architecture/test_audio_lab_uses_durable_jobs.py (3 tests — adapter durable submit, not-in-memory, INFRASTRUCTURE_UNAVAILABLE); tests/integration/jobs/test_audio_lab_scope.py (1 test — cancel scoping vs device_sync, real WM).
- tests/qml/audio_lab/ (23 files): test_audio_analysis.py, test_audio_analysis_advanced.py, test_audio_analysis_batch.py, test_audio_conversion.py, test_audio_integrity.py, test_audio_jobs.py, test_audio_keyboard.py, test_audio_lab_analysis_v2.py, test_audio_lab_completo.py, test_audio_lab_home.py, test_audio_lab_hub_five_cards.py, test_audio_lab_integrity_comparison.py, test_audio_lab_orchestrated.py, test_audio_lab_orquestado.py, test_audio_lab_overview.py, test_audio_lab_replaygain_v2.py, test_audio_lab_service.py, test_audio_lab_v12.py, test_audio_negative.py, test_conversion_async_qprocess.py, test_conversion_cancel_qprocess.py, test_jobs_persistence.py, test_replaygain.py.
- Bridge tests asserting LOCAL-registry semantics (RED under durable migration): test_audio_lab_completo.py:106-201 (job_id.startswith("analysis_"), cancelJob ok, retryJob new_job_id, cleanupCompleted mutates `bridge._active_jobs`, jobStatus, activeJobs()); test_audio_negative.py:42-58 + 97-101 (JOB_NOT_FOUND / NOT_FAILED / cleaned=0 / SERVICE_UNAVAILABLE).
- Others: tests/test_audio_lab_bridge.py (minimal), test_audio_lab_setup.py, test_audio_lab_routes_contract.py, test_audio_lab_capture_contracts.py (startAnalysis 199/209), tests/qml/productive_workflows/test_audio_lab_analyze_convert.py (bootstrap smoke), tests/qml/functional/test_bridges.py, tests/qml/workflows_specialized/test_audio_lab_orchestrated.py, tests/qml/workflows/* (analyzeFile usages).

### 10. Other references
- core/audio_lab/periodic_analyzer.py: calls `diagnostics_service.analyse_file(fp)` directly (NOT durable) — out of scope.
- core/audio_lab/job_controller.py: legacy AudioLabJobController (unused by bridge/adapter path).
- core/audio_lab/audio_lab_sync.py: `sync_audio_lab_result_to_media_item(db, fp, result)`.
- JobService canonical: core/job_service.py re-exports DurableJobService; container registers it in core/composition/infrastructure.py:57.

## Gaps (M1.1 build/change list)
1. Handler factory `make_analysis_handler(port)` in core/jobs/handlers.py (stdlib-only, pure, closes over port; progress + raise_if_cancelled; error status → raise; result dict returned verbatim) + JOB_TITLES["analysis"].
2. Port: implement reserved `AudioLabPort.analyze(filepath, ctx)` (ports.py:113) or dedicated AudioLabAnalysisPort; composition closes over `AudioLabService.analysis`. analyze_file has no ctx — handler wraps cancellation around the call (cooperative only between phases).
3. Registration in core/composition/jobs.py: port in _build_ports + `register_handler("analysis", make_analysis_handler(port))`. TITLE_BY_TYPE["analysis"] in job_bridge.py.
4. Bridge convergence (audio_lab_bridge.py): startAnalysis → create_job("analysis", owner="audio_lab", payload={"request":{"filepath":...}}, cancellable=True, pausable=False, retryable=True) + start_job on injected job_service; subscribe to job_service signals, re-emit bridge jobProgress/jobCompleted/jobFailed (job_id, "analysis", payload); cancelJob → `_jobs.cancel_job`; retryJob → `_jobs.retry_job` (SAME id — UX change); cleanupCompleted → delete_job over terminal owner="audio_lab"; jobStatus/activeJobs → get_job/list_jobs(owner="audio_lab"); drop raw threading.Thread for analysis; keep degraded mode when no job_service.
5. Adapter alignment: retryable=True for analysis; `_durable_to_public` state mapping via QML vocabulary; ensure registration happens before submit.
6. Tests (strict TDD — RED first): handler unit tests; bridge-durable integration; registration test; extend tests/architecture/test_audio_lab_uses_durable_jobs.py + tests/integration/jobs/test_audio_lab_scope.py; update test_audio_lab_completo.py / test_audio_negative.py bridge expectations.
7. QML gate edge: AudioAnalysisPage.qml:64 `typeof jobId === "string"` vs `@Slot(result=dict)` — return a string job id (or update gate).

## Approaches
1. **Bridge → DurableJobService directly (recommended)** — startAnalysis creates/starts durable job; bridge subscribes to job_service signals and re-emits its own QML signals. Pros: single durable source of truth, persistence, cooperative cancel (WM), matches JobBridge pattern; Cons: small mapping layer stays in bridge; Effort: Medium.
2. **Bridge → AudioLabJobAdapter.submit_analysis** — delegate to existing adapter durable path. Pros: adapter already encodes titles/payload/durable→public mapping (fix retryable + registration); Cons: adapter orphaned/broken today (no handler), extra layer, adapter signals need QML shaping; Effort: Medium.
3. **Extend JobBridge** — QML consumes jobBridge uniformly. Pros: uniform job UI; Cons: larger QML/route refactor, bigger blast radius; Effort: High.

## Recommendation
Approach 1 (bridge → DurableJobService directly), reusing the adapter's payload/title conventions (`type="analysis"`, owner="audio_lab", payload={"request": {"filepath": ...}}). Handler + registration land FIRST (same slice) to avoid "No handler for type". Keep the bridge's public QML API stable; only the backing store changes. Update RED tests per strict TDD.

## Risks
- Enabling the durable path before registering the handler → every analysis job fails with "No handler for type: analysis".
- analyze_file is synchronous, non-cancellation-aware — cancellation only between progress points.
- Existing bridge tests assert local-registry semantics (job_id prefixes, cleanup counts, retry new-id, _active_jobs mutation) — breaking test contract, RED first.
- Retry semantics change (new id → same id) alters QML UX; verify no path depends on new_job_id.
- QML `typeof jobId === "string"` gate — QVariantMap is an object; must return a string job id or update the gate.
- Scope discipline: only "analysis" is converged; replaygain/integrity/comparison/conversion/rip/recording_split stay on `_start_background_job`.
- Shared WorkerManager pool (max_concurrent=4) — analysis competes with scan/mix/device_sync (observable, acceptable).
- Architecture gates: handlers.py stdlib-only; no service resolution inside handlers.

## Ready for Proposal
Yes — orchestrator should tell the user: M1.1 is feasible on the existing DurableJobService with no schema changes; decisions needed: (a) delegation point bridge-vs-adapter (recommended: bridge directly, adapter aligned), (b) retry same-id UX change, (c) cooperative-only cancellation for synchronous analyze_file, (d) expected break of existing bridge tests (RED first per strict TDD).
