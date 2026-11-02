# F11 Legacy EQ — Concept Extraction

Reference: `pitydah/michi-legacy` (private). No code, asset, screenshot or
dependency was copied into this repository.

## Reused concepts

- Studio workflow: draft -> validate -> commit -> readback.
- Quick/Advanced split and mode selector.
- Theoretical magnitude response from RBJ transfer functions.
- Auditable preset identity, origin and review state.
- Capability-gated DSP modules, not editable fake cards.

## Explicitly not ported

- `EqBridge` synchronous mutations and optimistic effective state.
- Legacy 31-band gain envelope (-24..+24). Current GraphicEqNode stays
  -12..+12.
- Legacy approximate labels (`1.3k`, `3.2k`, `13k`). Current ISO centers are
  canonical.
- AutoEQ downloader, legacy preset JSON storage and MPD string authority.
- The legacy baseline screenshot as an EQ golden (it shows overlays, not the
  active editor).

## Current implementation

The only productive DSP authority is `AudioProcessingService`. Quick EQ uses
`PreampNode + ParametricEqNode` with 10 PEAK bands at canonical centers. The
calculated response consumes the same `biquad_coefficients` implementation as
the graph compiler.
