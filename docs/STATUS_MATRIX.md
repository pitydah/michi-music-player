# Status Matrix

Governance authority for component and work-package state. It owns only the two exact state sets and their transition semantics.

No state labels or transitions exist beyond those defined below.

## Component State Machine

Components track implementation health through a staged lifecycle. Each component carries exactly one state at all times.

### States

| State      | Meaning                                                                          |
| ---------- | -------------------------------------------------------------------------------- |
| UNKNOWN    | Not yet audited; no evidence collected                                           |
| AUDITED    | Evidence collected; state and risks are documented                               |
| BROKEN     | Known defects prevent basic function                                             |
| PARTIAL    | Subset of responsibilities is functional; known gaps remain                      |
| FUNCTIONAL | All responsibilities verified as working                                         |
| TESTED     | Automated test coverage exists for all responsibilities                          |
| STABLE     | No regressions across multiple release cycles                                    |
| FROZEN     | Design closed; no further changes permitted without approved reopening exception |

### Normal Progression

```
UNKNOWN → AUDITED → FUNCTIONAL → TESTED → STABLE → FROZEN
```

### Exceptional States

- **BROKEN**: component has known defects that prevent basic function. Recovery path is `BROKEN → FUNCTIONAL` only — a BROKEN component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.
- **PARTIAL**: subset of responsibilities is functional; known gaps remain. Recovery path is `PARTIAL → FUNCTIONAL` only — a PARTIAL component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.

Recovery from BROKEN or PARTIAL requires: (a) remediation passes all functional criteria, (b) evidence is recorded, and (c) the transition is explicitly reviewed.

### Evidence Required per Transition

| Transition           | Evidence                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| UNKNOWN → AUDITED    | Audit report: current state, known risks, dependencies                                         |
| AUDITED → FUNCTIONAL | Functional criteria met; manual or automated verification                                      |
| FUNCTIONAL → TESTED  | Automated test suite passes (see Evidence-Based Definition of TESTED in DEFINITION_OF_DONE.md) |
| TESTED → STABLE      | No regressions across ≥2 release cycles                                                        |
| STABLE → FROZEN      | Approved freeze decision; no open P0/P1                                                        |
| BROKEN → FUNCTIONAL  | Remediation passes; all functional criteria re-verified                                        |
| PARTIAL → FUNCTIONAL | Remaining gaps closed; all responsibilities verified                                           |

## Work-Package State Machine

Work packages (WPs) track deliverable progress through the SDD pipeline. Each WP carries exactly one state and, when BLOCKED, records its prior state for correct resumption.

### States

| State       | Meaning                                            |
| ----------- | -------------------------------------------------- |
| BACKLOG     | Captured but not yet ready for execution           |
| READY       | Admitted for execution by the readiness authority  |
| IN_PROGRESS | Active development                                 |
| REVIEW      | Under review (code, design, or architecture)       |
| VERIFY      | Acceptance criteria being verified                 |
| BLOCKED     | Cannot proceed; prior state recorded               |
| DONE        | Accepted by the completion authority and delivered |
| DEFERRED    | Intentionally postponed with rationale             |

### Normal Flow

```
BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
```

### Blocking Rules

READY, IN_PROGRESS, REVIEW, and VERIFY MAY enter BLOCKED when a dependency or obstacle prevents progress. BLOCKED MUST record the immediately prior active state; no other state may enter BLOCKED.

Resumption restores the recorded prior state:

Each route below is a suspension and restoration path, not a fresh progression:

- `READY → BLOCKED` resumes as `READY`
- `IN_PROGRESS → BLOCKED` resumes as `IN_PROGRESS`
- `REVIEW → BLOCKED` resumes as `REVIEW`
- `VERIFY → BLOCKED` resumes as `VERIFY`

### Deferral Rules

Only these states MAY enter DEFERRED, each with a recorded rationale:

- `BACKLOG → DEFERRED`
- `READY → DEFERRED`
- `BLOCKED → DEFERRED`

`DEFERRED → BACKLOG` SHALL occur only after an approved scope change. Otherwise the item remains DEFERRED or is permanently retired.
These rules are exhaustive for work-package interruption and deferral.

## Current Capability Matrix

Snapshot of the rebuild's components against the component state machine. Evidence: pytest suite (460 passing, snapshot 2026-08-16), Ruff clean, CI green. The count is a dated snapshot; authoritative evidence is the passing full suite in CI. The matrix is a report, not a new state set; the state machine above is authoritative and unchanged.

