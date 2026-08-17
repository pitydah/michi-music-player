# Definition of Done

Governance authority for readiness and completion gates. Owns Definition of Ready (DoR), Definition of Done (DoD), and the Golden Path. No gate definition or delivery sequence exists outside this document.

## Definition of Ready

A work package SHALL NOT transition from BACKLOG to READY until all seven DoR criteria are evidenced. The readiness authority assesses each criterion before admission.

| #   | Criterion                     | Requirement                                                                                                             |
| --- | ----------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 1   | Responsibility                | Ownership is assigned and recorded.                                                                                     |
| 2   | Explicit scope                | The deliverable boundary is documented: what is in, what is out, and any known interactions with adjacent deliverables. |
| 3   | Known dependencies            | All predecessor work packages are DONE or explicitly acknowledged as non-blocking with a rationale and mitigation.      |
| 4   | Sufficiently defined contract | The deliverable contract is documented with enough precision for implementation.                                        |
| 5   | Applicable invariants         | All applicable invariants from INVARIANTS.md are identified and will be verified.                                       |
| 6   | Acceptance criteria           | Every requirement has at least one verifiable acceptance criterion stated in Given/When/Then form.                      |
| 7   | Verification strategy         | The verification approach is named: test layer, scope, and the exact command or assertion that will prove the criteria. |

All seven criteria MUST be met. Partial readiness SHALL NOT proceed.

## Definition of Done

A work package SHALL NOT transition from VERIFY to DONE until all eight DoD criteria are satisfied for every applicable condition. The completion authority assesses each criterion before acceptance.

| #   | Criterion                    | Requirement                                                                                                  |
| --- | ---------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1   | Contract implemented         | Every requirement in the contract has a corresponding implementation trace.                                  |
| 2   | NEW tests from scratch       | Every new test is written from scratch for this work package; no copied or adapted Legacy tests.             |
| 3   | Integration validated        | Integration boundaries are verified end-to-end.                                                              |
| 4   | Errors explicit              | All error paths are handled explicitly; no silent failures.                                                  |
| 5   | Lifecycle validated          | Component lifecycle — create, initialize, run, shutdown — is verified.                                       |
| 6   | Docs updated                 | All affected documentation is updated and consistent.                                                        |
| 7   | No duplicated/parallel truth | There is exactly one authority for each fact; no competing sources.                                          |
| 8   | Verification approved        | Independent verification confirms contract implementation, design adherence, and zero unapproved deviations. |

All applicable criteria MUST be met. A work package that satisfies only a subset SHALL NOT be marked DONE.

## Evidence-Based Definition of TESTED

The component state TESTED (see STATUS_MATRIX.md) is currently defined by evidence, not by a coverage threshold:

- The automated test suite passes in full: `pytest -q` (current count per STATUS_MATRIX evidence and the latest green Michi CI run; no hardcoded count).
- Static quality gates pass: `ruff check src tests` and `ruff format --check src tests`.
- CI is green (lint, test with `QT_QPA_PLATFORM=offscreen`, build via `python -m build`).

Coverage tooling and an enforced threshold are **deferred** (tracked in TECHNICAL_DEBT_REGISTER.md). Until such tooling exists, TESTED means "automated suite passing as evidenced above" — there is no numeric coverage requirement, and no phase may claim TESTED solely from documentation. This section resolves the previous wording conflict that referenced a coverage threshold without tooling.

## Golden Path

The Golden Path is the singular end-to-end product sequence that MUST function correctly for every release. It is the canonical acceptance walkthrough; no release SHALL proceed if any step fails.

### Sequence (annotated: executable today vs blocked)

```
clean install            [blocked-by: packaging — M13; 1.0 artifacts are Linux
                          (AppImage/Flatpak/deb); today: venv + `pip install -e .`]
→ start app              [executable]
→ select music directory/library
                         [executable]
→ scan                   [executable]
→ browse                 [executable]
→ search                 [executable — substring filter]
→ select track           [executable]
→ display metadata       [blocked-by: metadata work package — Required 1.0, not implemented]
→ play                   [executable]
→ pause/resume           [executable]
→ seek                   [executable]
→ previous/next          [executable]
→ manage Queue           [executable — add/remove/clear/move/play_index]
→ shuffle/repeat         [executable]
→ close                  [executable]
→ restart                [executable]
→ recover valid consistent state
                         [partial — settings (volume/muted/last_directory/recent_files) persist;
                          queue/playback-position persistence is Post-1.0 by contract]
```

### Rules

1. Every step MUST be executable and verifiable in sequence. Steps marked `blocked-by` are allowed to gate the corresponding release milestone; they MUST be unblocked before that milestone's acceptance.
2. Restart recovery preserves ONLY the state explicitly marked Required 1.0 in MASTER_ROADMAP_1.0.md. Required today: settings persistence (volume, muted, last_directory, recent_files). Post-1.0 and NOT restart requirements for 1.0: queue persistence, playback position, current track.
3. A release candidate SHALL NOT proceed if any Golden Path step fails or requires a workaround.
4. The Golden Path is derived exclusively from the canonical 1.0 contract (MASTER_ROADMAP_1.0.md). Post-1.0 capabilities (queue persistence, playback-position persistence, gapless, crossfade, non-Linux platforms) never appear as path steps; their absence is a contract decision, not a path gap.
5. The Golden Path is exhaustive for the core product loop. Extensions (plugins, integrations, ecosystem features) augment it post-1.0 but do not replace it.
