# AI Development Policy — Architecture-First Baby-Step (26A)

Policy 26A governs every AI-assisted change in this repository: how features are
built, how tests are treated, and how work hands off between agents and humans.

**One-line summary**: never implement a feature in one shot; build it in
architecture-first baby steps, wire each slice into the real runtime, validate
with evidence, and report honest states.

## Scope

1. 26A applies to all AI-assisted implementation, refactoring, and test changes in this repo.
2. 26A complements, does not replace, the SDD precedence rules in AGENTS.md §2.
3. The orchestrator (human or lead agent) owns the sequence; agents execute steps, not skip them.

## Architecture first

4. **No code before architecture**: every non-trivial change starts with a written spec and an architecture approach (SDD phases or the equivalent evidence).
5. **No one-shot implementation**: never implement an entire feature in a single pass; split it into phases.
6. Required pipeline: `spec → architecture → phases → baby step → real wiring → validation → checkpoint`.
7. Each phase ends at a **checkpoint**: stop, verify, record evidence, then proceed or return.

## Baby steps and slices

8. A **baby step** is the smallest change that is real, wired, and demonstrable at runtime.
9. **Vertical slices**: build a thin full-stack slice (UI → service → data), not a complete horizontal layer.
10. **Connect early**: wire the slice into the real runtime as soon as it is syntactically sound; no long-lived branches in isolation.
11. **Design for testability**: seams, dependency injection, no hidden globals — testability is an architecture decision, not a retrofit.
12. The checkpoint validates the slice end-to-end; a slice that only passes unit-level checks is not complete.

## Tests are evidence, not specification

13. A test records behavior you verified; it does not define what the product should be.
14. **No test appeasement**: never weaken or delete assertions to turn red green.
15. **No patch cascade**: fix the root cause at its own checkpoint; do not stack fixes on fixes in the same work unit.
16. **No monolithic dump**: no giant multi-file changes mixing unrelated work.
17. **No mock-only completion**: a feature is not done until exercised against real wiring, or an explicit `N/A` records why not.
18. Honest states only: PASS / PARTIAL / FAIL / NOT_TESTED / BLOCKED. No "fully stabilized" claims.
19. When product and test disagree, the product decision belongs to the architecture checkpoint — never to the test's assertions.

## Feature states

20. Feature states: **CODED → WIRED → PRODUCTIVE → VALIDATED → STABLE**.

| State | Evidence required |
|---|---|
| CODED | Unit-level; code exists, tests may be partial |
| WIRED | Connected to the real runtime path |
| PRODUCTIVE | Used in a real flow (manual or automated exercise) |
| VALIDATED | Tests + evidence recorded at a checkpoint |
| STABLE | Repeated green evidence (see promotion in Development Convergence Mode) |

21. A feature may be called STABLE only with repeated green evidence; a single green run is not enough.

## Tiers and gates

22. New code and its tests default to tier T2 (advisory) and promote to T1 through the promotion workflow in [Development Convergence Mode](../testing/DEVELOPMENT_CONVERGENCE_MODE.md#promotion-workflow-development-stable).
23. T0 Safety Gate and T1 regressions always block; no feature ships that weakens either.
24. Environment-dependent checks go to T3 explicitly; they never masquerade as T1/T2.
25. Failing legacy tests are triaged with KEEP / REWRITE / QUARANTINE / DELETE — never appeased (clause 14).

## Orchestrator responsibility

26. The orchestrator splits tasks into work units, each sized for one checkpoint and one reviewable commit (see the work-unit commit rules in the SDD workflow).
27. No skill or agent may expand scope, change contracts, or create artificial compatibility without explicit evidence and authorization (AGENTS.md §2).
28. A work unit is done when: code, wiring, tests, evidence, and rollback boundary are recorded together.

An operational rollback boundary names the exact files or behavior that can be
removed without unrelated work, plus the recovery command pattern: `git revert
<commit>` of the work unit, or a targeted file restore (`git checkout <sha> --
<path>`). It is stated independently of commit creation; uncommitted work
units still require one.
29. If a step fails validation, return to the last checkpoint — never move forward on a failed checkpoint.
30. Blocked work is reported as BLOCKED with its reason; it is never silently skipped.

## Engram handoff rules

31. At every handoff, save to Engram: What / Why / Where / Learned, plus the current feature state and last checkpoint.
32. Handoff records must include the architecture rationale, not just the diff; decisions are saved as decisions.
33. On session end, save a session summary (goal, instructions, discoveries, next steps); after compaction, re-save the summary before continuing work.

## Normative reference

34. **AGENTS.md normativa**: AGENTS.md carries a concise Spanish normative section summarizing 26A and Development Convergence Mode. It is normative for agents, links to this policy and to the testing docs, and does not duplicate their content.
