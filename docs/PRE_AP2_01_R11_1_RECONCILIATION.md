# PRE-AP2-01 — R11.1 exact-head reconciliation

This records the WU6 reconciliation between the Audio Phase 2 R11.1 plans
(folder `/home/cristian/Descargas/Audio-phase-2/`) and the current
repository. It is a report, not a plan rewrite: R11.1 remains the
architectural authority; current repository code wins for preimage facts.

## Baselines

| Source | Head |
| --- | --- |
| R11.1 M11.4 handoff snapshot | `8bea498b0c2838b962352e09aa70da73088ced23` |
| Repository at PRE-AP2-01 start | `23ce05db466408b1564c40a47e74e88a8283a0eb` |
| PRE-AP2-01 code commit (WU1–WU3) | `7904c753944f` |
| M11.5A freeze + reconciliation commit | `705303a52f2d` |
| AI contamination reverted | `bfef286` (post-revert baseline for F00) |

## AI contamination: detected and reverted

Two unrelated Michi AI commits landed here by mistake:

- `4449b05 feat(ai): add read-only host integration baseline`
- `23ce05d ci(ai): authenticate private host dependency`

Michi AI is out of scope for Audio Phase 2 and the Phase2 baseline must not
freeze accidental AI work, so both were **reverted in dependency-safe reverse
order** in `bfef286` (the integration package, ADR-0009, the optional
dependency, the bootstrap composition wiring, the architecture-test addition,
its test module and the CI authentication step are gone). The reverts applied
cleanly with no conflict against the PRE-AP2-01 package; focused
architecture/bootstrap/package tests pass on the reverted tree.

Shared bootstrap/package files (`src/michi/bootstrap/__init__.py`,
`pyproject.toml`, `tests/test_architecture.py`) were briefly touched by those
commits; the audio ownership preimages were inspected and remained intact
throughout, and the reverted tree restores their pre-AI content. The current
reconciliation therefore records the contamination as **resolved**, not as
baseline drift.

## References checked

- 67 repository paths are cited across the R11.1 mega-plan: 43 exist today;
  the 24 that do not are Phase 2 deliverables that F00+ must create
  (`PHASE2_STATE.json`, `IMPLEMENTATION_LEDGER.json`, `phase2_context.py`,
  `verify_audio_phase2*.py`, `tests/audio_phase2/`, the DSP/DSD runtime
  modules, Phase 2 architecture tests) plus the canonical UI targets
  `EqualizerPopup.qml`, `AdvancedEqualizerPopup.qml` and
  `SignalTruthPopup.qml` (mega-plan target list), not drift.
  `AudioLabView.qml` appears only in the historical §153 Audio Lab design
  section; it is **not** classified here as an active required future file.
- Cited commands that exist today and are valid: `python -m pytest -q
  tests/dac/` and the `gstreamer_runtime` marker gate (`pyproject.toml`).
  The remaining cited commands (`tests/audio_phase2/`,
  `scripts/phase2_context.py`, `scripts/verify_audio_phase2*.py`,
  `scripts/audio_phase2_lab.py`) are F00+ tooling.
- Ownership/API spot-check against the current head passed for:
  `PlaybackService`, `PlaybackSessionService`, `OutputSessionService` +
  `ProductiveOutputRequestResolver`, `SignalTruthRecorder`, the GStreamer
  adapter/port, `SubprocessSourceCharacterizer`/`characterize_cli`,
  `AudioOutputBridge` and the QML output surfaces.

## Adjustments for F00

1. **Path shape:** the mega-plan cites `src/michi/bootstrap.py`; the
   repository ships the `src/michi/bootstrap/` package. F00's canonical spec
   install must use the package path.
2. **Baseline:** F00's baseline HEAD is the post-revert PRE-AP2-01 head
   (`bfef286` or later), not `8bea498`; the accidental AI work is no longer
   part of the baseline.
3. **Spec install:** the plan expects its own canonical copy under
   `docs/audio/` with `PHASE2_STATE.json`, the implementation ledger, the
   context tool and the alignment verifier — still F00 deliverables.

## Conclusion

`R11.1 = reconciled` to the PRE-AP2-01 head with the three adjustments
above. No plan rewrite is required, and no ownership, API, phase-dependency
or failure-semantics contradiction was found beyond them.
