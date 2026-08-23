# Status Matrix

Governance authority for component and work-package state. It owns only the two exact state sets and their transition semantics.

No state labels or transitions exist beyond those defined below.

## Component State Machine

Components track implementation health through a staged lifecycle. Each component carries exactly one state at all times.

### States

| State      | Meaning                                                                          |
| ---------- | -------------------------------------------------------------------------------- |
| UNKNOWN    | Not yet audited; no evidence collected                                           |
| AUDITED    | Evidence collected; state and risks are documented                               |
| BROKEN     | Known defects prevent basic function                                             |
| PARTIAL    | Subset of responsibilities is functional; known gaps remain                      |
| FUNCTIONAL | All responsibilities verified as working                                         |
| TESTED     | Automated test coverage exists for all responsibilities                          |
| STABLE     | No regressions across multiple release cycles                                    |
| FROZEN     | Design closed; no further changes permitted without approved reopening exception |

### Normal Progression

```
UNKNOWN → AUDITED → FUNCTIONAL → TESTED → STABLE → FROZEN
```

### Exceptional States

- **BROKEN**: component has known defects that prevent basic function. Recovery path is `BROKEN → FUNCTIONAL` only — a BROKEN component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.
- **PARTIAL**: subset of responsibilities is functional; known gaps remain. Recovery path is `PARTIAL → FUNCTIONAL` only — a PARTIAL component MUST NOT skip to TESTED or STABLE without passing FUNCTIONAL first.

Recovery from BROKEN or PARTIAL requires: (a) remediation passes all functional criteria, (b) evidence is recorded, and (c) the transition is explicitly reviewed.

### Evidence Required per Transition

| Transition           | Evidence                                                                                       |
| -------------------- | ---------------------------------------------------------------------------------------------- |
| UNKNOWN → AUDITED    | Audit report: current state, known risks, dependencies                                         |
| AUDITED → FUNCTIONAL | Functional criteria met; manual or automated verification                                      |
| FUNCTIONAL → TESTED  | Automated test suite passes (see Evidence-Based Definition of TESTED in DEFINITION_OF_DONE.md) |
| TESTED → STABLE      | No regressions across ≥2 release cycles                                                        |
| STABLE → FROZEN      | Approved freeze decision; no open P0/P1                                                        |
| BROKEN → FUNCTIONAL  | Remediation passes; all functional criteria re-verified                                        |
| PARTIAL → FUNCTIONAL | Remaining gaps closed; all responsibilities verified                                           |

## Work-Package State Machine

Work packages (WPs) track deliverable progress through the SDD pipeline. Each WP carries exactly one state and, when BLOCKED, records its prior state for correct resumption.

### States

| State       | Meaning                                            |
| ----------- | -------------------------------------------------- |
| BACKLOG     | Captured but not yet ready for execution           |
| READY       | Admitted for execution by the readiness authority  |
| IN_PROGRESS | Active development                                 |
| REVIEW      | Under review (code, design, or architecture)       |
| VERIFY      | Acceptance criteria being verified                 |
| BLOCKED     | Cannot proceed; prior state recorded               |
| DONE        | Accepted by the completion authority and delivered |
| DEFERRED    | Intentionally postponed with rationale             |

### Normal Flow

```
BACKLOG → READY → IN_PROGRESS → REVIEW → VERIFY → DONE
```

### Blocking Rules

READY, IN_PROGRESS, REVIEW, and VERIFY MAY enter BLOCKED when a dependency or obstacle prevents progress. BLOCKED MUST record the immediately prior active state; no other state may enter BLOCKED.

Resumption restores the recorded prior state:

Each route below is a suspension and restoration path, not a fresh progression:

- `READY → BLOCKED` resumes as `READY`
- `IN_PROGRESS → BLOCKED` resumes as `IN_PROGRESS`
- `REVIEW → BLOCKED` resumes as `REVIEW`
- `VERIFY → BLOCKED` resumes as `VERIFY`

### Deferral Rules

Only these states MAY enter DEFERRED, each with a recorded rationale:

- `BACKLOG → DEFERRED`
- `READY → DEFERRED`
- `BLOCKED → DEFERRED`

`DEFERRED → BACKLOG` SHALL occur only after an approved scope change. Otherwise the item remains DEFERRED or is permanently retired.
These rules are exhaustive for work-package interruption and deferral.

