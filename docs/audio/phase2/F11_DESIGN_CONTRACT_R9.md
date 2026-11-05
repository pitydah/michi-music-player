# F11 Design Contract R9 — implemented surface contract

Status: implemented; closure review pending exact-SHA CI.
Phase: AP2-F11 `ACTIVE`. F10 is `CLOSED`.
Authoritative source: `MICHI_AP2_F11_MEGA_PLAN_R9_IMPLEMENTATION.md` and the
Audio Phase 2 Bible (§§197, 331–380, 416).

## 1. Scope and authority

F11 is a presentation phase. QML never owns audio truth, signal-path truth,
processing state, device state or transport state. It renders projections from
Python bridges and emits intents back to existing authorities.

Implemented F11-owned surfaces:

- `src/michi/presentation/audio_processing_bridge.py`
- `src/michi/presentation/signal_path_bridge.py`
- `src/michi/presentation/qml/player/EqualizerPopup.qml`
- `src/michi/presentation/qml/player/AdvancedEqualizerPopup.qml`
- `src/michi/presentation/qml/player/SignalTruthPopup.qml`
- `src/michi/presentation/qml/components/MichiEqSlider.qml`
- `src/michi/presentation/qml/components/MichiPopupHeader.qml`
- `src/michi/presentation/qml/components/MichiPopupFooter.qml`
- `src/michi/presentation/qml/components/MichiSignalNode.qml`
- `src/michi/resources/audio/factory_eq_presets_v1.json`

Modified in place:

- `NowPlayingBar.qml`
- `AudioEnginePopup.qml`
- `AudioOutputPopup.qml`
- `audio_engine_bridge.py`
- `audio_output_bridge.py`
- `MichiIcon.qml`
- `AppShell.qml`
- `bootstrap/__init__.py`

Forbidden surfaces were not created: no `DacQuickPopup.qml`, no
`AudioProcessingPopup.qml`, no `SignalPathPopup.qml`, no second theme or token
system, no second DSP engine, no second `SignalTruthRecorder`, no UI-owned
effective state.

## 2. Visual DNA and tokens

The UI uses the existing “Feline Hi-Fi Atelier” system: machined graphite,
obsidian, smoked glass, anodized-aluminum accents, editorial hierarchy and one
dominant accent per surface. All values come from the existing theme files:

- `MichiPalette`: obsidian, graphite, smoke, textPrimary/Secondary/Muted,
  auroraBlue/Cyan/Purple, success, warning, error.
- `MichiSemanticColors`: hover 0.055, pressed 0.09, selected blue 0.14,
  borderSubtle 0.07, borderStrong 0.12, focusRing 0.9.
- `MichiRadius`: 6 / 8 / 12 / 14 / 24 / pill.
- `MichiSpacing`: 2 / 4 / 8 / 12 / 16 / 24 / 32 / 48.
- `MichiTypography`: display 30, title 23, section 18, body 14, secondary 13,
  technical 12, caption 11, micro 10.
- `MichiMetrics`: controlSmall 28, medium 36, large 44; icons 16 / 20 / 24.
- `MichiMotion`: micro 110 ms, standard 180 ms, popupOpen 200 ms,
  popupClose 140 ms, selection 160 ms; zero under reduced motion.

No QML file introduced a local palette, hard-coded color system, alternate
radius scale, alternate motion scale or CSS/HTML-like styling layer.

## 3. NowPlayingBar composition

The certified bar remains 154 px high, with no scroll, no third action row and
no transport redesign.

Output zone (four columns):

| Row | Column 0 | Column 1 | Column 2 | Column 3 |
|---|---|---|---|---|
| 0 | `DacVolumeControl` span 2 | — | EQ `settingsButton` | Queue |
| 1 | Audio Engine | Quality / Signal Truth | Audio Output | empty spacer |
| 2 | empty span 4 | | | |

Preserved geometry: track card 94 px, artwork 72 px, transport centered,
`PlaybackZone` minimum width 360, compact threshold 1320, narrow threshold 980,
lateral inset 20 compact / 38 full.

