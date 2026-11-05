# F11 Closure Readiness

Verdict: **NO-GO for closure after KILLCRITIC X10 Visual Recovery R1**.
F11 status: **ACTIVE**. See `F11_VR_CLOSURE_REPORT.md` for the current
active-runtime and KWin gaps. The previous `84c7c3c` CI remains historical
certification of the earlier surface, not of the new visual-recovery code. F10: **CLOSED**. F12/F13/F14/F15: **LOCKED**; F14
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
- Official Tabler SVG route-icon family at 24 px with `Shape.CurveRenderer`
  and no manual scale for engines, DAC, jack, display audio, USB/internal and
  shared output.

## Evidence

- Design contract: `docs/audio/phase2/F11_DESIGN_CONTRACT_R9.md`.
- Work log: `docs/audio/phase2/F11_WORK_LOG.md`.
- Visual audit: `docs/audio/phase2/F11_VISUAL_AUDIT.json`.
- UI contract evidence: `docs/audio/phase2/F11_UI_CONTRACT_EVIDENCE.json`.
- Screenshots: `evidence/f11/2026-11-01-f11-surfaces/` (12 PNGs).
- Commits: `95db637`, `c891a7e`, `dd02a8f`, `83a5272`, `41b454d`,
  `484925b`, `a19fdf5`, `d883a03`, `db25e75`, `396de6d`, `b829a8a`,
  `6c6c78a`, `0b26241`, `cce711a`.
- Mandatory CI gate: `F11 audio surfaces and bridges (mandatory, no skips)`.

## Verification already passed

- `test_f11_audio_processing_bridge.py`: 13 passed.
- `test_f11_signal_path_bridge.py`: 3 passed.
- `test_f11_processing_bridge_productive.py`: 1 passed against a real hosted
  GStreamer fakesink graph.
- `test_f11_qml_contract.py`: 8 passed.
- `test_f11_kwin_visual_contract.py`: 3 passed.
- Mandatory F11 gate: 28 passed in 31.17 s, zero skips.
- Targeted QML/runtime regression batch: 205 passed, 3 warnings.
- Full suite at `cce711a`: **6430 passed, 41 skipped, 0 failed**, exit 0,
  in 2000.46 s (33:20).
- Ruff check and format: clean.
- AP2-F11 alignment gate: GO.
- DAC repository alignment gate: OK.
- KWin visual review in the prior sprint: full, compact, narrow, stress, high
  contrast and reduced motion, plus all five audio surfaces. The new
  visual-recovery captures are idle-only and documented separately.

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
| 10. Full/compact/narrow + KWin review | PARTIAL — idle/compact/stress captured; active playback and W1–W9 NOT_RUN |
| 11. F06/F10/DAC/AudioEngine/M9 regressions | PASS |
| 12. Exact-SHA CI | PASS (`41375199479`, `7bd75a0`) |

## Why not CLOSED yet

- The exact-SHA CI on the final commit must complete; the repository-wide
  suite already passes locally at `cce711a`.
- Exact-SHA CI at `7bd75a0` is 4/4 green (`check`, `dac-v35-software-closure`, `dop-native-gate-a`, `min-qt`).
- Advanced Graphic, Convolution/FIR and Profiles CRUD remain capability-gated.
  The UI is honest about the missing authority, but a future F11 follow-up may
  connect them when the backend contracts exist.
- Quick EQ during DSD→PCM currently has no decoded-PCM signal provider in the
  presentation composition; the bridge refuses instead of claiming a
  transform it cannot prove.
- KWin captures are sprint evidence; there is no automated pixel-diff golden.
- F14 remains NOT_RUN and F12/F13/F15 remain LOCKED.

No test was disabled, weakened or skipped to obtain this result.


## KILLCRITIC X10 follow-up (2026-11-02)

The earlier READY_FOR_CLOSURE_REVIEW verdict was based on idle captures and
hash-only visual checks. KILLCRITIC found active/historical collapse, a
`hasTrack` success indicator, fixed five-stage rail semantics, Quick EQ
draft/effective ambiguity, Advanced dead chips and sidebar artifacts.

Visual Recovery R1 corrected the authority and surface defects and recorded
honest evidence in `F11_VR_*`. It remains **NO-GO** until active playback
ST-02/03/07/08/09/11, the sidebar W1–W9 matrix, high-contrast/reduced-motion
captures, Advanced capability contracts and new exact-SHA CI are complete.

## Visual Recovery R2 (2026-11-02)

R2 addresses the pointer-authority defect and the remaining surface gaps from
the R2 design/QA brief:

- popups are modal without dimming and consume outside clicks; the underlying
  library row is never activated;
- Signal Truth nodes have exclusive pointer and keyboard handling, semantic
  stage pictograms and independent evidence microbadges;
- the stage rail is dynamic and preserves first/last semantics;
- Advanced Graphic10 and PEAK10 editors share the canonical quick draft, and
  preset loading only loads a draft;
- FIR and Signal / Resampling remain read-only, capability-gated views;
- footer Apply/Discard appear only for editable tabs;
- engine and output popups use the route icon and route selection skin system;
- NowPlaying carries the integrated historical/active Signal Truth capsule;
- the header shows `DSP detected · identity unverified` when a DSP is detected
  without a verified identity.

