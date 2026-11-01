# AP2-F10 S16 — Closure Readiness

**Verdict: READY_FOR_CLOSURE_REVIEW**

F10 stays **ACTIVE** until the exact-SHA CI and the canonical phase transition
are executed. F11–F15 stay **LOCKED**. F14 stays **NOT_RUN** as an independent
qualification phase.

## Implemented in S16

- **Asynchronous Managed adoption.** `CLAIM_PRELOADED_MANAGED` runs on a worker
  and completes on the owner loop. The owner never blocks on the host claim.
- **Commit / acceptance split.** `_commit_pending_output_once` performs the
  `OutputSessionService.commit_media` authority step. Acceptance is published
  only after the managed START is confirmed by `managed_active` and
  `notify_managed_playing`.
- **Exact pipelined claim.** `PreloadedManagedClaim` carries the observed
  `pipeline_generation`; owner and host reject a missing, stale or replaced
  generation. The claim is single-use.
- **T03/T04 remain PASS** on the real `PlaybackService -> OutputSessionService ->
  AudioTransportRouter -> GStreamerHostedAudioPort -> GStreamerHostSupervisor`
  chain with `fakesink` laboratory sink.
- **Live DSP reapply.** `DSP_CAPS_NOT_NEGOTIATED` is closed: a live DSD→PCM
  processing reapply negotiates working caps, and OFF→ON→OFF→ON publishes
  graph revisions 2 and 3 as effective.
- **QUALITY A→B→A.** Same-family quality changes release the exact predecessor,
  prepare the new plan and publish a fresh output snapshot per transition; a
  stale binding is rejected before the destructive release.
- **Managed adversarial.** Late A/B/C completions never commit or accept;
  STOP, PLAY failure, commit failure, unconfirmed START and DAC disappearance
  never publish acceptance; Qt keeps ticking while CLAIM is held.

## Evidence

- `docs/audio/phase2/F10_S16_TRANSITION_MATRIX.json`
- `docs/audio/phase2/F10_S16_EVIDENCE.json`
- `tests/audio_phase2/test_managed_adoption_async.py` (7 tests)
- `tests/audio_phase2/test_managed_preloaded_claim.py` (7 tests)
- `tests/audio_phase2/test_f10_s14_managed_qt_host_e2e.py` (T03/T04)
- `tests/audio_phase2/test_dsd_pcm_dsp_reconfiguration.py` (live OFF→ON→OFF→ON)
- `tests/audio_phase2/test_family_handover_matrix.py` (T11 A→B→A)

## §196.7 — exit gate

- **Complete decision table:** PASS. T01–T12 have real evidence classes; T08 is an
  alias of T02 and is not duplicated.
- **New snapshot per transition:** PASS. T11 A→B→A asserts a new generation,
  plan and execution for each step; T03/T04 publish host transition snapshots.
- **Policy/runtime coherence after failures:** PASS. Release, prepare, adoption,
  commit and START refusals never publish acceptance or fake a predecessor.
- **STOP/PAUSE/REPLAY convergence:** PASS. PAUSED and STOPPED never autoplay,
  failed rollback converges STOPPED, and STOP during release, prepare or managed
  adoption never accepts a late completion.

## §415 — exit gate

- Request freshness: PASS.
- No autoplay after a non-playing predecessor: PASS.
- No false restore after the destructive boundary: PASS.
- DSD→PCM explicit and visible: PASS.
- Target family and generation checked: PASS.
- Transition receipts carry exact identities: PASS.

## Remaining limitations

- Physical T03/T04 qualification is NOT_RUN and belongs to the independent F14
  qualification process.
- PAUSED/EOS live quality cycles remain an evidence extension; they do not
  invalidate the §196.7 convergence gate already covered by the service and
  adversarial tests.
- No physical DAC certification or bit-perfect claim is made.

## Next action

Push with user approval, verify the exact-SHA CI (four jobs, six Qt+host E2E,
managed adoption/DSP/quality gate with zero skips), then execute the canonical
F10 → F11 transition only if every gate is green.
