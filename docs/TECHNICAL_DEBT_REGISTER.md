# Technical Debt Register

Governance authority for acknowledged technical debt. Every entry records a
conscious shortcut, deferred decision, or known gap with its severity, source,
reproducible symptom, mitigation, and target resolution phase. No debt exists
outside this document.

Debt severity is distinct from the P0/P1 release gate (INVARIANTS.md). Severity
measures the operational risk and compounding cost of the debt itself, not its
impact on a release candidate.

## Severity Scale

| Severity    | Definition                                                        |
| ----------- | ----------------------------------------------------------------- |
| MINOR       | Cosmetic or low-impact; no user-facing effect; resolves passively |
| MODERATE    | Tangible drag on velocity or quality; requires active mitigation  |
| SIGNIFICANT | Blocks a capability or verification path; must resolve before 1.0 |
| SEVERE      | Carries data-loss, corruption, or systematic failure risk         |

## Register

| ID     | Severity    | Source        | Description                                                                                                                                                                                                                  | Repro                                                                                                    | Mitigation                                                                                                      | Target       |
| ------ | ----------- | ------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------- | ------------ |
| TD-001 | SIGNIFICANT | M0 Foundation | Architecture dimensions D1-D10 remain unresolved. Language/runtime, layers, state ownership, composition, lifecycle, concurrency, QML boundary, audio port, persistence, and error/effect models have no selected mechanism. | Attempt to select a toolchain or framework — every dimension requires a decision before M1 can proceed.  | ADR sequence A1-A5 resolves D1-D10 before M1 Bootstrap; no tooling selected until ADRs are Accepted.            | M1 Bootstrap |
| TD-002 | SIGNIFICANT | M0 Foundation | Verification is limited to manual structural shell checks. No automated test runner, framework, or CI verification gate exists.                                                                                              | Run `ctest` or any test command — no target, framework, or harness present.                              | M1 Bootstrap introduces the first runnable CTest target; each subsequent M phase adds its own test suite.       | M1 Bootstrap |
| TD-003 | MODERATE    | G3 Governance | Prettier formatting enforcement is manual. The `npx prettier --write` check is executed ad-hoc during verification, not as an automated gate.                                                                                | Submit a change with trailing whitespace or inconsistent line width — no CI hook rejects it.             | Integrate Prettier into CI pipeline at M1 Bootstrap (pre-commit hook or CI check).                              | M1 Bootstrap |
| TD-004 | MODERATE    | M0 Foundation | Markdown link validation is not automated. Broken cross-references between governance authorities may go undetected until a human navigates them.                                                                            | Insert a broken link in any governance document — no automated check surfaces it.                        | Integrate link validation (lychee or equivalent) into CI at M1 Bootstrap.                                       | M1 Bootstrap |
| TD-005 | MODERATE    | M0 Foundation | Hybrid parity between OpenSpec artifacts and Engram observations is maintained manually. Drift between filesystem authorities and persistent memory is possible without automated reconciliation.                            | Modify a spec file without updating the corresponding Engram observation — no tool detects the mismatch. | Parity verification is documented in apply-progress.md per work unit; automated parity check deferred to M1 CI. | M1 Bootstrap |
| TD-006 | MINOR       | M0 Governance | The 22 feature exclusions from M0 scope are deferred to POST_1_0_BACKLOG without prioritization or sizing beyond category labels.                                                                                            | Open POST_1_0_BACKLOG.md — all entries carry deferral rationale but lack implementation sizing.          | Backlog grooming at M16 exit assigns t-shirt sizing and rough priority to each entry.                           | M16 Stable   |
| TD-007 | MINOR       | G1 Governance | The `.gitignore` file is stack-neutral by design but will require expansion when a build system and language are selected. Current patterns cover only OS/editor/environment artifacts.                                      | Add a `build/` directory or compiled artifact — it is not ignored and pollutes `git status`.             | Build-system-specific patterns appended to `.gitignore` as part of M1 Bootstrap deliverable.                    | M1 Bootstrap |
