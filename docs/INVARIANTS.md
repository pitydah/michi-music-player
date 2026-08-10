# Invariants

Governance authority for constraints that apply across every phase, work package, and release. Owns freeze/reopen rules, the P0/P1 release gate, feature-freeze policy, WIP limits, baby-steps policy, and the new-tests-only rule. No constraint exists outside this document.

## Freeze

A freeze suspends scope expansion for a defined boundary. It does not halt in-progress work on already-admitted items.

### Prerequisites

A freeze SHALL NOT be declared unless ALL of the following are confirmed:

- Stable contract and implementation for the boundary being frozen.
- New tests passed for all work packages within the boundary.
- Integration validated end-to-end.
- Architecture verification confirmed — design decisions are followed and no unapproved deviations exist.
- Zero P0 and zero P1 within the boundary (no P0/P1 open).

### Reopen

A reopen lifts a freeze and restores normal admission. A reopen SHALL NOT occur except for exactly these reasons:

| Reason                  | Trigger                                                                                       |
| ----------------------- | --------------------------------------------------------------------------------------------- |
| Bug                     | A defect in released behavior that produces incorrect results.                                |
| Regression              | Previously working behavior is broken by a recent change.                                     |
| Vulnerability           | A security weakness that enables unauthorized access, data exposure, or privilege escalation. |
| Accessibility           | A defect that prevents users from accessing or operating core functionality.                  |
| Layout breakage         | The UI layout is broken such that content is unreachable or misrendered.                      |
| Unavoidable integration | An external dependency change forces an adaptation with no reasonable deferral path.          |

A reopen MUST record: the reopened boundary, the reason, the approving authority, and the effective date.

## P0/P1 Release Gate

The P0/P1 release gate is the mandatory quality barrier before any release candidate proceeds to release.

### P0 — Blocker

| Condition                     | Definition                                                                              |
| ----------------------------- | --------------------------------------------------------------------------------------- |
| Corruption                    | Data or state corruption that is irreversible or propagates.                            |
| Library loss                  | Loss of music library, metadata, playlists, or user-configured state.                   |
| No start                      | The application cannot start or crashes immediately.                                    |
| Systematic Golden crash       | Any step in the Golden Path crashes consistently.                                       |
| Critical security             | Vulnerability that enables unauthorized access, data exposure, or privilege escalation. |
| Fundamental playback unusable | Play, pause, seek, or queue operations are completely non-functional.                   |

### P1 — Critical

| Condition                     | Definition                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------ |
| Core broken                   | A core capability — library, playback, queue, search, settings — is partially unavailable. |
| Severe state inconsistency    | Application state diverges from canonical truth without a recovery path.                   |
| Incorrect queue-playback      | The queue plays the wrong track, skips tracks, or violates shuffle/repeat contract.        |
| Incorrect primary persistence | Settings, library metadata, or queue state is lost, corrupted, or not restored on restart. |
| Severe Golden degradation     | One or more Golden Path steps fail intermittently or require workarounds.                  |

### Gate Rule

A release candidate SHALL NOT proceed to release when either P0 count > 0 or P1 count > 0. Both MUST be exactly zero: `Release: P0 = 0, P1 = 0`.

## Feature Freeze

A feature freeze prohibits new feature work from entering the pipeline while stabilization completes.

### Policy

1. New feature work packages SHALL NOT be admitted to READY during a feature freeze.
2. Legacy existence of a feature is insufficient to admit it. Pre-existing code or design from a prior system does not automatically qualify a feature for inclusion.
3. Unneeded features SHALL be routed to POST_1_0_BACKLOG with rationale.
4. Necessary features require an approved scope change with justification, risk acceptance, and mitigation.
5. A feature freeze SHALL NOT be lifted without an approved reopening exception.

## WIP Limits

Work-in-progress limits cap concurrent implementation to prevent overload, reduce context-switching, and keep delivery predictable.

### Limits

| Scope                                            | Maximum concurrent work |
| ------------------------------------------------ | ----------------------- |
| Principal architecture capability implementation | 1                       |
| Concurrent verification unit                     | 1                       |

### Policy

1. At most one principal architecture capability implementation SHALL be in progress at any time.
2. At most one verification unit SHALL be concurrent with the principal implementation.
3. No second dependent feature SHALL start before the first is stabilized: DONE, verified, and frozen.
4. WIP limits are evaluated at admission (BACKLOG → READY) and at work start (READY → IN_PROGRESS).

## Baby Steps

Every change SHALL be the smallest independently-verifiable unit of work that delivers measurable progress.

### Policy

1. Every change MUST be strictly reversible. A change that cannot be rolled back independently SHALL be split or rejected.
2. No copy-now-fix-later. Code that is knowingly incomplete, duplicated, or structurally broken SHALL NOT be admitted with the intent to fix it later.
3. No conscious structural debt for speed. If a shortcut creates known debt, it SHALL be rejected at READY.
4. A work package SHALL NOT bundle unrelated changes. Each package delivers one behavior, fix, or deliverable.
5. The smallest possible step is preferred; when a step could be 2 commits or 1, prefer 2 if each is independently verifiable.

## New-Tests-Only

Every behavioral change SHALL be accompanied by at least one passing test that verifies the new or changed behavior.

### Policy

1. New tests SHALL be written only from new specs, contracts, invariants, or accepted behavior.
2. No tests SHALL be written for Explore, Propose, Spec, or Design phases — those phases produce artifacts, not executable behavior.
3. Legacy tests, fixtures, mocks, helpers, snapshots, and infrastructure are read-only evidence and SHALL NEVER be copied or adapted.
4. A work package that introduces or modifies behavior SHALL include at least one passing test per behavioral change.
5. Tests SHALL verify the behavior described in the acceptance criteria. Generic smoke tests or unrelated coverage SHALL NOT substitute.
6. Do NOT impose fail-first while `strict_tdd` is false. Test-first is required only when `strict_tdd` is active.
7. A work package with zero passing new tests SHALL NOT reach DONE.
