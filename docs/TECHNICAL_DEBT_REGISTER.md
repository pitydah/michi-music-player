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

Entries TD-001 through TD-007 were registered against the superseded clean-rebuild
governance draft (M0 Foundation v2: C++20 architecture anticipation with CMake/CTest,
C++ test frameworks, and Prettier).
They are **RESOLVED** — superseded by the adoption of the Python/PySide6 stack
(ADR 0001). They impose no active requirements and are retained only as history.
TD-008A (current era) is also resolved — see its resolution note below. TD-008B
(the async half of TD-008) is implemented and regression-tested locally but
remains in Active Debt until final CI verification.

| ID     | Original entry                                      | Resolution                                                                                                                                                              |
| ------ | --------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| TD-001 | D1–D10 architecture dimensions unresolved           | RESOLVED — dimensions decided via Accepted ADRs 0001–0006 on the Python/PySide6 stack                                                                                   |
| TD-002 | No automated test runner or CI verification gate    | RESOLVED — pytest (154 tests) + Ruff + `python -m build` in GitHub Actions CI, green                                                                                    |
| TD-003 | Prettier formatting enforcement manual              | RESOLVED for code — Ruff automates code format checks (`ruff check` / `ruff format --check`); Markdown docs remain formatted manually with Prettier in the SDD workflow |
| TD-005 | Hybrid parity (OpenSpec/Engram) maintained manually | RESOLVED — superseded by evidence-based governance reconciliation                                                                                                       |
| TD-006 | 22 M0 exclusions unsized                            | RESOLVED — POST_1_0_BACKLOG.md carries sizing for all deferred entries                                                                                                  |
| TD-007 | `.gitignore` stack-neutral and incomplete           | RESOLVED — repository has a build system (setuptools); patterns added                                                                                                   |
| TD-008A | Queue↔Playback atomicity (synchronous half): `QueueService.play_index`/`next`/`previous` mutated `current_index` before `PlaybackService.load_and_play` returned. A synchronous playback failure (missing file, unsupported format) could leave queue and playback divergent — the queue pointing at a track playback never loaded. | RESOLVED — confirm-after-effect: `QueueService.play_index` requests playback before committing `current_index`; `next`/`previous` route through the same path; synchronous exceptions propagate with no commit. Committed 8d555a45 (`fix(queue): make playback transitions failure-atomic`). Regression-tested by failure injection (`tests/test_queue_service.py::TestNavigationFailureAtomicity`, `tests/test_convergence.py::TestEndOfMedia::test_auto_advance_failure_preserves_index`); full suite 162 passed. |

## Active Debt

