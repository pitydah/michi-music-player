# F11 Signal Truth 2.0 — Specification

## Truth model

The recorder remains the only Signal Truth authority. The bridge exposes one
immutable read model with temporal status:

- ACTIVE: current committed execution evidence.
- PENDING: candidate/preparation, never shown as effective.
- HISTORICAL: last completed playback, neutralized and labelled.
- NOT_ACTIVE: no media/path.

`proofLevel` is evidence provenance, not a certainty ladder. It is assembled
from observed source, host, transport and device facts only.

## Stage policy

- Source: file/nominal facts, always labelled nominal.
- Decode: decoded runtime PCM and port generation.
- Processing: only `transformed` with an effective plan id equal to the
  snapshot plan id and a readback receipt. Identity mismatch is `unknown`.
- Resample / channel remap / FIR: only appended when the runtime transform or
  graph factory proves the operation. Unknown order is never invented.
- Output: negotiated ALSA/engine format; requested format is a detail row.
- Device: snapshot stable id, binding/port generation; selection mismatch is an
  explicit error.

States are closed and non-color-only: unknown, pending, observed, transformed,
historical, error. Each has an icon, token and accessible text. The rail uses
index/count and first/last flags.

## Failure handling

- Stop/EOS/host loss: no stale stage is presented as active; historical is
  labelled if retained.
- Processing runtime mismatch: processing is unknown, not effective.
- Bridge failure: projection degrades to no active path; QML never infers.
- No bit-perfect, exclusive, Native-preserved or DoP-verified claim is made.

## QML surfaces

`MichiSignalPathView` is the only stage renderer. `SignalTruthPopup` and
`SignalTruthPanel` wrap it at full/compact density. `MichiSignalIndicator`
shows the same state in NowPlaying. Details disclosure precedes configuration;
configuration emits an intent only.
