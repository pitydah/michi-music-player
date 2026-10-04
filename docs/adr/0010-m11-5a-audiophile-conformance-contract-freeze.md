# ADR 0010 — M11.5A Audiophile Conformance Contract Freeze (R11.1)

- **Status:** Accepted — `M11.5A = FROZEN`
- **Date:** 2026-10-03

## Context

Audio Phase 2 (DSP / DSD / DoP / signal-path work) is entering restricted
activation F00–F04. Before any Phase 2 runtime lands, the conformance
vocabulary, authority split and ownership boundaries must be frozen so that
runtime implementation, conformance evaluation and qualification evidence
cannot drift into duplicate authorities. This ADR freezes semantics only:

- it does **not** mean `M11.5B = IMPLEMENTED`;
- it does **not** mean `M11.5 = PHYSICAL PASS`;
- it cannot upgrade any M11.4 physical evidence.

## Decision

### 1. Proof vocabulary

One vocabulary is frozen for every conformance statement:

- `VERIFIED` — the required evidence exists, is current, and proves the claim.
- `UNVERIFIED` — evidence could exist but has not been produced yet.
- `NOT_APPLICABLE` — the claim does not apply to this configuration.
- `BROKEN` — current evidence contradicts the claim.
- `UNKNOWN` — evidence is missing, incomplete or contradictory.

Missing evidence is never `PASS` and never `FAIL` by itself.

### 2. Authority split

- `SignalTruthRecorder` records runtime evidence. It is the single runtime
  evidence authority; no second recorder may be created.
- M11.5 evaluates conformance and owns the verdict rules built on that
  evidence.
- QML only renders the result; no business state moves into QML.
- `Direct` never implies `bit-perfect` by itself.

### 3. Bit-perfect proof ownership

M11.5 owns bit-perfect verdict rules. Audio Phase 2 produces the runtime and
system evidence those rules consume. Physical promotion evidence remains a
DAC-V35 qualification concern (see §7).

### 4. Gapless and transitions

- Same-format gapless: Audio Phase 2 implements runtime continuity; M11.5
  owns its verification rules.
- Cross-format transition: a transition is explicitly **not** claimed as
  gapless unless M11.5 verifies it under the same rules.
- Accepted-media boundary and position/queue ownership remain with
  `PlaybackSessionService` and `PlaybackService`; no Phase 2 component may
  fork those authorities.
- Failure behavior must be explicit: a broken or unknown transition reports
  `BROKEN`/`UNKNOWN`, never a silent success.

### 5. Native DSD, DoP and DSD→PCM

- Audio Phase 2 owns the runtime implementation of Native DSD, DoP,
  DSD→PCM conversion and family transitions.
- M11.5 owns conformance: preservation proof, bit-perfect verdict rules and
  gapless/transition verification.
- No Phase 2 component may create a second output planner, a second Signal
  Truth recorder or a second playback authority.

### 6. Requested vs effective semantics

`selected != active` and `requested != effective`. Conformance statements
must name which side they describe, and contradictions between the two are
`BROKEN` or `UNKNOWN` — never silently reconciled.

### 7. Relationship with DAC-V35-140

DAC-V35-140 remains qualification/promotion evidence scope. M11.5 does not
duplicate it, and any formal supersession requires a future accepted ADR.
This ADR freezes the boundary only.

### 8. Physical evidence boundary

`M11.5A` cannot upgrade M11.4 evidence. `R32 = DEFERRED_UPSTREAM_BLOCKER`
stays deferred; `R25 HA01`, `R35` and `R36` stay pending;
`PHYSICAL_VERDICT = INCOMPLETE`; `PASS_MULTI_HARDWARE`, bit-perfect and
exclusive remain unclaimed.

### 9. Deferred blockers before F05

Recorded explicitly by PRE-AP2-01 (WU2B and the R11.1 killcritic):

- `GST_LIFECYCLE_GATE` — the Direct GStreamer lifecycle can still wedge on a
  reproducible upstream GStreamer 1.28.x state-change race
  (`Eyevinn/strom#963` signature; evidence under
  `evidence/dac-v35-pcm-closure/2026-09-30-smsl-152a85dd/diagnostics/`).
- `GST_LIFECYCLE_GATE_BLOCKER` — the request build (which contains the
  bounded characterization worker process) still executes inline on the Qt
  owner thread, and `cancel_pending_prepare` supersedes via generation but
  cannot preempt an in-flight characterization. The attempted async offload
  changes the load contract encoded by 118 tests and is deferred to the same
  gate.

F00–F04 do not depend on Direct lifecycle changes; F05/F06 stay locked until
this gate passes.

## Consequences

- Audio Phase 2 implements runtime; M11.5 conformance rules consume Signal
  Truth evidence; DAC-V35 qualification evidence stays separate.
- Any new conformance vocabulary term, recorder, planner or playback
  authority requires a superseding ADR.
