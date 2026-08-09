# Proposal: M1.1 Audio Lab Analysis Durable Job Convergence

## Intent

Replace Audio Lab analysis's local thread registry with `DurableJobService`. Jobs must survive restarts, resume at startup, appear in generic Jobs, retry with the same ID, and support cooperative cancellation.

## Scope

### In Scope
- Register durable `analysis` jobs owned by `audio_lab` with their original payload.
- Move `AudioLabBridge` analysis start/status/cancel/retry/cleanup to `DurableJobService` while preserving QML signals.
- Add the analysis title to `JobBridge`; align `AudioLabJobAdapter` retry and state mapping.
- Validate `resume_pending_jobs`, unified visibility, same-ID retry, and cancellation checkpoints.

### Out of Scope
- Migrating conversion, ReplayGain, integrity, comparison, CD ripping, or marker splitting.
- Interrupting synchronous `AudioAnalysisService.analyze_file()` mid-call.
- Schema changes, pause support, or Jobs UI redesign.

## Capabilities

### New Capabilities
- `durable-audio-analysis-jobs`: Persistent analysis lifecycle, recovery, visibility, retry, cancellation, and QML bridge behavior.

### Modified Capabilities
None.

## Approach

Use the recommended direct path: `AudioLabBridge` creates and starts `analysis` jobs on `DurableJobService`, then maps canonical signals and states to its existing QML contract. Add a pure handler and injected Audio Lab port, register them before pending jobs resume, and persist payload `{request: {filepath}}` with owner `audio_lab`. Align, but do not delegate through, `AudioLabJobAdapter`.

Apply strict RED-GREEN-REFACTOR slices: handler/registration, bridge lifecycle, adapter/Jobs visibility, then restart and productive-path validation. Keep tests with each work unit.

### Alternatives Considered
- Delegate through `AudioLabJobAdapter`: unnecessary extra mapping through an orphaned path.
- Move analysis UI to `JobBridge`: better unification, but excessive QML blast radius for M1.1.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `core/jobs/handlers.py`, `core/jobs/ports.py` | Modified | Handler, title, injected port |
| `core/composition/jobs.py` | Modified | Registration before recovery |
| `ui_qml_bridge/audio_lab_bridge.py` | Modified | Durable lifecycle and signal mapping |
| `core/audio_lab/audio_lab_job_adapter.py` | Modified | Retry/state alignment |
| `ui_qml_bridge/job_bridge.py` | Modified | Generic Jobs title |
| `tests/` | Modified/New | Handler, bridge, restart, QML contracts |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| Resume precedes handler registration | Medium | Register before `resume_pending_jobs` |
| Cancellation is delayed mid-analysis | High | Document limitation; check between handler steps |
| Tests encode local/new-ID behavior | High | Change contracts test-first; preserve QML signals |
| QML rejects non-string job ID | Medium | Return a string and test the productive path |

## Rollback Plan

Revert handler registration and bridge delegation together, restoring only analysis to local execution. No schema rollback is needed.

## Dependencies

- Existing `DurableJobService`, `WorkerManager`, startup recovery, and `AudioAnalysisService`.

## Success Criteria

- [ ] Pending analysis jobs survive restart and resume with original payload.
- [ ] Analysis appears in generic Jobs with canonical state and title.
- [ ] Retry preserves ID; cancellation is observed at checkpoints.
- [ ] Productive QML flow, focused tests, and `scripts/test_gate.sh` pass.
