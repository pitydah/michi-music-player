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

## Visual Recovery R2 (2026-11-02)

- Applied the cumulative R2/R4 implementation patch on top of `162decc`
  (`input_patch_sha256=17d59f09…`).
- Popups are modal without dimming and consume outside clicks; Signal Truth
  nodes have exclusive pointer/keyboard interaction; stage pictograms and
  evidence microbadges are independent; the rail dynamic height preserves
  first/last semantics.
- Advanced Graphic10 and PEAK10 share the canonical quick draft; preset loading
  only stages a draft; FIR and Signal / Resampling are read-only; Apply/Discard
  appear only where an edit is possible.
- Engine/Output use the route icon and route selection skin; NowPlaying carries
  the integrated Signal Truth capsule; DSP identity mismatch is visible in the
  header.
- KWin isolated pointer matrix: Source click, ten chevron toggles and an
  outside click over a library row all left track `pcm16_44100_30s` unchanged;
  the outside click did not activate the row. Scroll and full keyboard traversal
  are NOT_RUN.
- Captures: `f11_vr_r2_pointer_source_click.png`,
  `f11_vr_r2_chevron_10x.png`, `f11_vr_r2_outside_click_consumed.png`, SHA-pinned
  in `F11_VR_R2_EVIDENCE.json`.
- R2 code and test commit: `c5635e6`.
- Verification: pointer guard 10 passed; combined R2 batch 226 passed;
  QML/runtime regression 182 passed; productive hosted EQ 1 passed; mandatory
  F11 CI gate 49 passed in 31.11 s with zero skips; full suite
  6457 passed, 41 skipped, 0 failed (exit 0, 1916.19 s); ruff check/format and
  `git diff --check` clean.
- Exact-SHA CI: run `41567906735` at `d94991a7f1dd13536f8646b5577e6fa21af09f05`
  completed 4/4 success (`check`, `min-qt`, `dac-v35-software-closure`,
  `dop-native-gate-a`).
- R2 remains NO-GO for F11 closure; the open gates are unchanged.

### R2 review fix

- Restored the NowPlaying album line to `textSecondary` + `opacity: 0.7`; the R2 capsule refactor had dropped the opacity expected by the M9 editorial contract. Targeted `tests/test_m9_r2_4_playlist_editorial.py` -> 28 passed.
- Python qmllint 6.11.1 on the R2 QML files exits 0; only unqualified-access warnings and the `pragma ComponentBehavior: Bound` suggestion.
- Factory preset asset validated: 8 reviewed presets, 10 bands each, MICHI_10 layout.

## Visual Recovery R3 (2026-11-03)

- `9a468bf` `fix(audio): keep signal truth inside a short window`: SignalTruthPopup
  now positions against `Overlay.overlay` with clamped x/y and a 560 px cap, so the
  fixed header/footer remain visible at 900×600 while the stage body scrolls.
- `8a94acd` `fix(audio): bind processing truth to the output pipeline`: DSP
  processing events are correlated by readback-proven pipeline generation instead
  of comparing unrelated processing and output plan ids. Live quick EQ now shows
  `Processing active`, `DSP active`, plan, revision and pipeline generation.
- R3 KWin captures: active PCM Direct, live quick EQ/readback, 900×600 responsive,
  Native DSD active with truth pending, high contrast and reduced motion.
  Evidence: `F11_VR_R3_EVIDENCE.json`, `evidence/f11/2026-11-03-f11-vr-r3/`.
- Pointer/keyboard: Source click, 10× chevron, outside click, scroll, full Tab
  traversal, Enter disclosure and Escape focus return PASS; track unchanged.
- Honest failures: DoP `DOP_QUALIFICATION_FAILED: probe deadline exceeded`;
  DSD→PCM `DSD_PCM_TARGET_UNQUALIFIED`; Native active playback has no recorder
  snapshot, so Signal Truth stays Pending/Unknown. Sidebar W1–W9 and Advanced
  CRUD remain NOT_RUN. F11 remains NO-GO/ACTIVE.