Evidence: `docs/audio/phase2/F11_VR_R2_EVIDENCE.json`. KWin pointer captures are
SHA-pinned in `evidence/f11/2026-11-02-f11-vr/`. The pointer matrix passed
Source click, ten consecutive chevron toggles and outside-click consumption,
with the active track unchanged and the library row not activated. Scroll and
full keyboard traversal remain **NOT_RUN**. R2 code and tests are in commit
`c5635e6`.

R2 targeted verification: pointer guard 10 passed; combined R2 batch 226
passed; QML/runtime regression 182 passed; productive hosted EQ 1 passed;
mandatory F11 CI gate 49 passed in 31.11 s with zero skips; full suite
**6457 passed, 41 skipped, 0 failed (exit 0, 1916.19 s)**; ruff
check/format and `git diff --check` clean. Exact-SHA CI run `41567906735` at
`d94991a7f1dd13536f8646b5577e6fa21af09f05` completed 4/4 success (`check`,
`min-qt`, `dac-v35-software-closure`, `dop-native-gate-a`).

R2 does not change the verdict: **NO-GO / F11 ACTIVE**. The open gates remain
active DSD/DoP/DSP-effective captures, the sidebar W1–W9 matrix, high-contrast
and reduced-motion captures, Advanced backend contracts, the DSD→PCM quick-EQ
signal provider, an automated pixel/perceptual golden, and new exact-SHA CI.

## Visual Recovery R3 (2026-11-03)

R3 closes two concrete truth/geometry defects found on the live production UI:

- Signal Truth no longer clips its fixed header at 900×600. The popup is
  parented to `Overlay.overlay`, clamped inside the overlay, keeps a 560 px cap
  and scrolls its stage body. Commit `9a468bf`.
- Effective DSP no longer reports `DSP detected · identity unverified` merely
  because the processing plan id differs from the output plan id. The bridge
  correlates the latest readback-proven processing event by pipeline generation
  and publishes plan, revision and pipeline generation. Commit `8a94acd`.

R3 KWin evidence: active PCM Direct and live quick-EQ both captured on the real
SMSL DAC through `alsasink`; keyboard traversal, Enter disclosure and Escape
focus return passed; vertical scroll did not change the track. Captures and
hashes are recorded in `docs/audio/phase2/F11_VR_R3_EVIDENCE.json` under
`evidence/f11/2026-11-03-f11-vr-r3/`.

Honest remaining failures:

- Native DSD playback is active but Signal Truth has no native recorder
  snapshot, so the popup stays Pending/Unknown.
- DoP qualification failed in the isolated session with
  `DOP_QUALIFICATION_FAILED: probe deadline exceeded`.
- DSD→PCM failed with `DSD_PCM_TARGET_UNQUALIFIED: PCM target is not qualified`
  for the `hw` SMSL binding.
- The sidebar W1–W9 isolation matrix, Advanced PEQ/FIR/Profiles CRUD and an
  automated pixel golden remain NOT_RUN.

R3 does not change the verdict: **NO-GO / F11 ACTIVE**.

## Visual Recovery R6 (2026-11-03)

VR-R6 replaces the remaining string-driven quality badge with typed source
quality and a separate path-proof state, measures Signal Truth against the
opener at four viewports, and turns Signal Truth and Advanced EQ into coherent
inspector surfaces. The quick EQ preset row is horizontally bounded so ten
rails fit the 440 px popup, and the engine popup is clamped inside the overlay.

Evidence: `docs/audio/phase2/F11_VR_R6_EVIDENCE.json` and
`evidence/f11/2026-11-03-f11-vr-r6/` (8 SHA-pinned captures plus clean KWin
runtime log).

Honest limits: human screenshot review, pixel/perceptual goldens, DPI scales
above 100 %, physical DAC re-qualification and the capability-gated Advanced
features remain NOT_RUN. R6 does not close F11; the verdict remains
**NO-GO / F11 ACTIVE**.

## Visual Recovery R7 (2026-11-03)

VR-R7 makes the Signal Truth inspector intrinsic to its five stages, with a
bounded short-window fallback instead of a permanent scroll box. Proof wording is
now strictly separated from the four observed evidence parts, stage certainty is
a microdot rather than repeated checkmarks, and stage configuration is an
independent capability-gated action. The NowPlaying card gains optical mass
(96 px card, 72 px artwork) without changing the 154 px bar or transport.

Evidence: `docs/audio/phase2/F11_VR_R7_EVIDENCE.json`, commit `879099c`.
Verification: pointer guard + R7 + QML contract + R6 evidence `32 passed`;
F11/QML regression `228 passed`; full suite `6479 passed, 41 skipped, 0
failed` in 1931.53 s.

Honest limits: KWin MCP was unavailable, so R7 screenshots and DPI scaling are
NOT_RUN; qmlformat/qmltestrunner are Qt 5-only in this environment; profiler p95
is NOT_RUN. F11 remains **NO-GO / ACTIVE**.