**Active-contract rule**: the matrix reports only components of the active 1.0 contract on the current stack. Every state below MUST be a legal state from the component state machine above — no invented labels. Superseded clean-rebuild governance draft components (the C++20-anticipation milestones) are not reported. A contract component that has not started is UNKNOWN (not yet audited), never a custom label.

**Post-1.0 rule**: a component is PARTIAL only when at least one responsibility REQUIRED by the active 1.0 release contract remains incomplete. Post-1.0 responsibilities (deferred context) are NOT gaps preventing FUNCTIONAL/TESTED and MUST NOT be listed as blockers.

| Component                    | State      | Notes                                                                                                                                                    |
| ---------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1 Bootstrap                 | TESTED     | Composition root, explicit wiring, best-effort shutdown (first-error-wins)                                                                               |
| M2 Minimal Playback          | TESTED     | Single-file playback via QtMultimediaBackend behind AudioPort                                                                                            |
| M3 Complete Playback         | TESTED     | Play/pause/resume/stop, seek, volume, mute, position/duration events all tested; metadata extraction owned by M6 Library; gapless/crossfade are Post-1.0 |
| M4 Queue                     | TESTED     | Queue basics, TD-015 pending identity, TD-016 cancellation terminal, repeat modes (none/one/all) and deterministic shuffle navigation — all TESTED (a977378, f93a6a8; 441-pass suite). ORIGINAL CONTRACT CLOSED: reorder (move) implemented (a52ce27); navigation truthful (has_next/has_previous service-level); empty-queue semantics deterministic; max-tracks capacity (QueueCapacityError). |
| M5 Database/Settings         | TESTED     | M5 ORIGINAL CONTRACT CLOSED: schema versioning (CURRENT_SCHEMA_VERSION=1, settings row schema_version) + migration framework v0→v1 (idempotent, transactional rollback, fail-closed on newer schema) + session snapshot (JSON session_snapshot row, strict decode, fresh-on-malformed) + queue restore (restore_session, capacity guard, duplicates preserved) + non-autoplay resume (prepare_for_resume, coherence rule, no fabricated current) + runtime checkpoints (PersistenceCoordinator, 5000ms position throttle) + theme/window geometry persistence + LKG integration (full-row comparison includes all new rows). M5-FINAL-CORRECTION: restore is guarded (no self-overwrite of the resume snapshot); volume/mute persist at runtime (no shutdown dependency); coordinator lifecycle explicit (start/stop/shutdown, freeze + unsubscribe, idempotent); durable position marker advances only on successful save (retry on failure, no crash). M5-LAST-GATE-2: two-phase resume confirmation (media acceptance ≠ position confirmed — the restored playback authority holds until the backend confirms a position, clamp tolerated, position 0 valid); queue mutations during the resume window persist via hybrid snapshots (live queue + restored playback truth); coherence-break/remove-current/rejection/supersession release the restore authority. M5-PRODUCTION-LIFECYCLE-GATE (65facc3): production lifecycle start→restore verified identical to tests; reentrant seek confirmation (arm-before-seek, unchanged-position, seek-failure disarm, zero-position via backend-reported position); queue-coherence-aware durable encode (no resurrected playback identity); sqlite connections closed explicitly (no GC dependence).|
| M6 Library                   | TESTED     | M6 ORIGINAL CONTRACT CLOSED + PRODUCTION COMPOSITION VERIFIED + CROSS-PERSISTENCE VERIFIED + AUTHORITATIVE DATA DECODE VERIFIED (M6.0-M6.8 per docs/M6_LIBRARY_MASTER_PLAN.md §8-§9): canonical model v2, persistent versioned index, incremental engine (no reparse of unchanged), async pipeline (supersession/cancellation/progress; TD-009 owned), artwork v2 (front/local/digest cache), canonical projections (six views one model, key-based selection), modular presentation (TD-017 resolved), golden+scale gates (beff4a0 + 01fe2ec). PRODUCTION INTEGRATION CORRECTION (39f0f3b..a3772bb): index/prefs/playlists wired in the production graph (bootstrap._build_services shared with tests), token per generation, worker never writes durable state (apply_delta after the generation gate), owner-thread dispatcher (QueuedConnection), shutdown lifecycle, album year deterministic, artist album_count canonical, artwork pruning + two-pass front, albumMode preserved, scan progress/cancel vertical, TrackRef technical carrier + facts-only quality labels, Michi fallback RECLASSIFIED to M9, scale memory claim corrected to M12. 26 production-composition gates green (test_m6_production_composition.py). CROSS-PERSISTENCE GATE (a3772bb..FINAL HEAD): provenance = authoritative logical state (settings + library_prefs via centralized _AUTHORITATIVE_TABLES; pre-M6 absence == empty; cache divergence never invalidates), LKG full-database snapshot verified, M6 user data (favorites/history/recently-added/playlists) restored verbatim through recovery and loaded by the production graph, index preserved/rebuildable across recovery, album technical summary honesty (EXACT/MIXED/PARTIAL/UNKNOWN — known+unknown never definitive), immutable ScanProgressSnapshot at the thread boundary. 26 cross-persistence gates green (test_persistence_cross_context.py). AUTHORITATIVE DECODE GATE (449bbdd..FINAL HEAD): strict string-list decoders (LOAD NEVER RAISES, no fabrication, no partial salvage), strict playlist root/entry validation (valid siblings preserved), explicit required-vs-optional authoritative tables (settings required fail-closed; library_prefs optional pre-M6), malformed-data production goldens (graph builds safely, no fabricated user state, recovery-safe). 53 decode gates green (test_persistence_authoritative_decode.py). |
| M7 Search                   | OPEN        | RICH CANONICAL LOCAL SEARCH IN PROGRESS (M7.0 contract reconciled at docs/M7_SEARCH_MASTER_PLAN.md; baseline ee8c23f): multi-entity/multi-field/multi-token in-memory search over the canonical M6 model, accent/case-insensitive normalization with raw query preserved, deterministic EXACT/PREFIX/TOKEN_PREFIX/SUBSTRING ranking, unified SearchProjection consumed by all six album views, corpus derived and rebuilt on structural change only; bootstrap substring search remains FUNCTIONAL; FTS POST-1.0; AI/vector/network NOT involved; no persistence; no filesystem/Mutagen access |
| M8 Navigation                | TESTED     | AppRoute navigation across all four screens                                                                                                              |
| M9 UI Foundation             | TESTED     | Tokens + primitives + shell; QML smoke tests                                                                                                             |
| M10 Settings                 | TESTED     | Persistence + restart gate verified                                                                                                                      |
| M11.1 Failure Contracts      | TESTED     | Runtime failure contracts verified                                                                                                                       |
| M11.2A Persistence Detection | TESTED     | Read-only health taxonomy verified; consumed by the M11.2D startup preflight (TESTED)                                                                      |
| M11.2B LKG Backup/Recovery   | TESTED     | Last-known-good backup (`<db>.lkg`) + non-destructive recovery staging verified (primitives consumed by M11.2E automatic recovery)                                     |
| M11.2C Field-Level Recovery  | TESTED     | Per-field malformed-data fallback with warnings (safe read fallback, no writeback); health classification remains strict (MALFORMED_DATA)                |
| M11.2D Startup Preflight     | TESTED     | Read-only preflight before any writable open; deterministic health routing; staged candidates are installed by M11.2E only after validation for recoverable states                    |
| M11.2E Recovery              | TESTED     | Validated automatic restore + quarantine: healthy-LKG-authorized trusted candidate installed atomically after byte-exact quarantine evidence; terminal states non-recovering; LKG preserved; field malformed stays on M11.2C. LKG committed WAL-visible state preserved; LKG sidecars are never recovery cleanup targets. |

Transitions pending per the canonical 1.0 contract: all components with outstanding Required-1.0 gaps must reach TESTED before M15. M6 is TESTED / ORIGINAL CONTRACT CLOSED (M6.0-M6.8, beff4a0/01fe2ec); M11.2A-E persistence recovery is COMPLETE for Required 1.0; TD-016 (Queue/Playback cancellation-terminal synchronization) is RESOLVED; LOCAL-01 (Canonical Music Model) is DONE (ba1532d); LOCAL-02 (Artwork Pipeline) is DONE (9b16504); LOCAL-03 (Rich Library Views) is DONE (e7416ac); LOCAL-04 (PathView) is DONE (635b35b); LOCAL-05 (Favorites / History) is DONE (938191b); LOCAL-06 (Playlists) is DONE (ccdbc85); LOCAL-STABILIZATION-01 is DONE (5 commits, 584-pass suite); LOCAL-META-02 (Rich Canonical Metadata) is DONE (4 commits, 619-pass suite); the next authorized WP is M7 — SEARCH per MASTER_ROADMAP_1.0.md.
