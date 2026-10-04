# ADR 0011 — Audio Phase 2 restricted activation (AP2-F00)

- **Status:** Accepted — `AP2-F00 = CLOSED`, `AP2-F01 = READY`
- **Date:** 2026-10-04

## Context

PRE-AP2-01 closed with GO: the R32 receipt-sidecar verifier is fail-closed,
the subprocess characterizer is sealed in the wheel/collection gates, the
corrected bounded preflight (external supervisor, real steady Direct window)
passed on the exact baseline head, M11.5A is frozen, the R11.1 reconciliation
is current, the accidental Michi AI contamination is reverted, and the
software regression is green with no unknown P0/P1.

Physical debt stays exactly as classified: R32 is an upstream GStreamer
1.28.x lifecycle blocker, R25 HA01, R35 and R36 remain pending, and the
physical verdict remains INCOMPLETE.

## Decision

1. The canonical R11.1 spec is installed at
   `docs/audio/MICHI_AUDIO_PHASE_2_DSP_DSD_DOP_SIGNAL_PATH_MEGA_PLAN.md`
   with its frozen SHA-256 recorded in `PHASE2_STATE.json`,
   `SPEC_COMPLETENESS.json` and the baseline manifest.
2. The baseline HEAD frozen for Audio Phase 2 is the PRE-AP2-01 seal commit `9c1c2d5fbeb35b20e76cb3a02702bd7666d9b160`
   (recorded in `docs/audio/phase2/audio_phase2_baseline.json`).
3. Phase states start at `AP2-F00 = CLOSED`, `AP2-F01 = READY`, and
   `AP2-F02..AP2-F15 = LOCKED`. State changes require explicit commits after
   the previous phase exit gate produced evidence.
4. F01–F04 are allowed under restricted activation. F05+ stays locked by
   `GST_LIFECYCLE_GATE` plus the recorded owner-thread characterization
   blocker (ADR-0010 §9).
5. F00 changes no productive behavior: no DSP, DSD, DoP, UI or bootstrap
   runtime class is added; the deliverables are governance artifacts,
   context tooling and gates.
6. The hardened physical lab (durable local evidence root, hash-chained
   journal, chunked receipts, external supervisor) starts the remaining
   M11.4 campaign independently from Phase 2 F01–F04 work. Physical debt is
   never upgraded by documentation.

## Consequences

- Agents must run `phase2_context.py` and the repository alignment gate
  before any Phase 2 patch, and must not mutate LOCKED phases.
- `SPEC_COMPLETENESS = 100 %` means no CORE decision is left to improvised
  judgement; it never means implementation, physical qualification or release.
- The physical campaign continues in parallel; its evidence never alters the
  Phase 2 baseline freeze.