| ID     | Severity    | Source                 | Description                                                                                                                                                                                                                                                                                      | Repro                                                                                                                                  | Mitigation                                                                                                                                                 | Target                                     |
| ------ | ----------- | ---------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------ |
| TD-004 | MODERATE    | Governance             | Markdown link validation is not automated: no link checker runs in CI or as a repo tool; internal cross-references are validated manually during reconciliation. Reopened from the resolved table — the reconciliation workflow does not constitute automation.                                  | Run any link checker on `docs/`: none is configured.                                                                                   | Adopt automated markdown link validation in the documentation pipeline; until then, reconciliation greps validate cross-links.                             | M12 Performance                            |
| TD-008B | SIGNIFICANT | Playback pipeline      | Queue↔Playback atomicity (asynchronous half): Qt Multimedia loads media asynchronously, so `setSource()`/`play()` returning did not prove acceptance. Queue transitions and `PlaybackState.PLAYING` were committed on request instead of on media acceptance, so rejected/stale loads could still become canonical state. | Request a track with an unsupported/corrupt file: before TD-008B the queue advanced to it immediately and playback claimed PLAYING although the backend never loaded the media. | Implemented: one explicit acceptance point — `AudioPort` media-accepted/rejected subscriptions (`subscribe_media_accepted`/`subscribe_media_rejected`), `QtMultimediaBackend` translates `LoadedMedia`→accepted and `InvalidMedia`/`errorOccurred`→rejected with the current source identity; `PlaybackService` owns the pending candidate and resolves it on acceptance (single commit, stale callbacks ignored via identity match + slot supersession, `stop()` invalidates); `QueueService` commits `current_index` only through the accepted-candidate callback with an index-identity guard; rejection keeps the last committed index/file with STOPPED + error. Fully regression-tested locally (`tests/test_queue_service.py::TestAsyncAcceptance`, `tests/test_playback_service.py`, `tests/test_convergence.py::TestEndOfMedia`, `tests/test_qt_backend.py::TestQtBackendMediaTranslation`); full suite 188 passed, ruff clean, build green. Remote CI evidence is the closing step. | Move to Resolved Debt on orchestrator final verification with CI evidence | TD-008B closeout WP                       |
| TD-009 | MODERATE    | M6 Library             | Library scan runs synchronously on the UI thread; large directories freeze the UI during scan.                                                                                                                                                                                                   | Scan a directory with thousands of files: UI is unresponsive until scan completes.                                                     | Move scanning off the UI thread (worker) or incrementalize; track progress in LibraryState.                                                                | M12 Performance                            |
| TD-012 | MODERATE    | Governance             | No enforced coverage threshold: docs reference TESTED state evidence, but no coverage tooling or threshold exists.                                                                                                                                                                               | Run any coverage tool: none configured.                                                                                                | Adopt coverage tooling (pytest-cov or equivalent) with a phase threshold; until then TESTED is evidence-based (suite passing) per DEFINITION_OF_DONE.md.   | M12 Performance                            |
| TD-013 | MODERATE    | M6 Library             | Filesystem-disappeared library degradation: if library files are removed/moved while the app runs, there is no watch or handling; stale entries persist silently.                                                                                                                                | Remove a scanned file from disk during runtime: it remains listed and fails only on play.                                              | Add rescan/validation handling for missing files (explicit diagnostic, not silent).                                                                        | After M11.2B-E (filesystem degradation WP) |
| TD-014 | MINOR       | Repository metadata    | The current clean-rebuild repository (pitydah/michi-music-player) metadata still describes the stack as "Python, PySide6 and GStreamer", while the active clean architecture uses Qt Multimedia (FFmpeg backend) and has no GStreamer integration. Documented only; no functional impact. (Historical Legacy GStreamer usage is a fact about Legacy, not a debt.) | Read the clean repository's description: mentions GStreamer, which is not part of the current architecture.                                                            | Update the clean repository metadata description when touched.                                                                                                      | Opportunistic                              |

## Required-1.0 Capability Gaps (not debt)

These entries are scheduled capability gaps of the canonical 1.0 contract, not technical debt: they are planned work against an explicit contract, not conscious shortcuts or deferred decisions. They are listed here for traceability only; the authority is the canonical 1.0 contract in MASTER_ROADMAP_1.0.md.

| ID     | Gap                                                                                                    | Contract status               | Work package              |
| ------ | ------------------------------------------------------------------------------------------------------ | ----------------------------- | ------------------------- |
| TD-010 | Metadata extraction (title/artist/album/duration) is not implemented; only the filename stem is shown. | Required 1.0, not implemented | Before M12 (Required 1.0) |
| TD-011 | Shuffle and repeat (none/one/all) are not implemented.                                                 | Required 1.0, not implemented | Before M12 (Required 1.0) |

## Rules

1. New debt is admitted only with severity, source, description, repro, mitigation, and target.
2. RESOLVED entries are never deleted; they move to the Resolved Debt section with resolution rationale.
3. SIGNIFICANT debt blocks 1.0: TD-008A is RESOLVED (see Resolved Debt); TD-008B is the current open SIGNIFICANT entry, implemented and regression-tested locally with remote CI evidence pending as its closing step. Required-1.0 capability gaps (TD-010/TD-011) are not debt; they are tracked by the canonical 1.0 contract in MASTER_ROADMAP_1.0.md and must close before release per their scheduled work packages.