The quality capsule is now a real accessible button that opens Signal Truth.
It is not decorative text. The EQ button opens the real equalizer. Queue keeps
its existing signal. Audio Engine and Audio Output keep their existing live
bindings and recovery behavior.

## 4. Popup family

All audio popups live inside the same Wayland window. They use `Popup` with the
opener as the coordinate authority, open upward with a 12 px gap, and use the
existing `MichiGlassSurface` with `materialOpacityOverride: 1.0` so library text
does not bleed through.

Implemented widths:

- Equalizer: 440 ideal / 420 minimum, overlay-relative.
- Advanced Equalizer: 760 ideal / 680 minimum, centered in the overlay, height
  640 ideal / 480 minimum with fixed header and footer, scrollable body.
- Audio Engine: 360 ideal / 320 minimum.
- Signal Truth: 480 ideal / viewport-safe minimum (V2; see F11_VR_UI_SPEC).
- Audio Output: 380 ideal / 340 minimum.

Visual exclusivity is implemented in `NowPlayingBar.closeOtherAudioPopups()`.
Opening EQ, Engine, Output or Truth closes the others. Opening Advanced from
EQ closes the quick surface first. Opening another surface while Advanced is
open also closes Advanced through `equalizerPopup.closeAllSurfaces()`. Popup
close restores focus to its opener.

## 5. Basic equalizer

The basic EQ maps to the existing DSP authority, not a new node type:

- `PreampNode` for preamp/headroom.
- One `ParametricEqNode` with exactly ten `BiquadType.PEAK` bands.
- Centers: 31.25, 62.5, 125, 250, 500, 1000, 2000, 4000, 8000, 16000 Hz.
- Q: `sqrt(2)` (`MICHI_10_Q`).
- Gain range −12…+12 dB, step 0.5 dB.
- Labels: `31 62 125 250 500 1K 2K 4K 8K 16K`.

Draft semantics are local until apply. A slider edit writes draft state only;
`apply_draft_async()` compiles the graph, delegates to
`AudioProcessingService.apply_processing_async()`, and only then treats the
draft as committed. `effectiveState` always comes from the service truth, never
from QML. `discard_draft()` restores the committed snapshot.

Preset handling is data-driven. The shipped
`factory_eq_presets_v1.json` contains a reviewed Flat preset. The bridge
deduplicates by id so Flat appears once. Extra presets are only surfaced when
they are reviewed and contain ten gains.

Native DSD and DoP never start conversion from the equalizer. They render as
unavailable for processing with the explicit reason that DSP requires an
explicit DSD-to-PCM conversion. The button never initiates that conversion.

## 6. Advanced equalizer

The Advanced surface uses exactly five tabs:

`Graphic`, `Parametric`, `Convolution / FIR`, `Signal / Resampling`, `Profiles`.

Capability honesty is mandatory:

- Graphic: the 31 ISO bands are displayed as unavailable until a proven
  runtime mapping exists; the warning explains that the ten-band quick EQ
  remains functional.
- Parametric: shows the current ten PEAK bands read-only, with the mapping
  limitation visible. No fake editable row is exposed without a proven bridge
  path.
- Convolution / FIR: no IR asset authority is claimed; the tab explains the
  missing capability instead of showing a fake “loaded” state.
- Signal / Resampling: shows request/effective state and source family; it does
  not claim to own output rate, dither or resampling policy.
- Profiles: lists reviewed factory presets, with no simulated create/delete/
  association/A-B actions.

The footer exposes Discard, Validate and Apply. Apply is disabled when the
bridge cannot apply. No advanced control writes DSP state directly.

## 7. Signal Truth

Signal Truth is a projection of the canonical `SignalTruthRecorder` and the
existing output bridge. It renders the base stages

`SOURCE → DECODE → PROCESSING → OUTPUT → DAC / DEVICE`

and inserts only observed transformation stages (resample, channel remap,
FIR) when runtime evidence proves them. Historical snapshots are labelled and
never presented as the active path. See `F11_VR_SIGNAL_TRUTH_SPEC.md`.

