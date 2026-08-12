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

## Resolved Debt

Entries TD-001 through TD-007 were registered against the historical superseded plan
(C++20 architecture with CMake/CTest, C++ test frameworks, and Prettier).
They are **RESOLVED** — superseded by the adoption of the Python/PySide6 stack
(ADR 0001). They impose no active requirements and are retained only as history.

| ID     | Original entry                                      | Resolution |
| ------ | --------------------------------------------------- | ---------- |
| TD-001 | D1–D10 architecture dimensions unresolved           | RESOLVED — dimensions decided via Accepted ADRs 0001–0006 on the Python/PySide6 stack |
| TD-002 | No automated test runner or CI verification gate    | RESOLVED — pytest (154 tests) + Ruff + `python -m build` in GitHub Actions CI, green |
| TD-003 | Prettier formatting enforcement manual              | RESOLVED — superseded by Ruff (`ruff check` / `ruff format --check`) |
| TD-004 | Markdown link validation not automated              | RESOLVED — superseded by doc reconciliation workflow |
| TD-005 | Hybrid parity (OpenSpec/Engram) maintained manually | RESOLVED — superseded by evidence-based governance reconciliation |
| TD-006 | 22 M0 exclusions unsized                            | RESOLVED — POST_1_0_BACKLOG.md carries sizing for all deferred entries |
| TD-007 | `.gitignore` stack-neutral and incomplete           | RESOLVED — repository has a build system (setuptools); patterns added |

## Active Debt

| ID     | Severity    | Source        | Description | Repro | Mitigation | Target |
| ------ | ----------- | ------------- | ----------- | ----- | ---------- | ------ |
| TD-008 | SIGNIFICANT | M4 Queue / M2 Playback | Queue↔Playback atomicity: `QueueService.play_index`/`next`/`previous` mutate `current_index` before `PlaybackService.load_and_play` completes. A playback failure (missing file, unsupported format) can leave queue and playback divergent — the queue points at a track playback never loaded. | Enqueue a track pointing to a missing file, trigger play_index, then next: current_index advances while playback state does not match. | Next technical work package: make queue index transitions contingent on successful load (rollback or confirm-after-load semantics), with regression tests. | Next technical WP (before M11.2B-E) |
| TD-009 | MODERATE    | M6 Library     | Library scan runs synchronously on the UI thread; large directories freeze the UI during scan. | Scan a directory with thousands of files: UI is unresponsive until scan completes. | Move scanning off the UI thread (worker) or incrementalize; track progress in LibraryState. | M12 Performance |
| TD-010 | MODERATE    | M3 Complete Playback | Metadata extraction (title/artist/album/duration) is not implemented; only the filename stem is shown. REQUIRED for 1.0 per the canonical contract. | Load any tagged audio file: display shows filename, not tags. | Implement basic metadata extraction (title/artist/album/duration) behind the library/playback services. | Before M12 (Required 1.0) |
| TD-011 | MODERATE    | M4 Queue       | Shuffle and repeat (none/one/all) are not implemented. REQUIRED for 1.0 per the canonical contract. | No shuffle/repeat controls exist in queue or UI. | Implement shuffle (deterministic seed) and repeat modes in QueueService with tests. | Before M12 (Required 1.0) |
| TD-012 | MODERATE    | Governance     | No enforced coverage threshold: docs reference TESTED state evidence, but no coverage tooling or threshold exists. | Run any coverage tool: none configured. | Adopt coverage tooling (pytest-cov or equivalent) with a phase threshold; until then TESTED is evidence-based (suite passing) per DEFINITION_OF_DONE.md. | M12 Performance |
| TD-013 | MODERATE    | M6 Library     | Filesystem-disappeared library degradation: if library files are removed/moved while the app runs, there is no watch or handling; stale entries persist silently. | Remove a scanned file from disk during runtime: it remains listed and fails only on play. | Add rescan/validation handling for missing files (explicit diagnostic, not silent). | After M11.2B-E (filesystem degradation WP) |
| TD-014 | MINOR       | Repository metadata | Legacy repository metadata still describes the stack as "PySide6 and GStreamer". Documented only; no functional impact. | Read repository metadata: mentions GStreamer, which is not part of the architecture. | Update metadata descriptions when touched. | Opportunistic |

## Rules

1. New debt is admitted only with severity, source, description, repro, mitigation, and target.
2. RESOLVED entries are never deleted; they move to the Resolved Debt section with resolution rationale.
3. SIGNIFICANT debt blocks 1.0: TD-008 must be resolved before release; TD-010/TD-011 represent Required-1.0 capability gaps and must be closed by their scheduled work packages.
