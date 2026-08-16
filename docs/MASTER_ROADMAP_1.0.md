# Master Roadmap 1.0

Michi Music Player — phase plan for the clean rebuild. Stack: Python 3.11+, PySide6 (Qt 6, Qt Multimedia with FFmpeg backend), QML, SQLite (WAL), pytest, Ruff, setuptools + build, GitHub Actions CI.

> **Superseded clean-rebuild governance draft**: M0 Foundation v2 governance artifacts of this rebuild (Proposed ADRs D1–D10, dated 2026-08-10) described a C++20/Qt 6 architecture with CMake, CTest, Catch2/doctest, and a `main.cpp` entry point. That anticipated direction was never implemented and is superseded by the Python/PySide6 stack (ADR 0001); it imposes **no active requirements**. It is preserved here only as historical context for reviewers.

Phases M0–M16 remain the roadmap skeleton. M0 (governance foundation) through M11.2A are executed on the current stack; the table below records their verified status. Remaining work follows the order in "Future Execution Order".

## Canonical 1.0 Contract

| Capability                                                                               | Decision       | Status                                                                                                                            |
| ---------------------------------------------------------------------------------------- | -------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| Playback controls (play/pause/resume/stop, seek, volume, mute, position/duration events) | Required 1.0   | Implemented                                                                                                                       |
| Queue (add/remove/clear, play_index, next/previous, auto-advance)                        | Required 1.0   | Implemented                                                                                                                       |
| Shuffle                                                                                  | Required 1.0   | Not implemented                                                                                                                   |
| Repeat (none/one/all)                                                                    | Required 1.0   | Not implemented                                                                                                                   |
| Gapless playback                                                                         | Post-1.0       | Deferred                                                                                                                          |
| Crossfade                                                                                | Post-1.0       | Deferred                                                                                                                          |
| Queue reorder (move)                                                                     | Post-1.0       | Deferred                                                                                                                          |
| Queue persistence                                                                        | Post-1.0       | Deferred                                                                                                                          |
| Playback position persistence                                                            | Post-1.0       | Deferred                                                                                                                          |
| Current track recovery                                                                   | Post-1.0       | Deferred                                                                                                                          |
| Settings persistence (volume/muted/last_directory/recent_files)                          | Required 1.0   | Implemented (restart gate)                                                                                                        |
| `last_directory` persistence                                                             | Required 1.0   | Implemented                                                                                                                       |
| Library scan (recursive, extension filter)                                               | Required 1.0   | Implemented                                                                                                                       |
| Library index DB                                                                         | Post-1.0       | Deferred                                                                                                                          |
| Basic metadata (title/artist/album/duration)                                             | Required 1.0   | Not implemented (filename stem only today)                                                                                        |
| Cover art                                                                                | Post-1.0       | Deferred                                                                                                                          |
| Search — simple substring filter                                                         | Required 1.0   | Implemented                                                                                                                       |
| Search — full-text indexed                                                               | Post-1.0       | Deferred                                                                                                                          |
| Settings persistence + corruption recovery                                               | Required 1.0   | M11.2A detection TESTED; M11.2B LKG/staging TESTED; M11.2C field recovery TESTED; M11.2D startup preflight TESTED; M11.2E automatic restore + quarantine TESTED — Required-1.0 persistence corruption recovery COMPLETE |
| Safe mode                                                                                | Post-1.0       | Deferred                                                                                                                          |
| Watchdog                                                                                 | Post-1.0       | Deferred                                                                                                                          |
| Video                                                                                    | Not applicable | Audio-only product                                                                                                                |
| Platform — Linux                                                                         | Required 1.0   | Primary target; M13 artifacts (AppImage/Flatpak/deb)                                                                              |
| Platform — Windows                                                                       | Post-1.0       | Deferred                                                                                                                          |
| Platform — macOS                                                                         | Post-1.0       | Deferred                                                                                                                          |

## Product Scope

