# Master Roadmap 1.0

Michi Music Player — phase plan for the clean rebuild. Stack: Python 3.11+, PySide6 (Qt 6, Qt Multimedia with FFmpeg backend), QML, SQLite (WAL), pytest, Ruff, setuptools + build, GitHub Actions CI.

> **Superseded clean-rebuild governance draft**: M0 Foundation v2 governance artifacts of this rebuild (Proposed ADRs D1–D10, dated 2026-08-10) described a C++20/Qt 6 architecture with CMake, CTest, Catch2/doctest, and a `main.cpp` entry point. That anticipated direction was never implemented and is superseded by the Python/PySide6 stack (ADR 0001); it imposes **no active requirements**. It is preserved here only as historical context for reviewers.

Phases M0–M16 remain the roadmap skeleton. M0 (governance foundation) through M11.2A are executed on the current stack; the table below records their verified status. Remaining work follows the order in "Future Execution Order".

## Canonical 1.0 Contract

| Capability                                                                               | Decision       | Status                                               |
| ---------------------------------------------------------------------------------------- | -------------- | ---------------------------------------------------- |
| Playback controls (play/pause/resume/stop, seek, volume, mute, position/duration events) | Required 1.0   | Implemented                                          |
| Queue (add/remove/clear, play_index, next/previous, auto-advance)                        | Required 1.0   | Implemented                                          |
| Shuffle                                                                                  | Required 1.0   | Not implemented                                      |
| Repeat (none/one/all)                                                                    | Required 1.0   | Not implemented                                      |
| Gapless playback                                                                         | Post-1.0       | Deferred                                             |
| Crossfade                                                                                | Post-1.0       | Deferred                                             |
| Queue reorder (move)                                                                     | Post-1.0       | Deferred                                             |
| Queue persistence                                                                        | Post-1.0       | Deferred                                             |
| Playback position persistence                                                            | Post-1.0       | Deferred                                             |
| Current track recovery                                                                   | Post-1.0       | Deferred                                             |
| Settings persistence (volume/muted/last_directory/recent_files)                          | Required 1.0   | Implemented (restart gate)                           |
| `last_directory` persistence                                                             | Required 1.0   | Implemented                                          |
| Library scan (recursive, extension filter)                                               | Required 1.0   | Implemented                                          |
| Library index DB                                                                         | Post-1.0       | Deferred                                             |
| Basic metadata (title/artist/album/duration)                                             | Required 1.0   | Not implemented (filename stem only today)           |
| Cover art                                                                                | Post-1.0       | Deferred                                             |
| Search — simple substring filter                                                         | Required 1.0   | Implemented                                          |
| Search — full-text indexed                                                               | Post-1.0       | Deferred                                             |
| Settings persistence + corruption recovery                                               | Required 1.0   | Detection done (M11.2A); recovery pending (M11.2B-E) |
| Safe mode                                                                                | Post-1.0       | Deferred                                             |
| Watchdog                                                                                 | Post-1.0       | Deferred                                             |
| Video                                                                                    | Not applicable | Audio-only product                                   |
| Platform — Linux                                                                         | Required 1.0   | Primary target; M13 artifacts (AppImage/Flatpak/deb) |
| Platform — Windows                                                                       | Post-1.0       | Deferred                                             |
| Platform — macOS                                                                         | Post-1.0       | Deferred                                             |

## Component Statuses

Evidence-based; states per `docs/STATUS_MATRIX.md`.

| Component                    | Status     | Implemented                                                                                                                         | Gap                                                                                           |
| ---------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------- |
| M1 Bootstrap                 | TESTED     | ApplicationContainer composition root, explicit wiring, best-effort shutdown (first-error-wins), pytest + Ruff + build in CI        | —                                                                                             |
| M2 Minimal Playback          | TESTED     | Single-file play/stop via `QtMultimediaBackend` behind `AudioPort`                                                                  | —                                                                                             |
| M3 Complete Playback         | PARTIAL    | Play/pause/resume/stop, seek, volume, mute, position/duration events                                                                | Metadata extraction absent (Required 1.0); gapless/crossfade deferred (Post-1.0 per contract) |
| M4 Queue                     | PARTIAL    | Add/remove/clear, play_index, next/previous, auto-advance                                                                           | Shuffle, repeat, reorder absent                                                               |
| M5 Database/Settings         | PARTIAL    | Settings persistence (SQLite, WAL) through `SettingsRepository`/`SQLiteSettingsRepository`; restart gate                            | Full DB scope deferred (library index, queue/position persistence are Post-1.0)               |
| M6 Library                   | PARTIAL    | Recursive scan with extension filter; substring filter                                                                              | Metadata extraction, library index DB absent                                                  |
| M7 Search                    | FUNCTIONAL | Substring search filter over library                                                                                                | FTS / indexed search (Post-1.0)                                                               |
| M8 Navigation                | TESTED     | AppRoute navigation across now_playing/library/queue/settings                                                                       | —                                                                                             |
| M9 UI Foundation             | TESTED     | MichiTheme tokens; MichiButton/MichiPanel/MichiSlider/MichiTextField; AppShell/Sidebar/ContentHost; views                           | —                                                                                             |
| M10 Settings                 | TESTED     | SettingsService sole owner; volume/muted/last_directory/recent_files persisted; restart gate                                        | —                                                                                             |
| M11.1 Failure Contracts      | TESTED     | Runtime failure contracts; no silent exceptions                                                                                     | —                                                                                             |
| M11.2A Persistence Detection | TESTED     | Read-only `inspect_path`; taxonomy MISSING/HEALTHY/CORRUPT_DATABASE/MALFORMED_DATA/LOCKED/ACCESS_FAILURE/IO_FAILURE/UNKNOWN_FAILURE | —                                                                                             |
| M11.2B/C/D/E Recovery        | UNKNOWN    | —                                                                                                                                   | Not yet audited; backup/recovery, repair, safe-path handling pending                          |

## Future Execution Order

The next work proceeds in this order:

1. **Governance Reconciliation** (this change) — align all docs with the real stack and capability state.
2. **Queue↔Playback Atomicity** — `QueueService.play_index/next/previous` mutate `current_index` before `PlaybackService.load_and_play`; a playback failure can leave queue and playback divergent. Next technical work package. (TD-008, SIGNIFICANT)
3. **M11.2B/C/D/E Recovery** — backup/recovery and repair for settings persistence on top of the M11.2A taxonomy.
4. **Filesystem Degradation** — handling for library files disappearing at runtime (TD-013).
5. **M12 Performance** — benchmark and tune scan/startup/memory; CI performance gate.
6. **M13 Packaging** — Linux installable artifacts (AppImage/Flatpak/deb), icon suite, desktop integration, CLI entry points. Windows and macOS are Post-1.0 per the canonical contract.
7. **M14 Beta** — beta channel, opt-in telemetry, feedback loop, triage SLA.
8. **M15 Release Candidate** — zero P0/P1, full docs, migration guide, signed RC artifacts.
9. **M16 Michi Music Player 1.0 Stable** — public stable release, project FROZEN.

Required-for-1.0 gaps (shuffle, repeat, metadata extraction) are scheduled as work packages within this order before M12; they are part of the 1.0 contract and may not slip past M15.

## Gate

No phase proceeds to release without its status reaching the state required by its phase contract in `docs/DEFINITION_OF_DONE.md` and `docs/STATUS_MATRIX.md`, and the P0/P1 gate in `docs/INVARIANTS.md` must hold (P0 = 0, P1 = 0).
