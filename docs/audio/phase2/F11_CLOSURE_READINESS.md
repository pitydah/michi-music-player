# F11 Closure Readiness

Verdict: **READY_FOR_CLOSURE_REVIEW**.
F11 status: **ACTIVE**. F10: **CLOSED**. F12/F13/F14/F15: **LOCKED**; F14
**NOT_RUN**.

This is a presentation phase. No physical DAC, analog audibility, bit-perfect
or F14 claim is made.

## Implemented

- `AudioProcessingBridge` and `SignalPathBridge`, owner-thread projections only.
- Basic equalizer with a real ten-band `ParametricEqNode` plus `PreampNode`,
  local drafts, real service commit and bypass.
- Signal Truth popup with five canonical stages and no future-only proof claims.
- Advanced equalizer with five tabs and honest capability-gated views.
- Audio Engine popup at 360 px and Audio Output popup at 380 px with
  selected/pending/active separation, icons, quick subtitles, recovery and
  focus return.
- Surgical NowPlaying slot migration preserving 154 px, track card, artwork
  and centered transport.
- Visual exclusivity across EQ, Advanced, Engine, Output and Truth.
- New Canvas icon taxonomy for engines, DAC, jack, optical, display audio and
  stream-cat.

## Evidence

- Design contract: `docs/audio/phase2/F11_DESIGN_CONTRACT_R9.md`.
- Work log: `docs/audio/phase2/F11_WORK_LOG.md`.
- Visual audit: `docs/audio/phase2/F11_VISUAL_AUDIT.json`.
- UI contract evidence: `docs/audio/phase2/F11_UI_CONTRACT_EVIDENCE.json`.
- Screenshots: `evidence/f11/2026-11-01-f11-surfaces/` (12 PNGs).
- Commits: `95db637`, `c891a7e`, `dd02a8f`.

## Verification already passed

- `test_f11_audio_processing_bridge.py`: 6 passed.
- `test_f11_signal_path_bridge.py`: 3 passed.
- `test_f11_processing_bridge_productive.py`: 1 passed against a real hosted
  GStreamer fakesink graph.
- `test_f11_qml_contract.py`: 7 passed.
- Targeted QML/runtime regression batch: 198 passed, 3 warnings.
- Ruff check and format: clean.
- AP2-F11 alignment gate: GO.
- DAC repository alignment gate: OK.
- KWin visual review: full, compact, narrow, stress, high contrast and reduced
  motion, plus all five audio surfaces.

## §197 status

| Criterion | Status |
|---|---|
| 1. Context/alignment/ownership | PASS |
| 2. All controls real or disabled with reason | PASS_WITH_CAPABILITY_GATES |
| 3. NowPlaying golden consciously reviewed | PASS |
| 4. Basic EQ exact contract | PASS |
| 5. Advanced EQ without simulated extras | PASS_WITH_CAPABILITY_GATES |
| 6. Engine/Output live binding and selected≠active | PASS |
| 7. Signal Truth observed facts only | PASS |
| 8. QML runtime warnings zero | PASS |
| 9. Keyboard/focus/screenreader/high contrast/reduced motion | PASS_WITH_AUTOMATED_AND_AT_SPI_EVIDENCE |
| 10. Full/compact/narrow + KWin review | PASS |
| 11. F06/F10/DAC/AudioEngine/M9 regressions | PENDING_FULL_SUITE |
| 12. Exact-SHA CI | PENDING |

## Why not CLOSED yet

- The repository-wide test suite and exact-SHA CI must complete on the final
  commit.
- Advanced Graphic, Convolution/FIR and Profiles CRUD remain capability-gated.
  The UI is honest about the missing authority, but a future F11 follow-up may
  connect them when the backend contracts exist.
- KWin captures are sprint evidence; there is no automated pixel-diff golden.
- F14 remains NOT_RUN and F12/F13/F15 remain LOCKED.

No test was disabled, weakened or skipped to obtain this result.
