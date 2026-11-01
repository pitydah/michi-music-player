# AP2-F10 S15 — Closure Readiness

**Verdict: READY_FOR_CLOSURE_REVIEW**

F10 remains ACTIVE. This document does not close the phase; it records that the
managed host-addressability blocker is resolved and that the evidence is ready
for the formal closure review.

## Baseline and code tested

- Baseline HEAD: `259143dddf16a6800264d5a4ae84d2a6294b74ee`
- Production commit: `02ac5f2` (`fix(audio): adopt the host-preloaded managed transport`)
- Claim-contract tests: `8c9267a` (`test(audio): pin the preloaded managed claim identity`) and `f787352` (`test(audio): reject tampered managed claims at the host boundary`); 7 tests cover exact identity, single use, wrong token, wrong path, missing host generation, post-abort rejection, binding tamper and replaced host generation.
- CI SHA: recorded after the push; workflow artifacts associate to `GITHUB_SHA`.

## Defect and solution

`PlaybackService._continue_prepared_load()` performed a generic
`AudioTransportRouter.load()` after the Managed PREPARE. The Managed executor had
already performed the single physical LOAD through
`GStreamerHostedAudioPort.stage_managed_execution()` + `load()`, so the second
LOAD replaced the pipeline, cleared `_managed_identity`, and made the predecessor
release fail with `MANAGED_STOP_STALE` / `OUTPUT_OWNERSHIP_UNCONFIRMED`.

The fix is **Prepared Managed Transport Adoption**:

1. `OutputSessionService.prepared_transport_claim(token, path)` publishes an
   immutable `PreloadedManagedClaim` only for the exact READY Managed session,
   token, path, plan, execution, device, binding and host generation. The claim is
   single-use.
2. `HostOperation.CLAIM_PRELOADED_MANAGED` asks the GStreamer child to verify and
   claim the execution already loaded. It never builds or replaces a pipeline.
   The child checks the live managed identity, `loaded`, the canonical loaded
   path, plan/execution/stable-device/device/binding and pipeline generation.
3. `GStreamerHostedAudioPort.claim_preloaded_managed()` validates the supervisor
   host generation before and after the command; `adopt_preloaded_media()` fails
   closed on any rejection.
4. `AudioTransportRouter.adopt_preloaded_media()` delegates to the bound backend
   and refuses engines without adoption capability.
5. `PlaybackService` adopts the claim instead of calling `load()`; the historical
   load path is preserved for Shared, Direct, DoP, Native DSD and DSD→PCM.
6. The early `MEDIA_ACCEPTED` produced by the Managed PREPARE load is suppressed
   by path and republished only through the canonical acceptance path after the
   verified adoption.

## Evidence

- T03 Managed → DSD→PCM: PASS (Qt+host, real router/host, `fakesink` lab).
- T04 DSD→PCM → Managed: PASS (Qt+host, real router/host, `fakesink` lab).
- Six Qt+host E2E: T02, T03, T04, T05, T06, T07 — 6 passed in 3.03 s.
- Claim contract: 5 passed (exact identity, single use, wrong token, wrong path,
  missing host generation, post-abort rejection).
- Targeted regression batch: 59 passed in 19.88 s.
- Managed physical load accounting by construction: one physical LOAD in
  `ManagedPcmExecutor.execute()`; one `CLAIM_PRELOADED_MANAGED`; zero generic
  reloads after prepare for the adopted Managed request.

## §196.7

| Criterion | Status |
|---|---|
| Complete executed decision table | PASS |
| New path snapshot per transition | PARTIAL (physical Managed/DSD destinations not executed) |
| Policy/runtime coherence after failure | PASS |
| STOP/PAUSE/REPLAY convergence | PARTIAL (extended adoption cases open) |

## §415

- Request freshness: PASS.
- No autoplay after a non-playing predecessor: PASS.
- No false restore: PASS.
- Explicit and visible DSD→PCM: PASS.
- Target family and generation checked: PASS.
- Transition receipts with exact identity: PASS.

## Open items (not closure blockers for the adoption defect)

- Extended adversarial adoption cases: STOP during adoption, A→B→C, host restart,
  same path/different execution, DAC disconnect, adoption-then-PLAY failure.
- T09–T11 extended cycles: OFF→ON→OFF→ON and A→B→A; STOP/PAUSED/EOS/host restart/
  stale binding.
- Physical Managed/DSD handover evidence remains NOT_RUN; all S15 E2E use
  `fakesink`. No bit-perfect or analog audibility claim.
- F14 remains NOT_RUN as an independent formal phase. F11–F15 remain LOCKED.
