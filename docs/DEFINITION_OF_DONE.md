# Definition of Done

Governance authority for readiness and completion gates. Owns Definition of Ready (DoR), Definition of Done (DoD), and the Golden Path. No gate definition or delivery sequence exists outside this document.

## Definition of Ready

A work package SHALL NOT transition from BACKLOG to READY until all seven DoR criteria are evidenced. The readiness authority assesses each criterion before admission.

| #   | Criterion                     | Requirement                                                                                                                       |
| --- | ----------------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Responsibility                | Ownership is assigned and recorded.                                                                                               |
| 2   | Explicit scope                | The deliverable boundary is documented: what is in, what is out, and any known interactions with adjacent deliverables.           |
| 3   | Known dependencies            | All predecessor work packages are DONE or explicitly acknowledged as non-blocking with a rationale and mitigation.                |
| 4   | Sufficiently defined contract | The deliverable contract is documented with enough precision for implementation.                                                  |
| 5   | Applicable invariants         | All applicable invariants from INVARIANTS.md are identified and will be verified.                                                 |
| 6   | Acceptance criteria           | Every requirement has at least one verifiable acceptance criterion stated in Given/When/Then form.                                |
| 7   | Verification strategy         | The verification approach is named: test layer, scope, coverage, and the exact command or assertion that will prove the criteria. |

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

## Golden Path

The Golden Path is the singular end-to-end product sequence that MUST function correctly for every release. It is the canonical acceptance walkthrough; no release SHALL proceed if any step fails.

### Sequence

```
clean install → start app → select music directory/library → scan → browse → search → select track → play → pause/resume → seek → previous/next → manage Queue → shuffle/repeat → close → restart → recover valid consistent state
```

### Rules

1. Every step MUST be executable and verifiable in sequence.
2. Intermediate state (library, queue, settings, playback position) MUST survive restart and recover to a valid consistent state.
3. A release candidate SHALL NOT proceed if any Golden Path step fails or requires a workaround.
4. The Golden Path is exhaustive for the core product loop. Extensions (plugins, integrations, ecosystem features) augment it but do not replace it.
