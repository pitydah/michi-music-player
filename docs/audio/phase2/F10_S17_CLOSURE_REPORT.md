# AP2-F10 S17 — Remaining blockers resolved

## Verdict

- **F10: CLOSED** for the F10 normative scope.
- **F11: ACTIVE**.
- **F12 / F13 / F15: LOCKED**.
- **F14: NOT_RUN** as a formal independent phase.
- No analog audibility or bit-perfect claim.

## Baseline

| Item | Value |
|---|---|
| Base HEAD | `c283707` |
| Phase | AP2-F10 ACTIVE / READY_FOR_CLOSURE_REVIEW |
| CI before S17 | `41348558745` at `c283707`, 4/4 success |

## Blocker 1 — PAUSED/EOS live DSP convergence

Test: `tests/audio_phase2/test_dsd_pcm_paused_eos.py`

Command:

```bash
env -u MICHI_GST_LAB_SINK QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/audio_phase2/test_dsd_pcm_paused_eos.py -q
```

Result: **2 passed**.

- DSP install/removal while the DSD→PCM pipeline is PAUSED fails closed with the typed code `DSP_PAUSED_REQUIRES_RESUME`.
- The previously installed graph remains installed; the playback status remains PAUSED; no autoplay occurs.
- After `resume()`, the processing transaction completes with negotiated caps and graph revision 3.
- EOS produces the Signal Truth event `dsd_pcm / UNAVAILABLE / detail=eos`; effective processing becomes `unavailable`; no second media is accepted; explicit STOP reaches IDLE.

Production change: `gstreamer_host_dsd_pcm.py` now tracks the live PAUSED state and refuses processing install/removal while paused instead of deadlocking on `filter_bin.set_state(NULL)`.

## Blocker 2 — physical T03/T04

Test: `tests/audio_phase2/test_f10_s17_physical_managed_dsd.py` (opt-in with `MICHI_PHYSICAL_DAC_TESTS=1`).

Command:

```bash
env -u MICHI_GST_LAB_SINK MICHI_PHYSICAL_DAC_TESTS=1 QT_QPA_PLATFORM=offscreen \
  python -m pytest tests/audio_phase2/test_f10_s17_physical_managed_dsd.py -q
```

Result: **2 passed**.

Device:

- SMSL USB AUDIO, stable ID `usb:152a:85dd:3-3.3.2`.
- Hardware locator `hw:CARD=AUDIO,DEV=0`.
- Hardware formats: `S32_LE`, `DSD_U32_BE`.
- Physical locator used: `plughw:CARD=AUDIO,DEV=0` because the DAC does not expose F32LE at `hw`; the DSD→PCM terminal contract remains F32LE and ALSA performs the final conversion.

T03 `PCM_MANAGED → DSD_TO_PCM`: PASS. Exact predecessor release receipt (`confirmed`, `RELEASED`, `SUPERVISED_HOST`, exact plan/execution, device `plughw:CARD=AUDIO,DEV=0`), target RUNNING, PLAYING, STOP → IDLE.

T04 `DSD_TO_PCM → PCM_MANAGED`: PASS with the symmetric exact release receipt and target RUNNING/PLAYING/STOP → IDLE.

Caveats:

- Analog audibility remains `REQUIRES_OPERATOR_CONFIRMATION`.
- No bit-perfect or physical DAC certification claim.
- The test injects the physical `plughw` locator into the productive fake-topology device; the host chain, ALSA sink and DAC are real.
- F14 remains NOT_RUN as a formal phase.

## Other gates

- `python -m ruff check` on all touched files: PASS.
- `python -m ruff format --check` on all touched files: PASS.
- F06/F08/F09 regressions are unchanged by this slice; the focused DSP/managed/owner-safe batch was re-run (25 passed, 9 skipped where lab env is required).
- AP2-F10 repository alignment gate: to be re-run after the state transition.
- DAC V3.5 alignment gate: to be re-run after the state transition.

## §196.7

| Criterion | Status |
|---|---|
| Complete executed decision table | PASS |
| New path snapshot per transition | PASS |
| Policy/runtime coherence after failures | PASS |
| STOP/PAUSE/REPLAY convergence | PASS |

## §415

| Criterion | Status |
|---|---|
| Newer request wins | PASS |
| No autoplay after non-playing predecessor | PASS |
| No false predecessor restore | PASS |
| Explicit DSD→PCM representation | PASS |

## Final statement

The two remaining F10 evidence blockers are resolved with executed tests. F10 is closed within its normative scope; F11 is active. F14 remains NOT_RUN and no physical/analog certification is claimed.