## Visual Recovery R6 (2026-11-03)

- `fix(audio): type the F11 quality badge and anchor signal truth`:
  SignalPathBridge now publishes `sourceQualityClass`, format and rate/depth
  strings, `pathProofState` and accessible quality text from structured facts.
  The NowPlaying capsule is an 8 px solid dot plus format and depth; path proof
  is separate. SignalTruthPopup is parented to `Overlay.overlay`, positioned from
  measured badge geometry on open and resize, and covered by Qt tests at
  1920×1036, 1920×1080, 1366×768 and 900×600 (8–12 px gap, 420–520 px surface,
  focus return, no track/seek/engine/device signal).
- `feat(audio): turn signal truth and advanced EQ into premium inspectors`:
  Signal Truth has an uppercase header, one LIVE/LAST PLAYBACK badge, typed
  source context, five semantic stages with 32 px icon boxes, a single global
  historical state and a device display name instead of a raw USB id. The
  Advanced workspace is a 960×700 desktop console with fixed header/tabs/footer,
  labelled ±12 dB and 20 Hz–20 kHz response axes, ten aligned rails and ten fixed
  PEAK gain rows; unsupported FIR/31-band/profile CRUD stays capability-gated.
  The quick-EQ preset row no longer widens the popup and clips the ten rails.
- KWin isolated session `wayland-mcp-2028722-1793743183`, 1920×1080 at 100 %:
  NowPlaying, quick EQ, Advanced EQ (1100 and 900), live Signal Truth,
  historical Signal Truth (900), Audio Engine and Audio Output captured after
  the fade-in. Evidence: `F11_VR_R6_EVIDENCE.json` and
  `evidence/f11/2026-11-03-f11-vr-r6/`.
- Honest limits: no human screenshot sign-off, no pixel/perceptual golden, DPI
  scales above 100 % not exercised, physical DAC not re-run, and the Advanced
  body scrolls in short windows. F11 remains NO-GO/ACTIVE.

## Visual Recovery R7 (2026-11-03)

- `879099c` `fix(audio): make signal truth intrinsic and proof-aware`:
  SignalTruthPopup now derives its height from five collapsed stages, keeps a
  bounded short-window fallback through `maxPopupHeight`, and only enables the
  Flickable when the content really exceeds its viewport. The repeated stage
  checkmarks became a 5 px certainty microdot, per-stage observed text is
  suppressed in favour of the global temporal badge, and each stage with a real
  capability exposes an independent gear action. Unknown verdicts with four
  proof parts remain `partially_verified`; only a proven verdict plus source,
  host, transport and device can be `verified`. The NowPlaying track card is
  96 px with 72 px artwork while the bar stays 154 px and transport is unchanged.
- Tests: pointer guard, R7 integrity, QML contract and R6 evidence `32 passed`;
  F11/QML, bridge, runtime, engine and golden regression `228 passed`. The
  first full-suite run exposed three stale R6 source-contract assertions in
  `test_f11_signal_truth_pointer_guard.py`; they were updated to the intentional
  R7 contracts (independent evidence microdot, capability-based configuration,
  96 px card / 72 px artwork) without weakening behaviour coverage. qmllint
  exits 0 with only pre-existing warnings; ruff check/format clean. Full suite:
  `6479 passed, 41 skipped, 0 failed` in 1931.53 s.
- Honest limits: KWin MCP was unavailable in this session, so VR-R7 KWin
  captures are NOT_RUN; qmlformat/qmltestrunner are Qt 5 binaries and were not
  used against Qt 6 QML; DPI scaling and Qt Quick profiler p95 are NOT_RUN.
  F11 remains **NO-GO / ACTIVE**.

## Visual Recovery R8–R10 (2026-11-04)

