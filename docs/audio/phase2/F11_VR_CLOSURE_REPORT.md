# F11 Visual Recovery — Closure Report (R1)

Verdict: **NO-GO for F11 closure**.
F11 remains **ACTIVE**. F10 is CLOSED. F12/F13/F14/F15 remain LOCKED; F14
NOT_RUN. This sprint improved the truthful UI but did not certify the full
active-runtime visual matrix.

## Delivered

- Signal Truth temporal integrity: ACTIVE / PENDING / HISTORICAL / NOT_ACTIVE,
  no historical-as-current collapse.
- Processing stage is `transformed` only with an effective plan id matching the
  snapshot; draft EQ bands are no longer used as truth.
- Dynamic resample/channel-remap/FIR stages only from observed evidence.
- Shared `MichiSignalPathView` and first/last rail semantics; status glyph,
  token and accessible text.
- NowPlaying indicator bound to Signal Truth, not `hasTrack`.
- Quick EQ state machine: Draft/Applying/Effective/Bypassed/Error, busy edit
  guards, calculated 256-point response from canonical RBJ coefficients.
- Bootstrap EQ signal uses active decoded PCM only; no library-metadata F32LE.
- Advanced Graphic gate replaces 31 dead chips with a compact capability card.
- Sidebar recursive backdrop blur disabled; smoked material/grain/shadow kept.

## Evidence

- `F11_VR_BASELINE.md`, `F11_VR_CONTRACTS.md`, `F11_VR_SIGNAL_TRUTH_SPEC.md`,
  `F11_VR_UI_SPEC.md`, `F11_VR_LEGACY_EQ_EXTRACTION.md`,
  `F11_VR_PERFORMANCE.md`, `F11_VR_RISK_REGISTER.json`.
- `F11_VR_VISUAL_AUDIT.json` + `evidence/f11/2026-11-02-f11-vr/`.
- Targeted suite: 236 passed; bridge/response/biquad/QML contracts all green.
- Full suite at `64d9f34`: 6444 passed, 41 skipped, 0 failed (31:03).
- Productive DSP bridge test: 5 passed including a real hosted GStreamer graph.

## Why NO-GO

1. No active-playback Signal Truth capture. The isolated library was empty and
   the native folder dialog did not accept a path in the automated session.
2. The KWin sidebar W1-W9 isolation matrix was not executed; only post-fix
   compact/stress captures were reviewed.
3. High-contrast capture was attempted but did not visually change in the
   isolated session, so it is recorded NOT_RUN rather than claimed.
4. Advanced Graphic31/FIR/Profiles CRUD remain capability-gated; no live
   edit/readback path is certified.
5. Quick EQ during DSD-to-PCM has no decoded-PCM provider in the presentation
   composition; it fails closed.
6. No automated pixel/perceptual golden or physical DAC/bit-perfect claim.

## Next gates

- Capture ST-02/03/07/08/09/11 with a real or explicitly LAB playback fixture.
- Execute W1-W9 and a high-contrast/reduced-motion matrix.
- Implement Advanced PEQ/Graphic editing only after a proven Graph→Host→Readback
  contract; keep FIR/Profiles gated until F13 asset/profile authority exists.
- Run full suite, AP2-F11/DAC gates, push, and exact-SHA CI before any closure
  decision.
