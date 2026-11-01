# AP2-F10 S14 — Closure Readiness

**Verdict: NOT_READY**

## Implemented
- Cut 1 — single-flight physical release reservation per exact execution.
- Cut 2 — committed Direct predecessor released with an identity-bound receipt before a DSD target prepares.
- Cut 3 — Native DSD <-> DSD->PCM Qt+host E2E (T05/T06); Managed cross-family remains partial.
- Cut 5 — DSD64 v3 numeric harness: criterion status model, certification flag, DC, isolated stopband sweep, response, channels, latency, profiles.
- Cut 7 — physical DAC ALSA-runtime evidence on SMSL and KINMAX.

## Remaining
- T03/T04 — Managed <-> DSD->PCM Qt+host E2E. Requires a real managed plan, terminal evidence and processing authority; current code proves managed playback independently.
- Cut 4 — DSP/quality T09/T10/T11 productive tests (ON->OFF->ON, A->B->A, STOP/PAUSED/EOS/stale binding/host restart).
- Cut 6 — adversarial Qt release/prepare barriers, duplicate release, host restart, binding ABA, disconnect, late callback, START failure.
- Cut 9 — full `pytest tests/ -q` after the Cut 5 harness rewrite, DAC/Qt/GStreamer/wheel gates and exact-SHA CI.

## §196.7
- Complete executed decision table: PARTIAL.
- New path snapshot per transition: PARTIAL.
- Policy/runtime coherence after failures: PASS.
- STOP/PAUSE/REPLAY convergence: PARTIAL.

## §415
- Request freshness: PASS.
- No autoplay after non-playing predecessor: PASS.
- No false restore after destructive boundary: PASS.
- Explicit DSD->PCM representation: PASS.

F14 remains **NOT_RUN**. F11-F15 remain **LOCKED**. F10 is not CLOSED.

## T03/T04 Managed Qt+host — BLOCKED

- Reproducer: `tests/audio_phase2/test_f10_s14_managed_qt_host_e2e.py`, strict xfail.
- Observed: managed prepare succeeds (44.1 kHz / 2 ch / S16_LE), then
  `query_managed_identity()` returns `{'managed': False}`; the handover release returns
  `MANAGED_STOP_STALE` (`no managed execution is current`) and the owner publishes
  `OUTPUT_OWNERSHIP_UNCONFIRMED`.
- Root cause: `PlaybackService._continue_prepared_load` calls `AudioTransportRouter.load`
  before `OutputSessionService.commit_media`; the router has no managed branch, so the
  managed host execution is not addressable for release.
- Retained production fixes (`f84c6e5`): managed `transition_snapshot()` publishes
  plan/execution identity; managed SOFTWARE volume authority is `MICHI_SOFTWARE`.
- Blocker record: `docs/audio/phase2/F10_S14_BLOCKERS.json`.
- Verdict remains **NOT_READY**.

## Cut 4 / Cut 6 partial closure (2026-11-01)

- Cut 4 `PARTIAL`: T09/T10 are proven by the productive DSD->PCM DSP tests; T11 is proven by the same-family handover matrix test. Missing extended OFF->ON->OFF, A->B->A, PAUSED, EOS, stale-binding and host-restart scenarios.
- Cut 6 `PARTIAL`: the nine adversarial/Qt tests cover release rejection, foreign receipt, host restart, STOP during RELEASE/PREPARE, device-selection ABA, prepare failure after RELEASE, A->B->C and a free Qt loop. Missing PAUSED, duplicate release, START failure, DAC disconnect and late-callback recovery.
- Combined verification: `20 passed, 1 warning in 5.85 s` (fakesink lab, real DSP host).