R8 captured the compact KWin signal-truth surface (`aa19fe3`..`b1770fa`,
`docs/audio/phase2/F11_VR_R8_KWIN_EVIDENCE.json`) and R9 replaced the inherited
stage glyphs with official Tabler geometry (`4148709`, `9ed74c8`,
`docs/audio/phase2/F11_VR_R9_KWIN_EVIDENCE.json`). R10 then fixed glyph
sharpness: the 24×24 paths were being squeezed through a manual uniform `Scale`
into 20 px and tessellated by the default Shape renderer, so `ad7ea5d` moved
`MichiSignalNode` to `Shape.CurveRenderer` at the native 24 px grid with a
2.0 stroke and no manual scale. `0949445` certified the renderer in a live KWin
session; the PySide6 6.11.1 runtime does not ship `QtQuick.VectorImage`, which
is recorded as an honest limitation rather than emulated. `12e1c95` certified
scaling and source disclosure, `2d4751d` restored expanded-stage scrolling and
source identity, and `4c0c4e7` moved stage colors into the theme.

This cut completes the route-icon side of R10:

- `MichiAudioRouteIcon` is now a facade over `MichiSignalStageIcon`; the Canvas
  implementation is gone and both popups consume `row.modelData.iconType` from
  the bridges. The engine bridge emits `engine-qt`, `engine-gstreamer`,
  `engine-mpd` and `audio-engine`; the output bridge emits `display-audio`,
  `dac`, `audio-jack` and `audio-output`. Shared/system rows resolve to
  `system`, and unknown roles fall back to `help` instead of a speaker glyph.
  Aliases also cover the legacy `qt`, `gstreamer`, `mpd`, `stream-cat`,
  `display`, `internal`, `usb` and `generic` vocabulary. QML still never infers
  an icon from a display name.
- All call sites render at 24 logical px: both popup rows inside their 32 px
  icon box and `MichiPopupHeader` via `MichiMetrics.iconLarge`. This removes the
  overflow/clipping produced by drawing 24-grid paths into 20 px without
  scaling.
- Both Enter activation handlers are restored on the popup rows. The native
  `Button` path does not deliver Return in this runtime; removing
  `Keys.onReturnPressed`/`Keys.onEnterPressed` made
  `test_ui90r1_12_enter_really_activates_focused_row` send zero shared
  requests, while the pre-change HEAD passed both Enter tests. Return and Enter
  remain distinct keys and both routes stay covered.
- The unused `chart-line` asset was removed; the family is now 16 official
  Tabler assets, each checked against its inline path data and its real file
  SHA-256. `SOURCES.json` records the 16 hashes.
- The "Audio Output Settings" footer button no longer sets `selected: true`;
  the settings entry is an action, not a permanently selected destination.
- Evidence: `f11_r10_route_icon_sheet_100.png` (640×500, DPR 1.0) and
  `f11_r10_route_icon_sheet_200.png` (1280×1000 physical for the same 640×500
  logical layout, `QT_SCALE_FACTOR=2`) show all 16 engine, output, shared and
  stage roles at 24 px. SHA-256:
  `207483c16711ed9f2a2c6e39907a7b8a22a33c538a57efff09fbb75d06cf6248` and
  `8a2ed8acb714fd8a7acc6e2cc2a6878a05a3d34a0c4b180c7e658734eeb402d3`.
  Both are referenced from the new `route_icons` block in
  `docs/audio/phase2/F11_VR_R10_ICON_RENDERER.json`, together with the bridge
  taxonomy, call-site geometry and the 16 asset hashes.
- Tests: QML contract, pointer guard and output-popup contract `93 passed`;
  F11 bridge/integrity/evidence batch `50 passed`. The new
  `test_route_icons_cover_every_bridge_icon_type` pins every bridge-emitted
  `iconType`, and the QML contract test now verifies all 16 assets against
  `SOURCES.json`.
- Honest limits: the route-icon sheets are offscreen `QQuickWindow.grabWindow()`
  captures of the productive component, not live KWin/Wayland captures; the
  2× run is a `QT_SCALE_FACTOR=2` render whose PNG carries no DPR metadata.
  Live KWin route-icon captures remain NOT_RUN, as does the Qt Quick profiler.
  F11 remains **NO-GO / ACTIVE**.