- **Michi AI** — PRODUCT CAPABILITY: RETAINED. CURRENT REFACTOR: OUT OF SCOPE. IMPLEMENTATION: AFTER PLAYER STABLE, in the separate repository `pitydah/michi-ai`. Not embedded in the Player: no AI engine, models, providers, bridges, or runtime dependencies in this repository.
- **Audio Lab** — RETAINED. OUT OF SCOPE. AFTER PLAYER STABLE.
- **Streaming / Radio** — RETAINED. OUT OF SCOPE. AFTER PLAYER STABLE.
- **Sync** — RETAINED. OUT OF SCOPE. AFTER PLAYER STABLE.
- **Ecosystem integrations (Michi Link, Michi Mobile, Michi Micro Server, Michi Big Server, Michi Music Stream, Home Audio)** — RETAINED. OUT OF SCOPE. AFTER PLAYER STABLE.
- **Mix** — two distinct capabilities: MIX LOCAL (deterministic, local data, part of the Player, pre-Stable local work) and MIX INTELIGENTE (recommendations/models, Michi AI, AFTER PLAYER STABLE). The roadmap preserves both.
- **Playlists** — distinct from Queue (current session) and Mix (dynamically generated selection): a persistent user-curated collection, developed during Local Player Completion (pre-Beta).
- **CoverFlow** — RETIRED: DO NOT implement, restore, or port from Legacy. Successor: PathView (ACTIVE PRODUCT CAPABILITY, pre-Stable local album experience, built after metadata → canonical album model → artwork → QML album model → PathView).
- **Note**: "RETAINED" means the product concept remains; it is not part of the current refactor and must not be implemented as placeholder/gateway/empty service.

## Component Statuses

Evidence-based; states per `docs/STATUS_MATRIX.md`.

| Component                    | Status     | Implemented                                                                                                                                           | Gap                                                                                               |
| ---------------------------- | ---------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| M1 Bootstrap                 | TESTED     | ApplicationContainer composition root, explicit wiring, best-effort shutdown (first-error-wins), pytest + Ruff + build in CI                          | —                                                                                                 |
| M2 Minimal Playback          | TESTED     | Single-file play/stop via `QtMultimediaBackend` behind `AudioPort`                                                                                    | —                                                                                                 |
| M3 Complete Playback         | TESTED     | Play/pause/resume/stop, seek, volume, mute, position/duration events                                                                                  | No Required-1.0 gap; gapless/crossfade Post-1.0; metadata owned by M6                             |
| M4 Queue                     | PARTIAL    | Add/remove/clear, play_index, next/previous, auto-advance                                                                                             | Shuffle, repeat absent (Required 1.0); reorder Post-1.0                                           |
| M5 Database/Settings         | TESTED     | Settings persistence (SQLite, WAL) through `SettingsRepository`/`SQLiteSettingsRepository`; restart gate                                              | No Required-1.0 gap; corruption recovery tracked under M11.2; queue/position persistence Post-1.0 |
| M6 Library                   | PARTIAL    | Recursive scan with extension filter; substring filter; filesystem degradation diagnostics (TD-013, RESOLVED/TESTED)                                  | Metadata extraction absent (Required 1.0, owned by M6); library index DB Post-1.0                 |
| M7 Search                    | FUNCTIONAL | Substring search filter over library                                                                                                                  | FTS / indexed search Post-1.0 (not a blocker)                                                     |
| M8 Navigation                | TESTED     | AppRoute navigation across now_playing/library/queue/settings                                                                                         | —                                                                                                 |
| M9 UI Foundation             | TESTED     | MichiTheme tokens; MichiButton/MichiPanel/MichiSlider/MichiTextField; AppShell/Sidebar/ContentHost; views                                             | —                                                                                                 |
| M10 Settings                 | TESTED     | SettingsService sole owner; volume/muted/last_directory/recent_files persisted; restart gate                                                          | —                                                                                                 |
| M11.1 Failure Contracts      | TESTED     | Runtime failure contracts; no silent exceptions                                                                                                       | —                                                                                                 |
| M11.2A Persistence Detection | TESTED     | Read-only `inspect_path`; taxonomy MISSING/HEALTHY/CORRUPT_DATABASE/MALFORMED_DATA/LOCKED/ACCESS_FAILURE/IO_FAILURE/UNKNOWN_FAILURE                   | —                                                                                                 |
| M11.2B LKG Backup/Recovery   | TESTED     | Last-known-good backup (`<db>.lkg`) + non-destructive recovery staging with exclusive destination reservation (primitives consumed by M11.2E automatic recovery)    |
| M11.2C Field-Level Recovery  | TESTED     | Malformed persisted fields fall back to defaults independently with warnings; no writeback; health classification stays strict (safe read fallback)   |
| M11.2D Startup Preflight     | TESTED     | Read-only preflight before any writable open; deterministic health routing; recovery staged (M11.2E installs for recoverable states); backend constructed only after preflight |
| M11.2E Recovery              | TESTED     | Validated automatic restore + quarantine: healthy-LKG-authorized trusted candidate installed atomically after byte-exact quarantine of original artifacts; terminal states non-recovering; LKG preserved; field malformed stays on M11.2C | — (safe mode remains Post-1.0) |