## Current Capability Matrix

Snapshot of the rebuild's components against the component state machine. Evidence: pytest suite (460 passing, snapshot 2026-08-16), Ruff clean, CI green. The count is a dated snapshot; authoritative evidence is the passing full suite in CI. The matrix is a report, not a new state set; the state machine above is authoritative and unchanged.

**Active-contract rule**: the matrix reports only components of the active 1.0 contract on the current stack. Every state below MUST be a legal state from the component state machine above — no invented labels. Superseded clean-rebuild governance draft components (the C++20-anticipation milestones) are not reported. A contract component that has not started is UNKNOWN (not yet audited), never a custom label.

**Post-1.0 rule**: a component is PARTIAL only when at least one responsibility REQUIRED by the active 1.0 release contract remains incomplete. Post-1.0 responsibilities (deferred context) are NOT gaps preventing FUNCTIONAL/TESTED and MUST NOT be listed as blockers.

| Component                    | State      | Notes                                                                                                                                                    |
| ---------------------------- | ---------- | -------------------------------------------------------------------------------------------------------------------------------------------------------- |
| M1 Bootstrap                 | TESTED     | Composition root, explicit wiring, best-effort shutdown (first-error-wins)                                                                               |
| M2 Minimal Playback          | TESTED     | Single-file playback via QtMultimediaBackend behind AudioPort                                                                                            |
| M3 Complete Playback         | TESTED     | Play/pause/resume/stop, seek, volume, mute, position/duration events all tested; metadata extraction owned by M6 Library | M3 ORIGINAL CONTRACT TESTED / CLOSED — no M3 gap. Gapless is a NEW Required-1.0 capability owned exclusively by M11.5; crossfade Post-1.0 |
| M4 Queue                     | TESTED     | Queue basics, TD-015 pending identity, TD-016 cancellation terminal, repeat modes (none/one/all) and deterministic shuffle navigation — all TESTED (a977378, f93a6a8; 441-pass suite). ORIGINAL CONTRACT CLOSED: reorder (move) implemented (a52ce27); navigation truthful (has_next/has_previous service-level); empty-queue semantics deterministic; max-tracks capacity (QueueCapacityError). |
| M5 Database/Settings         | TESTED     | M5 ORIGINAL CONTRACT CLOSED: schema versioning (CURRENT_SCHEMA_VERSION=1, settings row schema_version) + migration framework v0→v1 (idempotent, transactional rollback, fail-closed on newer schema) + session snapshot (JSON session_snapshot row, strict decode, fresh-on-malformed) + queue restore (restore_session, capacity guard, duplicates preserved) + non-autoplay resume (prepare_for_resume, coherence rule, no fabricated current) + runtime checkpoints (PersistenceCoordinator, 5000ms position throttle) + theme/window geometry persistence + LKG integration (full-row comparison includes all new rows). M5-FINAL-CORRECTION: restore is guarded (no self-overwrite of the resume snapshot); volume/mute persist at runtime (no shutdown dependency); coordinator lifecycle explicit (start/stop/shutdown, freeze + unsubscribe, idempotent); durable position marker advances only on successful save (retry on failure, no crash). M5-LAST-GATE-2: two-phase resume confirmation (media acceptance ≠ position confirmed — the restored playback authority holds until the backend confirms a position, clamp tolerated, position 0 valid); queue mutations during the resume window persist via hybrid snapshots (live queue + restored playback truth); coherence-break/remove-current/rejection/supersession release the restore authority. M5-PRODUCTION-LIFECYCLE-GATE (65facc3): production lifecycle start→restore verified identical to tests; reentrant seek confirmation (arm-before-seek, unchanged-position, seek-failure disarm, zero-position via backend-reported position); queue-coherence-aware durable encode (no resurrected playback identity); sqlite connections closed explicitly (no GC dependence).|
| M6 Library                   | TESTED     | M6 ORIGINAL CONTRACT CLOSED + PRODUCTION COMPOSITION VERIFIED + CROSS-PERSISTENCE VERIFIED + AUTHORITATIVE DATA DECODE VERIFIED (M6.0-M6.8 per docs/M6_LIBRARY_MASTER_PLAN.md §8-§9): canonical model v2, persistent versioned index, incremental engine (no reparse of unchanged), async pipeline (supersession/cancellation/progress; TD-009 owned), artwork v2 (front/local/digest cache), canonical projections (six views one model, key-based selection), modular presentation (TD-017 resolved), golden+scale gates (beff4a0 + 01fe2ec). PRODUCTION INTEGRATION CORRECTION (39f0f3b..a3772bb): index/prefs/playlists wired in the production graph (bootstrap._build_services shared with tests), token per generation, worker never writes durable state (apply_delta after the generation gate), owner-thread dispatcher (QueuedConnection), shutdown lifecycle, album year deterministic, artist album_count canonical, artwork pruning + two-pass front, albumMode preserved, scan progress/cancel vertical, TrackRef technical carrier + facts-only quality labels, Michi fallback RECLASSIFIED to M9, scale memory claim corrected to M12. 26 production-composition gates green (test_m6_production_composition.py). CROSS-PERSISTENCE GATE (a3772bb..FINAL HEAD): provenance = authoritative logical state (settings + library_prefs via centralized _AUTHORITATIVE_TABLES; pre-M6 absence == empty; cache divergence never invalidates), LKG full-database snapshot verified, M6 user data (favorites/history/recently-added/playlists) restored verbatim through recovery and loaded by the production graph, index preserved/rebuildable across recovery, album technical summary honesty (EXACT/MIXED/PARTIAL/UNKNOWN — known+unknown never definitive), immutable ScanProgressSnapshot at the thread boundary. 26 cross-persistence gates green (test_persistence_cross_context.py). AUTHORITATIVE DECODE GATE (449bbdd..FINAL HEAD): strict string-list decoders (LOAD NEVER RAISES, no fabrication, no partial salvage), strict playlist root/entry validation (valid siblings preserved), explicit required-vs-optional authoritative tables (settings required fail-closed; library_prefs optional pre-M6), malformed-data production goldens (graph builds safely, no fabricated user state, recovery-safe). 53 decode gates green (test_persistence_authoritative_decode.py). |
| M7 Search                   | TESTED      | RICH CANONICAL LOCAL SEARCH CLOSED (M7.0-M7.7 per docs/M7_SEARCH_MASTER_PLAN.md): canonical in-memory search over the M6 model — SearchQuery raw-preserved + normalized (accent/case-insensitive, multi-token AND across fields), fields title/artist/album/album_artist/genre/composer/display_name, match types EXACT/PREFIX/TOKEN_PREFIX/SUBSTRING, deterministic relevance (input-order independent), entity results (tracks/albums/artists/genres/composers), unified SearchProjection filtering Songs/Albums/Artists/Genres/Favorites/History/Recently-Added, six album views on ONE filtered canonical model, selection canonical-safe, active search rebuilt on structural changes, clear restores canonical exactly; FTS POST-1.0; AI/vector/network NOT involved; no persistence; no filesystem/Mutagen access; 10k correctness+determinism scale baseline. 93 M7 gates green. CANONICAL-SEMANTICS CORRECTION (re-close): track album_artist = M6 resolve_album_artist (single source; compilations searchable as Various Artists consistently across track+album results), album entity ranking title-first (dedicated AlbumSearchDocument bands; exact title > exact album artist), track tie-break honors sort_title before track id, bridge composers Property exposed, six-view invariant verified on AlbumIds. 24 re-close gates green (test_search_canonical_semantics.py) |
| M8 Navigation                | TESTED     | AppRoute navigation across now_playing/library/queue/settings + PLAYLISTS (M8-R1, DONE): playlist target semantics, delete-selected convergence, rename keeps target. REFROZEN after M8-R1 |
| M9 UI Foundation             | TESTED     | Tokens + primitives + shell; QML smoke tests                                                                                                             |
| M9 Premium Presentation System | FROZEN    | CLOSED / TESTED / FROZEN baseline delivered by PR #204 (merged 87c534e): Michi UI Design Canon 2.0 (Aurora/Obsidian semantic design system, smoked-glass control surfaces, desktop interaction system), canonical application shell (Sidebar, floating content islands, global search overlay), six canonical Library album views (Grid/PathView/Vinyl Wall/Timeline/Magazine/List), Album/Artist UX (responsive album detail, technical inspector, canonical artist detail), Search UX consuming M7, contextual Queue, canonical persistent NowPlayingBar (golden-pinned 1920×154), Artwork Focus Mode, Library Density, Precision Mode, keyboard/focus/accessibility, reduced motion, capability gating, visual/material refinements through the final premium passes at PR head 4415843. Accepted by the product owner to continue the roadmap; evidence: Michi CI #2158 success on merge 87c534e (1245 passed, lint/Qt-QML/build green). Per `docs/M9_PREMIUM_PRESENTATION_SYSTEM.md`. |
| M10 Settings                 | TESTED     | Persistence + restart gate verified                                                                                                                      |
| M11.1 Failure Contracts      | TESTED     | Runtime failure contracts verified                                                                                                                       |
| M11.2A Persistence Detection | TESTED     | Read-only health taxonomy verified; consumed by the M11.2D startup preflight (TESTED)                                                                      |
| M11.2B LKG Backup/Recovery   | TESTED     | Last-known-good backup (`<db>.lkg`) + non-destructive recovery staging verified (primitives consumed by M11.2E automatic recovery)                                     |
| M11.2C Field-Level Recovery  | TESTED     | Per-field malformed-data fallback with warnings (safe read fallback, no writeback); health classification remains strict (MALFORMED_DATA)                |
| M11.2D Startup Preflight     | TESTED     | Read-only preflight before any writable open; deterministic health routing; staged candidates are installed by M11.2E only after validation for recoverable states                    |
| M11.2E Recovery              | TESTED     | Validated automatic restore + quarantine: healthy-LKG-authorized trusted candidate installed atomically after byte-exact quarantine evidence; terminal states non-recovering; LKG preserved; field malformed stays on M11.2C. LKG committed WAL-visible state preserved; LKG sidecars are never recovery cleanup targets. |
| M11.3 Multi-Engine Audio Runtime | AUDITED | IN PROGRESS — foundations DONE / TESTED / FROZEN: A (engine contracts + ADR 0007), A-R1, B (Qt Multimedia PRODUCTIVE reference engine through the AudioTransportRouter — transactional startup, first-error-wins, six-callback contract), B-R1, B-R2 (integrity seal), C (GStreamer AudioPort adapter — playbin3, lazy GI, generation provenance, truthful probe), C-R1 (real runtime convergence), C-R2 (runtime truth seal), C-R3 (failure-atomicity seal), C-R4 (bus watch lifecycle seal), C-R5 (terminal cleanup seal), C-R5.1 (cleanup exception-boundary seal), C-R6 (transport lifecycle & arm transaction seal), C-R6.1 (resource ownership & load-disposition convergence seal — AudioLoadError contract), C-R6.2 (terminal runtime truth seal — real playback-state authority, two-phase load disposition), C-R6.3 (post-play-failure backend ownership seal — pending candidate terminal in backend, late-event generation isolation), C-R6.4 (state-change failure return convergence seal — PLAYING FAILURE return is terminal for pending candidates), C-R6.5 (owner-thread generation commit seal — pump observes, owner commits, queued provenance), C-R6.5.1 (owner-to-subscriber atomic publication seal — one async boundary, direct owner callbacks). Outstanding: D (MPD adapter), E (availability runtime), F (selection/persistence), G (failure convergence). Work package M11.3 — IN PROGRESS |
| M11.4 Audiophile Output & DAC | AUDITED | Not implemented. Evidence collected (RESEARCH-01 — DAC_DEVICE_REFERENCE_AUDIT.md + AUDIOPHILE_FEATURE_MATRIX.md: stable identity, capability probing, profiles, DSD/DoP, volume, rate switching, hotplug); state/risks documented in docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md (multi-backend deduplication rule, four-stage bit-perfect evidence model). Work package M11.4 — READY. |
| M11.5 Audiophile Guarantees  | AUDITED    | Not implemented. Evidence collected (RESEARCH-01 — BIT_PERFECT_CONTRACT_PROPOSAL.md: bit-perfect contract, gapless ownership, cross-format degradation); state/risks documented in docs/M11_5_AUDIOPHILE_PLAYBACK_GUARANTEES.md (post-decode signal comparison; M6 metadata = file facts, decoder/engine = runtime truth). Work package M11.5 — READY. |