Headlines are restricted to observed or explicitly unknown states: `Direct
path`, `Direct · container adapted`, `Resampled`, `Channel remix`, `Processing
active`, `Output mismatch`, `Not verified`. The popup never claims `Bit-perfect
playback`, `Exclusive verified`, `Native DSD preserved` or `DoP verified
end-to-end` without a future explicit proof authority. With no active media it
shows `Not verified`, source `No active media`, processing `bypassed` where
that is the observed state, and DAC/Device `Not selected` when unresolved.

Node details are disclosed before any configuration action. Configuration
buttons emit only `NONE`, `OPEN_ENGINE`, `OPEN_PROCESSING`, `OPEN_OUTPUT` or
`OPEN_DEVICE_SETUP`; AppShell/NowPlaying owns navigation. The
popup owns no recorder and no independent truth.

## 8. Audio Engine and Audio Output

Audio Engine is an in-place 360 px quick selector. Rows are 56 px, expose an
engine icon and a short subtitle from the bridge, keep the selection radio
separate from the Active badge, preserve fallback/blocked/not-available states,
and keep keyboard navigation and focus restore. No new view model was created.

Audio Output is an in-place 380 px destination selector. Rows expose selected
intent, pending state, Playing/Active badge, destination icon, quick subtitle
and canonical status. Section headers remain non-clickable except Display Audio
expansion. The fixed footer keeps `Audio Output Settings`. Recovery actions
remain real bridge actions and never change policy automatically. Selected and
active are intentionally distinct; a selected destination is not painted as
Playing until the output authority confirms it.

Route icons are official Tabler SVG geometry rendered through
`MichiAudioRouteIcon`, a facade over `MichiSignalStageIcon`, at a 24 px integer
grid with `Shape.CurveRenderer` and no manual scale. The family covers
`engine-qt`, `engine-gstreamer`, `engine-mpd`, `audio-engine`, `dac`,
`audio-jack`, `display-audio`, `audio-output`, `system`, `display`, `usb`,
`internal` and `generic`. Icon type comes from the bridge (`iconType`), never
from display-name heuristics; unknown types fall back to `help`.

## 9. Accessibility and responsive behavior

- Focus policy and focus return are defined for all popups.
- Keyboard navigation skips disabled rows.
- Accessible names preserve canonical status text, including selected/active
  semantics.
- High contrast raises text and border contrast through existing tokens.
- Reduced motion disables popup and control transitions.
- Full (1920), compact (1100), narrow (1024) and stress (900×600) viewports
  were captured and reviewed.
- The NowPlaying bar never scrolls; popup bodies scroll internally with fixed
  headers and footers.

## 10. Verification map

- `tests/audio_phase2/test_f11_audio_processing_bridge.py` — basic EQ contract,
  exact graph, presets, bypass/reset, DSD refusal, missing signal.
- `tests/audio_phase2/test_f11_signal_path_bridge.py` — five-stage projection,
  no proof upgrade, intent-only configuration.
- `tests/audio_phase2/test_f11_processing_bridge_productive.py` — real hosted
  GStreamer processing apply and bypass.
- `tests/test_f11_qml_contract.py` — NowPlaying geometry, slot map, popup
  exclusivity, EQ/Truth/Advanced contracts.
- `tests/test_qml_runtime_gate.py`, `tests/test_m11_3_ui_qml_runtime.py`,
  `tests/test_m9_qml.py`, `tests/test_m9_now_playing_golden.py`,
  `tests/test_m9_design_canon.py`, `tests/test_m11_3_ui_audio_engine.py`,
  `tests/test_v35_090_qml_audio_output.py` — existing QML/runtime regressions.

## 11. Non-claims

F11 is a UI phase. It does not add physical DAC certification, analog
audibility, bit-perfect certification, F14 execution, or a second DSP/audio
authority. Advanced tabs that lack a proven backend contract remain explicitly
capability-gated rather than simulated.
