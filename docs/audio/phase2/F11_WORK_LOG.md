# F11 Work Log

Phase: AP2-F11. F10 is CLOSED. F11 remains ACTIVE until the formal closure
review and exact-SHA CI.

## Baseline

- Base HEAD: `fc7986c57f2242a561b47ca41042fd14de58281f`
- Phase gates: AP2-F11 spec sha
  `4f0e41eb6570527d40e2a40dff29e31214488efa8aed53d079320513122c6d12`;
  dependencies AP2-F02 / F03 / F06 / F10; alignment `GO`; DAC gate `OK`.
- QML preimage inspected before edits: NowPlayingBar 702 lines, Engine popup
  214, Output popup 263, AppShell 267, existing theme and primitive inventory.

## Implementation cuts

### F11-00 — baseline and preimage

- Confirmed the certified NowPlaying geometry: 154 px, no scroll, output grid
  four columns, track card 94 px, artwork 72 px, transport centered, compact
  threshold 1320, narrow threshold 980.
- Confirmed the existing token system already matched the R9 contract; no new
  theme was created.
- Confirmed app entry point `michi.__main__:main` and verified PySide6/Qt
  6.11.1 in the test interpreter.

### F11-01 / F11-02 — shared shell and bridges

- Added `AudioProcessingBridge`: draft/effective separation, exact ten-band
  graph, preset loading, DSD/DoP refusal, typed errors, owner-thread
  projection.
- Added `SignalPathBridge`: canonical five-stage projection, restricted
  headlines, no proof upgrade, configuration intents only.
- Added shared `MichiPopupHeader`, `MichiPopupFooter`, `MichiEqSlider`,
  `MichiSignalNode`.
- Added reviewed factory preset asset with Flat only.
- Wired both bridges into bootstrap and AppShell context (`audioProcessing`,
  `signalPath`).

### F11-03 — basic equalizer

- Added `EqualizerPopup` at 440 px: ten vertical rails, exact centers/labels,
  ±12 dB, 0.5 dB step, Flat preset, preamp, headroom readback label, bypass,
  Reset and Advanced entry.
- Draft edits stay local until apply. Apply delegates to
  `AudioProcessingService`; no QML DSP authority.
- Bands at or above the decoded Nyquist rate stay visible and keep their saved
  gain, but are marked inactive with the reason “Unavailable at current sample
  rate”; they are never silently clamped.
- A failed apply keeps the draft editable and never reports a false effective
  state.
- Native DSD/DoP show processing unavailable with explicit conversion reason.

### F11-04 — advanced equalizer

- Added centered 760 px `AdvancedEqualizerPopup` with exactly five tabs:
  Graphic, Parametric, Convolution / FIR, Signal / Resampling, Profiles.
- Capability-gated views report missing backend proof instead of simulating
  controls: 31 ISO mapping unavailable, convolution asset authority absent,
  profile CRUD absent.
- Fixed footer with Discard / Validate / Apply.

### F11-05 — Signal Truth

- Added 440 px `SignalTruthPopup` with five stages and canonical headline.
- No future-only claims: no bit-perfect, exclusive, native-preserved or
  DoP-verified assertion without a new proof authority.
- Configuration actions are intents; navigation stays in AppShell/NowPlaying.

### F11-06 / F11-07 — engine and output popups

- Engine popup: 360 px, 56 px rows, bridge-provided icon and subtitle,
  selection radio separate from Active badge, keyboard navigation, focus
  return.
- Output popup: 380 px, 62 px rows, selected/pending/active distinction,
  Playing badge only when active, fixed settings footer, real recovery,
  display expansion preserved.
- Added Canvas icons for Qt/GStreamer/MPD, DAC, jack, optical, display audio and
  stream-cat. No SVG or external assets.

### F11-08 — NowPlaying migration

- Surgical slot migration only: DacVolume span 2, EQ, Queue on row 0; Engine,
  Quality/Signal Truth, Output, empty spacer on row 1.
- Preserved 154 px height, track card, artwork, centered transport and all
  existing signals.
- Quality capsule became an accessible Signal Truth button.

### F11-09 — cross-surface rules

- Added `closeOtherAudioPopups()` and `closeAllSurfaces()`.
- Opening EQ, Engine, Output or Truth closes the others; Advanced replaces the
  quick EQ instead of stacking.

### F11-10 — KWin visual audit

- Isolated KWin Wayland session at 1920×1080, KWin 6.8.1, Qt 6.11.1.
- Captured and reviewed 12 surfaces/viewports:
  full, compact, narrow, stress, EQ, EQ stress, Truth, Advanced, Engine, Output,
  high contrast and reduced motion.
- Defects found and fixed: opener-relative popup collapse, stacked popups,
  duplicate Flat, clipped advanced warning, colliding EQ value labels,
  unstyled bypass switch, translucent popup legibility.
- Evidence: `docs/audio/phase2/F11_VISUAL_AUDIT.json` and
  `evidence/f11/2026-11-01-f11-surfaces/`.

## Commits

| Commit | Purpose |
|---|---|
| `95db637` | F11 processing/signal-truth bridges and QML surfaces |
| `c891a7e` | Engine and output popup refinement |
| `dd02a8f` | Surface legibility and mutual exclusivity fixes |
| `83a5272` | Productive hosted EQ proof and 12 KWin captures |
| `41b454d` | F11 design, visual audit and closure evidence |
| `484925b` | Output bridge formatting |
| `a19fdf5` | Machine-checked KWin visual manifest |
| `d883a03` | Pinned clean KWin runtime log |
| `db25e75` | Nyquist bands stay visible but inactive |
| `396de6d` | Failed apply keeps the draft |
| `b829a8a` | Quick-EQ controls commit through the bridge |
| `6c6c78a` | Incomplete EQ capabilities fail closed |
| `0b26241` | Lowercase host strategies normalize for the EQ |
| `cce711a` | Proof scope follows only observed stages |

## Verification

- Bridge tests: 13 + 3 passed.
- Productive hosted processing test: 1 passed.
- QML contract: 8 passed.
- KWin visual manifest contract: 3 passed.
- Mandatory F11 gate (bridges, productive hosted, QML and KWin contracts):
  28 passed in 31.17s.
- QML/runtime regression batch: 205 passed, 3 warnings.
- Ruff check and format: clean.
- AP2-F11 alignment: GO.
- DAC gate: OK.
- Full suite at `cce711a`: 6430 passed, 41 skipped, 0 failed, exit 0,
  2000.46 s (33:20).
- Full suite: 6430 passed, 41 skipped, 0 failed at `cce711a`.
- Exact-SHA CI: `41375199479` at `7bd75a0`, 4/4 jobs success.
- CI now runs the mandatory F11 gate and rejects any skipped/xfailed/xpassed
  surface test.

## Open limitations

- Advanced Graphic, Convolution/FIR and Profiles CRUD remain capability-gated.
- Quick EQ during DSD→PCM remains unavailable until a decoded-PCM provider is
  exposed by the presentation composition.
- KWin captures are reviewed evidence, not an automated pixel-diff golden.
- F11 does not claim physical DAC, analog audibility or bit-perfect.
- F14 remains NOT_RUN; F12/F13/F15 remain LOCKED.
