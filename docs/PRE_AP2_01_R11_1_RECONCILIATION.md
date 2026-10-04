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

## Drift between the handoff snapshot and the PRE-AP2-01 baseline

Two commits landed after `8bea498` from an independent, additive workstream:

- `4449b05 feat(ai): add read-only host integration baseline`
- `23ce05d ci(ai): authenticate private host dependency`

They add the optional read-only `michi_ai` host integration (`ADR-0009`,
`src/michi/integrations/michi_ai/`, a pinned optional dependency in
`pyproject.toml`, composition wiring in `src/michi/bootstrap`, an
architecture-test update and a CI authentication step). **No audio,
playback, DAC, Signal Truth, planner, lab or verifier file was touched**, so
every R11.1 audio preimage remains valid. The M11.4 verifier stays green on
the new head, which is the operational proof of that claim.

## References checked

- 67 repository paths are cited across the R11.1 mega-plan: 43 exist today;
  the 24 that do not are Phase 2 deliverables that F00+ must create
  (`PHASE2_STATE.json`, `IMPLEMENTATION_LEDGER.json`, `phase2_context.py`,
  `verify_audio_phase2*.py`, `tests/audio_phase2/`, the DSP/DSD runtime
  modules, `AudioLabView.qml`, Phase 2 architecture tests), not drift.
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
2. **Baseline:** F00's baseline HEAD is the PRE-AP2-01 package head, not
   `8bea498` (the AI-integration commits are part of the baseline).
3. **Spec install:** the plan expects its own canonical copy under
   `docs/audio/` with `PHASE2_STATE.json`, the implementation ledger, the
   context tool and the alignment verifier — still F00 deliverables.

## Conclusion

`R11.1 = reconciled` to the PRE-AP2-01 head with the three adjustments
above. No plan rewrite is required, and no ownership, API, phase-dependency
or failure-semantics contradiction was found beyond them.
