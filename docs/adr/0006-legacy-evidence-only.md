# ADR 0006: Legacy is evidence only

## Title

The Legacy codebase is read-only evidence; every rebuild decision is made on the new contract, not inherited from Legacy.

## Date

2026-08-12

## Context

The rebuild starts from an empty workspace. Two distinct prior authorities exist: the historical Legacy repository (pitydah/michi-legacy, frozen for evidence at `63914a00...`, a Python/PySide6/QML application) and the superseded clean-rebuild governance draft (M0 Foundation v2 artifacts anticipating C++20/Qt 6). Both contain useful product concepts — features, UX ideas, and structural patterns — but neither is the target. The risk is silent inheritance: treating prior design choices as if they were still binding, or copying prior code/tests into the new repository.

## Decision

- Governance documents use exactly two evidence class labels: **LEGACY EVIDENCE** for the historical Legacy repository (pitydah/michi-legacy @ `63914a00...`) and **SUPERSEDED CLEAN-REBUILD GOVERNANCE DRAFT** for the M0 Foundation v2 artifacts (see MIGRATION_LEDGER.md). Both are non-authoritative and read-only.
- Zero Legacy files are copied. Zero Legacy tests are executed or adapted.
- Classification of each prior concept is exact: ADAPT (concept carried over, re-implemented on the new stack), REWRITE (goal retained, implementation rebuilt), DISCARD (explicitly dropped, e.g. the retired CoverFlow successor — never to be restored or ported from Legacy). Distributed/ecosystem scope is NOT DISCARD: it is RETAINED as a future product capability, AFTER PLAYER STABLE, per MASTER_ROADMAP_1.0.md Product Scope and MIGRATION_LEDGER ML-110. Video was already rejected in Legacy itself (its test suite rejects video workflows); the rebuild independently declares it Not Applicable.
- The superseded clean-rebuild governance draft (C++20/Qt 6 anticipation with CMake/CTest) is distinct from Legacy: it is a draft of this rebuild, preserved only as historical context; it imposes no active requirements.
- The new contract (governance docs, ADRs, code) is the sole source of authority.

## Consequences

- Clear audit trail between Legacy concepts and new implementations.
- New code and tests are written from scratch against the new contract (new-tests-only policy in INVARIANTS.md).
- Distributed/ecosystem capabilities are NOT discarded: they are RETAINED as future product capabilities, AFTER PLAYER STABLE, per MASTER_ROADMAP_1.0.md Product Scope and MIGRATION_LEDGER ML-110. Video-related capabilities remain excluded: the product is audio-only.
- Anything not classified in the ledger has no standing; unclassified Legacy material is not a dependency.

## Alternatives considered

- **KEEP Legacy artifacts where they still work**: preserves engineering investment, but the Legacy implementation does not satisfy the clean rebuild's architecture, ownership, lifecycle, testing, and scope contracts. Although both use Python/PySide6/QML, the clean rebuild intentionally does not reuse Legacy files because responsibilities, boundaries, and state ownership are being reconstructed from scratch. Rejected.
- **Full re-derivation without a ledger**: no traceability; reviewers cannot distinguish informed decisions from accidental omissions. Rejected.
- **Copy Legacy tests as regression coverage**: violates the new-tests-only policy and imports Legacy assumptions into the new contract. Rejected.

## Status

Accepted