Transitions pending per the canonical 1.0 contract: all components with outstanding Required-1.0 gaps must reach TESTED before M15. M6 is TESTED / ORIGINAL CONTRACT CLOSED (M6.0-M6.8, beff4a0/01fe2ec); M7 SEARCH is TESTED / CLOSED / FROZEN (canonical local search, M6 shared album-artist semantics, title-first album ranking, five entity result sets, six-view same-AlbumIds invariant, 10k correctness baseline, FTS Post-1.0 — per docs/M7_SEARCH_MASTER_PLAN.md); M9 PREMIUM PRESENTATION SYSTEM is CLOSED / TESTED / FROZEN (PR #204 merged 87c534e; Michi CI #2158 success on the merge head — per docs/M9_PREMIUM_PRESENTATION_SYSTEM.md); M11.2A-E persistence recovery is COMPLETE for Required 1.0; TD-016 (Queue/Playback cancellation-terminal synchronization) is RESOLVED; LOCAL-01 through LOCAL-06 and LOCAL-META-02 are DONE. MICHI-RESEARCH-01 is CLOSED / ACCEPTED (playlists + multi-engine + audiophile reference study, external workspace; per docs/RESEARCH_01_AUDIO_PLAYLISTS_FINDINGS.md). Playlists first-class navigation, multi-engine audio (Qt+GStreamer+MPD), audiophile output/DAC management, and same-format gapless are Required-1.0 per the 2026-08-21 product-owner realignment. M8-R1 — Playlists First-Class Navigation is DONE (stable playlist_id, V1→V2 migration, pinned/recent, PLAYLISTS route, identity-driven bridges; 9f0aa0e..cc7422f, suite 1324 passed) and M8 Navigation is TESTED / REFROZEN. M8-R1F — Playlist Navigation Convergence is DONE (coordinator open intent, idempotent recent, startup reconciliation, search playlistId; d3d91eb.., suite 1362 passed) — M8 Navigation remains TESTED / REFROZEN. M9-R1 — Playlists Sidebar / Presentation is DONE (first-class Shell playlists: Sidebar section, All Playlists, Detail, create flow, search convergence, PlaylistsBridge; a87f651..96dd57c, suite 1406 passed) plus M9-R1I production convergence (b6b8311..6249cb8, suite 1437 passed: single navigation truth, one production bridge, dialog determinism, accessibility) and M9 Premium Presentation System is REFROZEN (scoped reopening closed). M11.3 overall remains IN PROGRESS (component AUDITED; M11.3C DONE / TESTED / FROZEN through R6.5.1; D–G outstanding). The approved next WP is M11.3D — MPD Adapter per `MASTER_ROADMAP_1.0.md`.

## Work-Package Statuses (active 1.0 contract)

Work packages use the work-package state machine above (BACKLOG → READY → … → DONE) and are distinct from component states. All realignment WPs were admitted for execution by the product owner on 2026-08-21 (readiness authority) in the canonical order of `MASTER_ROADMAP_1.0.md` — READY means admitted, not started.

| Work package                     | State      | Notes |
| -------------------------------- | ---------- | ----- |
| M8-R1 Playlists First-Class Navigation | DONE | Delivered 2026-08-21 (9f0aa0e..cc7422f): stable opaque `playlist_id` (UUID4; deterministic UUIDv5 legacy migration, no writeback on load, duplicate first-wins), identity-based PlaylistService CRUD, pinned/recent navigation metadata (MRU bounded 5, id-based, delete prunes), `AppRoute.PLAYLISTS` + playlist target semantics (rename keeps target, delete-selected converges to All Playlists), identity-driven bridges (`playlistId`/`selectedPlaylistId`/pinned/recentRank), minimal ContentHost route plumbing. Full suite 1324 passed; ruff/build green. Queue/Playlist separation preserved; M6/M7 untouched; M9 visual baseline unchanged. Component counterpart: M8 Navigation — TESTED / REFROZEN. |
| M8-R1F Playlist Navigation Convergence | DONE | Convergence gate delivered 2026-08-21 (d3d91eb.., suite 1362 passed): `PlaylistNavigationCoordinator` (application seam — validate → mark recent → navigate; invalid/empty/whitespace ids fall back to All Playlists, never dangling), `mark_recent` idempotent (MRU rank 0 = no persist/notify), startup pinned/recent SAFE-READ normalization (stale pruned, duplicates first-wins, recent bounded, no load writeback), `searchPlaylists` rows expose canonical `playlistId`, bridge delete-selection converges to empty, delete/recreate same name → new identity with no inherited pinned/recent/navigation state. Product open intent is canonical; raw `navigate_to_playlist` slot DEPRECATED (tests/compat only). M8 Navigation remains TESTED / REFROZEN. |
| M9-R1 Playlists Sidebar / Presentation | DONE | Delivered 2026-08-21 (a87f651..96dd57c) + M9-R1I production convergence (b6b8311..6249cb8): Playlists is a FIRST-CLASS SHELL feature — dedicated PLAYLISTS section in Sidebar (All Playlists, bounded pinned/recent quick access, New Playlist), All Playlists workspace (responsive card grid, empty state, pin/open/play/rename/delete), Playlist Detail (header, track list with remove/reorder, rename, delete confirmation — "Music files will remain in your library"), PlaylistCreateDialog (create → open workflow), search results open the first-class route via `open_playlist` (validated + Recent), Library Add-to-Playlist by canonical id. Dedicated `PlaylistsBridge` owns the canonical playlist presentation projection; `LibraryBridge` no longer exposes `selectedPlaylistId`/`playlistTracks`; the old Library Playlists tab and `views/PlaylistsView.qml` are REMOVED; raw `navigate_to_playlist` QML slot SEALED. M9-R1I single-navigation-truth: NavigationState.playlist_id is the ONE detail authority (PlaylistsBridge projection-only), one production bridge with explicit lifecycle, search keyboard parity, deterministic create/rename dialogs, card accessibility hardened. Suite 1437 passed; ruff/build/QML smoke green. M9-R1J interaction & search reactivity seal (6ee9e12..7d78fab, suite 1449 passed): shared-dialog Detail actions, reactive playlist search (LibraryService observation), combinedResultCount overlay aggregation, card focus hardening, dynamic QML interaction gates. Component counterpart: M9 Premium Presentation System — REFROZEN. |
| M11.3 Multi-Engine Audio Runtime | IN PROGRESS | M11.3A + M11.3A-R1 + M11.3B + M11.3B-R1 + M11.3B-R2 + M11.3C (GStreamer adapter DONE/TESTED/FROZEN 2026-08-22) DONE. M11.3A DONE/TESTED/FROZEN + M11.3A-R1 DONE (2026-08-22: activation semantics can_activate/activation_blocker, lifecycle UNINITIALIZED, Qt provider lifecycle ownership, AudioPort transport-only sealed). Router PRODUCTIVELY WIRED since M11.3B; Qt PRODUCTIVE REFERENCE ENGINE. M11.3B-R2 final integrity seal (first-error-wins cleanup, all six callbacks verified, coordinator same-router identity). M11.3A impl: domain contracts (AudioEngineId/Lifecycle/Descriptor/State), AudioTransportRouter stable identity + AudioTransportBindingPort, registry + provider ports, AudioEngineService (sole AudioEngineState), Qt provider reference, GStreamer/MPD availability probes (installed != implemented), ADR 0007 (GStreamer PyGObject/GI lazy; MPD in-repo minimal protocol; MPD private managed only). AudioPort stays transport-only; quiescent switching M11.3F; DAC/output config in separate ports (M11.4). |
| M11.4 Audiophile Output & DAC Management | READY | AudioDeviceRegistry with multi-backend deduplication/provenance; stable identity; capability probing; per-DAC profiles; Shared/Direct; PCM/DSD/DoP; volume; rate switching; hotplug. |
| M9-R2 Audio Output UX           | READY | Controlled M9 reopening (pre-authorized); engine/DAC/profile selectors, Signal Path telemetry, BitPerfectState; NowPlayingBar geometry protected. |
| M11.5 Audiophile Playback Guarantees | READY | Bit-perfect conformance (signal-level, post-decode), same-format gapless, honest cross-format degradation, DSD/DoP transitions, parity, convergence, failure injection. |

Reopening note: M8-R1/M9-R1/M9-R2 reopen their component counterparts under the M9 Freeze Policy (scoped, with REOPEN REASON / SCOPE / TRIGGERING MILESTONE / AFFECTED COMPONENTS / NON-GOALS / TEST-ACCEPTANCE GATES / REFREEZE CONDITION); after their gates pass, the component returns to FROZEN.