## Future Execution Order

**M11.2A-E persistence recovery — COMPLETE for Required 1.0** (M11.2E validated automatic restore + quarantine TESTED). **TD-013 filesystem degradation — RESOLVED / TESTED.** **TD-016 cancellation-terminal synchronization — RESOLVED / TESTED.** NEXT AUTHORIZED WP: **M4 Repeat**.

1. ~~**TD-016 — Queue/Playback cancellation-terminal synchronization**~~ — DONE (216f5a1).
2. **M4 Repeat** — repeat modes none/one/all.
3. **M4 Shuffle** — deterministic shuffle navigation (shuffle order/remaining pool + navigation history; never `next = random.choice`).
4. **M4 Queue → TESTED closeout**.
5. **M6 Metadata** — real title/artist/album/duration extraction behind a clean port boundary.
6. **M6 Library → TESTED closeout**.
7. **LOCAL-01 Canonical Music Model**.
8. **LOCAL-02 Artwork Pipeline**.
9. **LOCAL-03 Rich Library Views**.
10. **LOCAL-04 PathView** (successor of the retired CoverFlow).
11. **LOCAL-05 Favorites / History**.
12. **LOCAL-06 Playlists**.
13. **LOCAL-07 Mix Local**.
14. **LOCAL-08 Premium Player UI Completion**.
15. **M12 Performance** — benchmark and tune scan/startup/memory; CI performance gate; resolves TD-009 (async/incremental scan with progress in LibraryState), TD-004 (markdown link validation), TD-012 (coverage tooling).
16. **M13 Packaging** — Linux installable artifacts (AppImage/Flatpak/deb), icon suite, desktop integration, CLI entry points. Windows and macOS are Post-1.0 per the canonical contract.
17. **M14 Beta** — beta channel, opt-in telemetry, feedback loop, triage SLA.
18. **M15 Release Candidate** — zero P0/P1, full docs, migration guide, signed RC artifacts.
19. **M16 Michi Music Player 1.0 Stable** — public stable release, project FROZEN.

LOCAL-01 through LOCAL-08 are the Local Player Completion work packages: after M6, the local product experience (canonical music model, artwork, albums/artists/genres/folders, PathView, favorites, history, playlists, local mix, final player UI) is developed BEFORE Beta — M6 closure does not jump directly to M12.

Required-for-1.0 gaps (shuffle, repeat, metadata extraction) are scheduled as work packages within this order before M12; they are part of the 1.0 contract and may not slip past M15.

## Gate

No phase proceeds to release without its status reaching the state required by its phase contract in `docs/DEFINITION_OF_DONE.md` and `docs/STATUS_MATRIX.md`, and the P0/P1 gate in `docs/INVARIANTS.md` must hold (P0 = 0, P1 = 0).
