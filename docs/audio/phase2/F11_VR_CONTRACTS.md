# F11 Visual Recovery — Contracts (S0/S1)

## SignalPathBridge projection

`SignalPathBridge` is a read-only owner-thread projection. It never classifies
audio and never invents a proof level.

Temporal status is one of:

| Status | Source | UI meaning |
|---|---|---|
| `ACTIVE` | `SignalTruthRecorder.active_snapshot` | observed current execution |
| `PENDING` | `candidate_snapshot` when no active snapshot | path in preparation; no effective claim |
| `HISTORICAL` | `last_snapshot` when no active/candidate | last playback only |
| `NOT_ACTIVE` | none | no active path |

Projection fields:

```text
headline, proofLevel, generation, sourceIdentity, stages, reasonCodes,
headlineTone, active, historical, status, statusLabel, pathVerdict,
indicatorState, indicatorTooltip, identity, configurationActions
```

Stage fields:

```text
id, title, summary, detail, configAction, state, detailRows,
index, count, first, last, expandable, expanded
```

Closed stage states: `unknown`, `pending`, `observed`, `transformed`,
`historical`, `error`. The rail is drawn from `first`/`last`, never from the
item's `y` position.

Dynamic stages are appended only from observed evidence:

- `resample` when `transform.resampler_transforming` is true;
- `channel-remap` when `transform.remix_transforming` is true;
- `fir` when the runtime graph factory reports FIR/convolution.

Processing is `transformed` only when the processing service is `effective`
AND its `effective_plan_id` equals the snapshot plan id. Otherwise it is
`unknown` with an explicit identity-mismatch reason. Draft EQ band values are
never read for Signal Truth.

## Quick EQ bridge

`AudioProcessingBridge` keeps the draft local and publishes effective state
only from `AudioProcessingService.processing_truth()`.

- `available`: capability + source family gate.
- `canEdit`: editability independent from whether a commit can be applied.
- `canApply`: requires decoded PCM, capability strategies and non-busy state.
- `draftDirty`: draft differs from last committed snapshot.
- `stateLabel`: `Unavailable | Ready | Draft | Applying | Effective · rev N |
  Bypassed | Error`.
- `responseCurve`: calculated 256-point magnitude response from canonical RBJ
  coefficients; `responseAvailable` is false without a decoded signal.
- `refresh()`: reconciles service truth; draft edits during in-flight commits
  are ignored so a late completion cannot mark an unapplied curve as committed.

`_f11_signal` in bootstrap uses only `active_snapshot.decoded_runtime.pcm`.
Library metadata and historical snapshots are not decoder evidence; the EQ
fails closed without an active decoded PCM contract.

## Visual ownership

- `MichiSignalPathView`: single stage renderer for popup and DAC diagnostics.
- `MichiSignalNode`: rail, status glyph/token/text, details/config disclosure.
- `MichiSignalIndicator`: compact NowPlaying evidence indicator.
- `SignalTruthPopup`: header/footer wrapper only.
- `SignalTruthPanel`: compact wrapper over the same renderer.
- `MichiEqResponsePlot`: calculated curve only; no spectrum animation.

No second `SignalTruthRecorder`, DSP service, theme or QML authority exists.
