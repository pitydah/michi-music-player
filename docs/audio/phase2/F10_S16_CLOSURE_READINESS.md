# AP2-F10 S16 — Closure Readiness

**Verdict: NOT_READY**

F10 stays **ACTIVE**. F11–F15 stay **LOCKED**. F14 stays **NOT_RUN** as an
independent qualification phase.

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

## Why NOT_READY

§196.7 is still PARTIAL:

- **Complete decision table:** PASS for T01–T12 with evidence classes.
- **New snapshot per transition:** PASS for the exercised family and quality
  transitions.
- **Policy/runtime coherence after failures:** PASS for the exercised release,
  prepare, commit, START and adoption failures.
- **STOP/PAUSE/REPLAY convergence:** PARTIAL. PAUSED/EOS live quality cycles
  remain an open evidence gap. PAUSED and STOPPED no-autoplay, STOP during
  release/prepare, DAC disappearance and stale-binding rejection are covered.

Physical T03/T04 qualification is NOT_RUN. No physical DAC certification or
bit-perfect claim is made. F14 remains NOT_RUN.

## Next work

1. Cover PAUSED and EOS across QUALITY A→B→A.
2. Re-run the full suite, repository gates and exact-SHA CI.
3. Only then evaluate canonical F10 closure and the F11 handoff.
