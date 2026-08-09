# Proposal: M1.1 Audio Lab Analysis — Durable Job Convergence

## Intent

Migrate `analysis` (the only Audio Lab operation with a durable job handler) onto the canonical path:

```
AudioLabBridge → AudioLabJobAdapter → DurableJobService → handler → _AnalysisPort → AudioAnalysisService
```

Other Audio Lab operations (conversion, ReplayGain, integrity, comparison, CD rip, etc.) remain on their existing local execution paths. This baby step isolates the analysis migration end-to-end before duplicating the pattern.

## Approach

1. **Foundation (#201)**: Pure handler factory, fail-closed port, payload validation, production-handler registration before `resume_pending_jobs`.
2. **Bridge lifecycle (#202)**: Delegate through adapter; readback real state on start/cancel/retry; active-state projection; signal propagation with `dataChanged`.
3. **Adapter/restart (#203)**: Remove private `_handlers` access; normalize state projection; fix `created_at`; unify title; restart persistence tests.

## Success Criteria

- Real `AudioAnalysisService` status `"completed"` → handler success → `DurableJob SUCCEEDED`
- `error`, `unsupported`, `disabled`, `unknown`, empty, unrecognized → handler failure → `DurableJob FAILED`
- Progress 1.0 only emitted after successful validation
- Capacity exhaustion → `QUEUED`, not `HANDLER_UNAVAILABLE`
- Cancel RUNNING → `CANCELLING`; only `CANCELLED` when truly terminal
- No private API access (`_handlers`, `_job_to_dict`)
- One orchestration surface (Adapter), one execution authority (DurableJobService)
- Analysis never enters local `_active_jobs` or creates local threads
- T0 green; focused tests pass

## Scope Boundary

| In scope | Out of scope |
|---|---|
| Analysis durable migration | Integrity, ReplayGain, Comparison, Conversion, CD, etc. |
| Adapter delegation | Removing `_active_jobs` / `_threads` entirely |
| Readback on start/cancel/retry | Cooperative mid-analysis cancellation |
| Single jobStatus schema | Full inventory green |
