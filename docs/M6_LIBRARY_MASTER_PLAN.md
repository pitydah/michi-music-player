# M6 — LIBRARY: ORIGINAL CONTRACT RECONCILIATION — OPERATIONAL MASTER PLAN

Baseline: `9c02e640af7d18add3f8d945146df6be4e8e7054` (HEAD at M6.0 open). M5: CLOSED / TESTED / FROZEN. This document is the SINGLE operational reference for M6 execution — the authoritative phase sequence, the reconciliation result of the original M6 contract, and the closeout contract. It supersedes all earlier M6 execution-plan language in the governance docs.

## 1. Contract Principle

M6 makes Library a **CANONICAL / PERSISTENT / INCREMENTAL / ASYNC / DETERMINISTIC / MODULAR / SCALABLE** musical subsystem. QML is a projection of musical truth, never a source of it.

Conceptual pipeline:

```
Filesystem
   → Discovery
   → Persistent Index
   → Metadata
   → Canonical Track Model
   → Canonical Music Model
   → Projections
   → Bridge
   → QML
```

Each stage has exactly one owner (domain/service/port/bridge), deterministic output, and no re-derivation of a stage by a layer above it. Musical rules (identity, ordering, grouping, timeline) live in the domain; the bridge only translates; QML only renders.

## 2. Authoritative Execution Order (the ONLY one)

1. **M6.0 Contract Reconciliation** — **DONE (567bbfa)**.
2. **M6.1 Canonical Music Model v2** — **DONE (8694077)**: canonical identity API (make_track_id/make_genre_key/make_composer_key), canonical disc/track ordering (UNKNOWN-last, input-order independent), ComposerRef + MusicModel.composers + LibraryState.composers, Album V2 derived fields (disc_count/genres/composers), timeline projection moved to domain (timeline_decade/build_timeline_projection, bridge adapts only).
3. **M6.2 Persistent Library Index** — **DONE (c26acfd)**: LibraryIndexEntry (track_id + fingerprint size/mtime_ns + full metadata carrier) in domain/library_index.py with the strict deterministic metadata codec (malformed rows skipped+logged, extra keys tolerated); LibraryIndexRepository port (load_all/upsert_many atomic/remove/clear/version, never raises); SqliteLibraryIndexRepository (bounded context: own library_index + library_meta tables, own library_schema_version — the M5 key space is not reused; fail-closed on newer schema; explicit connection close; all-or-nothing batches).
4. **M6.3 Incremental Library Engine** — **DONE (dd701e7)**: pure classify_scan (ADDED/MODIFIED/REMOVED/UNCHANGED by size/mtime_ns fingerprint); LibraryScannerPort.fingerprint; incremental scan with the index wired (extraction ONLY for added/modified, index metadata reused for unchanged — unchanged rescans perform ZERO extractions; the 10k/1-change acceptance gate holds), atomic commit (full derived build before a single assignment + one notify), index upsert/remove, fingerprint errors wrapped like scan errors (preserve + diagnostic); full-scan path unchanged without an index.
5. **M6.4 Async Library Pipeline** — **DONE (0dc2566)**: LibraryScanStatus (IDLE→DISCOVERING→INDEXING→EXTRACTING→COMMITTING→COMPLETED/CANCELLED/FAILED) + scan_generation/processed/total/progress/current_path on LibraryState; ScanPipelinePort (submit/cancel) with cooperative ScanCancelToken/ScanCancelled; LibraryService.start_scan (async; sync fallback without a pipeline never arms the scan-state) + cancel_scan + _on_scan_progress/_on_scan_done (generation guard first — a stale generation NEVER commits); ScanResult payload with directory; ThreadScanRunner + ScanRelay (Qt dispatch only in infrastructure — the service stays Qt-free); the bridge scan slot delegates to start_scan; TD-009 owned here (NOT M12).
6. **M6.5 Artwork Pipeline v2** — **DONE (0736534)**: front-cover preference (APIC/Picture type 3, fallback to the first frame only without a front designation); deterministic local fallback (cover.*/folder.*/front.*, case-insensitive, unreadable skipped, no arbitrary scanning); content-digest-aware cache key (sha256(album_key + sha256(data))) — changed artwork becomes active on rescan, unchanged content keeps the same path idempotently, old entries stay (stale-aware, no eager deletion); resolution order in enrichment: embedded front → local → none; no premium processing.
7. **M6.6 Canonical Library Projections** — **DONE (44b1471)**: the six views consume ONE canonical album model (library.albums + the timeline's canonical domain projection; no view-specific album models anywhere — structural pins); selection identity is the canonical album key (selectedAlbumKey): view switches preserve it (albumMode is purely local QML state) and album deletion clears the detail safely; albumTracks rows gain trackNumber/discNumber following the M6.1 canonical ordering; the bridge adapts build_timeline_projection exactly (only hasArtwork/artworkPath added).
8. **M6.7 Library Presentation Architecture** — **DONE (b9b243b)**: LibraryView.qml decomposed (1147-line monolith → 30-line orchestration + 20 components: LibraryHeader/LibraryToolbar (scanStatusText)/LibraryTabs/LibraryContentHost (Loader on-demand with synchronous objectName-clear unload)/SongsView/AlbumsView (albumMode host + mode Loader + persistent AlbumDetailView)/the six album projections/AlbumDetailView/ArtistsView/GenresView/FoldersView/FavoritesView/HistoryView/RecentlyAddedView/PlaylistsView); objectNames preserved + migrated (tests activate tab/mode before findChild — documented); bridge scanStatus projection; only the active tab/mode instantiated (no six heavy trees alive); TD-017 resolved.
9. **M6.8 Golden / Scale / Closeout** — **DONE (beff4a0 + 01fe2ec)**: REAL-pipeline golden dataset (29 tracks: single/multi-disc, compilation Various Artists, explicit/missing album_artist, composer, untagged, same-title-different-artists, artist case variations, duplicate titles, unknown numbers, different years, MP3+FLAC, embedded/folder/no/modified artwork) + golden restart (unchanged restart: ZERO extractions), golden incremental (+A/−B/modify C: extraction only for the changed), golden async (gen 101 supersedes 100 — late gen 100 never commits), golden six views (selectedAlbumId without drift), golden degradation (broken artwork/malformed file/missing file+dir preserve the library) + 10k synthetic scale baseline (index 10k rows, unchanged rescan ZERO extractions, coherent model, deterministic).

Execution SHALL follow this order. A phase does not start before its predecessor reaches its contract state.

## 3. Reclassification (the old parallel tracks are absorbed)

| Old track | Disposition |
| --------- | ----------- |
| LOCAL-MODEL-02 | → **M6.1** (Canonical Music Model v2) |
| M12A Async Library Pipeline | → **M6.4** (Async Library Pipeline) |
| LOCAL-ART-02B | → **M6.5** (Artwork Pipeline v2) |
| LOCAL-LIBRARY-02 | → **M6.6** (Canonical Library Projections) + **M6.7** (Library Presentation Architecture) |
| The previous mega-WP (LOCAL-01..08 as an execution sequence) | **STATUS: SUPERSEDED AS EXECUTION PLAN; USE REQUIREMENTS SOURCE.** |

The completed LOCAL work packages (LOCAL-01..06, LOCAL-META-02, LOCAL-STABILIZATION-01) remain DONE and are absorbed as completed contract scope of M6.

## 4. Reconciliation Matrix (M6.0 audit result)

The M6.0 audit reconciled the original M6 contract against the delivered surface (31 findings). Classifications: `DONE` / `PARTIAL` / `TODO` / `MOVED_TO_M7` (rich search) / `MOVED_TO_M9` (visual premium) / `MOVED_TO_M12` (profiling/optimization) / `OBSOLETE`.

| # | Item | Classification | Evidence pointer |
| - | ---- | -------------- | ---------------- |
| 1 | Recursive scan with extension filter | DONE | `LibraryScannerPort` / `FilesystemLibraryScanner` |
| 2 | Canonical basic metadata (title/artist/album/duration, Mutagen, per-file fallbacks, failure-safe) | DONE | `InfrastructureMetadataExtractor` (5fd8ec3) |
| 3 | Substring search filter | DONE | `LibraryBridge.search` |
| 4 | Filesystem degradation diagnostics | DONE | TD-013 RESOLVED (3a2aec9) |
| 5 | Canonical types + normalized identity keys (AlbumRef/ArtistRef/MusicModel, make_album_key/make_artist_key) | DONE | `domain/library.py` (ba1532d, aaddf30) |
| 6 | LibraryState.albums/artists rebuilt per successful scan + bridge counts | DONE | `LibraryService` (ba1532d) |
| 7 | Embedded artwork extraction + deterministic per-album-key disk cache + has_artwork | DONE | LOCAL-02 (9b16504) |
| 8 | Six canonical views + view modes (Grid/Cover/Vinyl Wall/Timeline/Magazine/List) | DONE | `LibraryView.qml` (e7416ac, a60d4c6) |
| 9 | Album Detail (artwork, track list, activation) | DONE | `LibraryView.qml` (e7416ac) |
| 10 | PathView album carousel (CoverFlow successor) | DONE | LOCAL-04 (635b35b) |
| 11 | Favorites / History / Recently Added | DONE | LOCAL-05 (938191b) |
| 12 | Playlists | DONE | LOCAL-06 (ccdbc85) |
| 13 | LOCAL-STABILIZATION-01 (queue semantics, architecture guard, derived-state, reference persistence) | DONE | deb5f93, 0c1b8c3, 1681c04, e650037, a7f8927 |
| 14 | LOCAL-META-02 rich musical + technical metadata fields | DONE | 08ea531, 3fc0cb3 |
| 15 | Canonical identity keys, compilation-aware grouping, AudioQualityLabel | DONE | aaddf30, 8e8f335 |
| 16 | TrackMetadata field count: 25 fields delivered (contract claimed 26) | PARTIAL | `domain/library.py:12-40` — field-list audit; reconcile the count in M6.1 |
| 17 | AlbumRef.year is first-member semantics (contract ambiguity) | PARTIAL | `domain/library.py:99-109` — pin semantics in M6.1/M6.6 |
| 18 | ArtistRef.album_count counted by title, not by canonical key | PARTIAL | `domain/library.py:260` — fix in M6.1/M6.6 |
| 19 | `_artwork_paths` stale accumulation across rescans (never pruned) | PARTIAL | `LibraryService._artwork_paths` (library_service.py:72/188) — prune in M6.3/M6.5 |
| 20 | Album Detail lacks track/disc number display | PARTIAL | `LibraryView.qml` Album Detail — M6.6 |
| 21 | MusicModel composers absent (no ComposerRef grouping) | TODO → M6.1 | `domain/library.py:141-146` |
| 22 | Timeline derivation lives in the bridge, not the domain | TODO → M6.1 | `LibraryBridge._get_timeline_albums` (library_bridge.py:89) |
| 23 | Search matches display_name only | TODO → M6.6 | `LibraryBridge` visible_tracks filter (library_bridge.py:156) |
| 24 | Canonical Music Model v2 (LOCAL-MODEL-02 absorbed) | TODO → M6.1 | §2.2 |
| 25 | Persistent Library Index | TODO → M6.2 | §2.3 |
| 26 | Incremental Library Engine | TODO → M6.3 | §2.4 |
| 27 | Async Library Pipeline (M12A absorbed; TD-009) | TODO → M6.4 | §2.5 |
| 28 | Artwork Pipeline v2 (LOCAL-ART-02B absorbed) | TODO → M6.5 | §2.6 |
| 29 | Canonical Library Projections (LOCAL-LIBRARY-02 data half absorbed) | TODO → M6.6 | §2.7 |
| 30 | Library Presentation Architecture (LOCAL-LIBRARY-02 QML half absorbed; TD-017) | TODO → M6.7 | §2.8 |
| 31 | Golden / Scale / Closeout | TODO → M6.8 | §2.9 |

Cross-classifications recorded by the M6.0 audit:

| Item | Classification |
| ---- | -------------- |
| Full-text indexed search | MOVED_TO_M7 (rich search) |
| Visual premium presentation (album-wall/premium artwork polish) | MOVED_TO_M9 (visual) |
| Scan/startup/memory profiling + CI performance gate | MOVED_TO_M12 (profiling/optimization — async itself belongs to M6, NOT M12) |
| CoverFlow (Legacy carousel) | OBSOLETE (RETIRED product decision; successor PathView is DONE) |
| Previous mega-WP as an execution plan | OBSOLETE (superseded as execution plan; requirements source only) |

## 5. M6 vs M9 vs M12 Boundary

| Milestone | Owns | Does NOT own |
| --------- | ---- | ------------ |
| M6 | Structure, architecture, behavior of the library subsystem: canonical model, persistence, incrementality, async pipeline, artwork mechanics, projections, QML decomposition | Visual polish/premium presentation; performance tuning |
| M9 | Visual premium (artwork presentation aesthetics, premium visual treatment) | Library structure/behavior; async pipeline |
| M12 | Profiling and optimization (scan/startup/memory benchmarks, CI performance gate, TD-004, TD-012) | Async — the async library pipeline is M6.4 and resolves TD-009 |

## 6. Closeout Contract (§69 checklist of the original M6 contract, condensed)

M6.8 SHALL close M6 only when all of the following hold:

1. **M6.1-M6.7 delivered** — every phase above reached its contract state with tests.
2. **Reconciliation gaps closed** — the PARTIAL/TODO rows of §4 are DONE or explicitly reclassified with approved scope change.
3. **Golden runs green** — restart, incremental, async, and six-views golden scenarios pass on the golden dataset.
4. **Scale baseline evidenced** — 10k-file scan baseline recorded. The M6 scale contract is: **10k correctness + time-bound + determinism** (index 10k rows, unchanged rescan ZERO extractions, coherent model, deterministic). **Memory profiling is MOVED TO M12** (no fake memory claims in M6 docs).
5. **Error/degradation contract honored** — typed diagnostics; stale generations never commit; no silent failures.
6. **Bridge audit clean** — no musical rule lives in the bridge; QML is projection-only.
7. **Contract complete** — the ORIGINAL M6 contract is declared complete, not a reduced subset.

## 7. Final State Definition

**M6 — LIBRARY: STATUS CLOSED / TESTED / FROZEN / PRODUCTION COMPOSITION VERIFIED / CROSS-PERSISTENCE VERIFIED; ORIGINAL CONTRACT COMPLETE + PRODUCTION-INTEGRATION CORRECTION APPLIED + CROSS-PERSISTENCE GATE APPLIED; CANONICAL MUSIC MODEL V2; LIBRARY INDEX PERSISTENT/VERSIONED/INCREMENTAL/REBUILDABLE CACHE + WIRED IN THE PRODUCTION GRAPH; USER LIBRARY STATE DURABLE + RECOVERY-AWARE; SCAN INCREMENTAL/ASYNC/CANCELLABLE/SUPERSESSION-SAFE; ARTWORK V2; PRESENTATION MODULAR; TECHNICAL METADATA CANONICAL + FACTS-ONLY; NEXT PHASE M7 — SEARCH (not automatic).**

Status: **M6 — CLOSED / TESTED / FROZEN / PRODUCTION COMPOSITION VERIFIED / CROSS-PERSISTENCE VERIFIED** (closeout gate passed at `01fe2ec` (CI green); original closeout at `39f0f3b`; production-composition re-close at the a3772bb-series; the M6-FINAL-CROSS-PERSISTENCE-GATE WP re-opened M6 LIMITED to the M6-persistence × M5/M11.2 recovery interaction and re-closed it at the FINAL HEAD — CI green; §6 checklist complete; §8 production-composition checklist complete; §9 cross-persistence checklist complete).

## 8. Production-Integration Correction (M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION)

A limited M6 re-open closed the ONLY weak category of the original closeout: TEST GRAPH == PRODUCTION GRAPH. The rule now enforced by `tests/test_m6_production_composition.py` (26 gates through the REAL bootstrap `_build_services`):

**PRODUCTION COMPOSITION** — `bootstrap._build_services(db_path, ...)` is the single production-graph construction path shared by `ApplicationContainer` and the tests. The production LibraryService is wired with the REAL `SqliteLibraryIndexRepository` (`library_index`), the REAL `SqliteLibraryPrefsRepository` (`library_prefs` — favorites/history/recently_added persist), and the REAL `SqlitePlaylistsRepository` + `PlaylistService` (`LibraryBridge.playlist_service` — playlist slots live). `LibraryPreferencesCoordinator` remains the distinct last_directory contract.

**ASYNC GENERATION SAFETY** — `ThreadScanRunner` keeps ONE `ScanCancelToken` PER GENERATION (a cancelled scan never poisons a later one; `cancel(generation)` targets exactly that generation; unknown generations are safe no-ops). The worker ONLY computes `ScanResult(tracks, upserts, removed)` — durable index mutation happens on the owner thread AFTER the generation gate via a single transactional `apply_delta` (BEGIN/upserts/removes/COMMIT, ROLLBACK on error). A stale generation can never write SQLite nor mutate LibraryState.

**OWNER-THREAD DISPATCH** — `LibraryScanDispatcher(QObject)` (infrastructure) receives the relay signals with EXPLICIT `Qt.QueuedConnection` and delegates to the public `LibraryService.handle_scan_progress/handle_scan_done` on the GUI thread; the service never touches Qt. Tests prove exact thread IDs: heavy work on the worker thread, progress/done/state mutation on the owner thread.

**SHUTDOWN LIFECYCLE** — `ApplicationContainer.shutdown()` order: (1) M5 persistence shutdown first; (2) `scan_runner.shutdown()` (reject new submits + cancel active generations) and `scan_dispatcher.shutdown()` (drop late callbacks) + relay disconnect; (3) playback coordinator; (4) library-preferences coordinator; (5) bridges; (6) backend; (7) QML. A worker finishing after shutdown can neither mutate state nor write the index.

**CANONICAL DETERMINISM** — `AlbumRef.year` = first CANONICAL-sorted member with a known year (0 when none) — input-order-independent (tested under permutation). `ArtistRef.album_count` counts canonical AlbumIds (same title under a different album artist is a different album).

**ARTWORK STATE** — `_artwork_paths` is rebuilt atomically during enrichment (stale entries pruned when albums/art disappear). Album resolution is two-pass: PASS 1 explicit FRONT (APIC/Picture type 3) across ALL tracks; PASS 2 first embedded fallback; PASS 3 local (`cover.*`/`folder.*`/`front.*`); PASS 4 none. **Michi fallback artwork: RECLASSIFIED — deferred to M9** (no canonical asset exists; the original master-prompt chain "... → Michi fallback" is documented as deferred, NOT dropped; M9 owns it).

**PRESENTATION STATE** — `albumMode` lives in `LibraryView` (survives the AlbumsView recreation on tab switches). The bridge exposes `scanProcessed/scanTotal/scanProgress/scanCurrentPath` + a `cancel_scan` slot; `LibraryToolbar` shows status / processed-total / plain progress bar / Cancel (functional, not premium — M9 refines aesthetics).

**TECHNICAL METADATA** — the canonical `TrackRef` retains codec/container/sample_rate_hz/bit_depth/channels/bitrate_bps/file_size (copied in `_trackref_from_metadata`); the album-tracks projection exposes them + a facts-only `qualityLabel` ("FLAC · 24-bit · 96 kHz", "MP3 · 320 kbps" — never "Hi-Res"/"Lossless"); `AlbumRef.technical_summary` is the exact label when every member renders the same one, else "Mixed formats"; AlbumListView shows year/duration/technical summary minimally.

**SCALE CLAIMS CORRECTION** — the M6 scale baseline is **10k correctness + time-bound + determinism**; the previous "time, memory, determinism" claim is corrected: **memory profiling MOVED TO M12**.

Commit record of the correction WP is in `git log` between `39f0f3b` and the FINAL HEAD.

## 9. Cross-Persistence Gate (M6-FINAL-CROSS-PERSISTENCE-GATE)

A final transversal gate closed the M6-persistence × M5/M11.2 recovery
interaction. Verified by `tests/test_persistence_cross_context.py` (26 gates;
the durability ownership policy is also documented in docs/ARCHITECTURE.md
"michi.db Durability Ownership").

**DURABILITY OWNERSHIP** — `settings` (incl. `session_snapshot`) =
AUTHORITATIVE application/session state; `library_prefs` (favorites/history/
recently_added/playlists) = AUTHORITATIVE user library state; `library_index`
= REBUILDABLE CACHE (the filesystem is the authority over file existence);
`library_meta` = CACHE SCHEMA METADATA.

**PROVENANCE** — `_candidate_matches_lkg` now compares the AUTHORITATIVE
logical state (`_AUTHORITATIVE_TABLES` = settings + library_prefs, ordered
rows; single centralized table set), NOT settings-only. Absence semantics:
an ABSENT optional authoritative table (pre-M6 `library_prefs`) is equivalent
to an EMPTY one; a NON-empty table is never equivalent to a missing one.
Rebuildable cache divergence NEVER invalidates provenance — but the LKG is a
FULL-database snapshot (SQLite backup API), so a valid index survives normal
recovery and a missing index is safely rebuilt from the filesystem. Fail
closed: unreadable/mismatched authoritative state rejects the candidate.

**RECOVERY** — after recovery, the PRODUCTION graph (bootstrap._build_services)
loads the restored favorites/history/recently_added/playlists verbatim — no
fabricated user data.

**TECHNICAL SUMMARY HONESTY** — album technical summary policy is structured
(EXACT/MIXED/PARTIAL/UNKNOWN): uniform known tracks report the exact
facts-only label; mixed known tracks report "Mixed formats"; known + unknown
reports "" (NEVER a definitive album-wide claim — UNKNOWN stays UNKNOWN);
all unknown reports "". No marketing labels.

**ASYNC PROGRESS SNAPSHOT** — the thread boundary transports an immutable
`ScanProgressSnapshot` (fresh instance per emission); the mutable builder
stays worker-local; owner-thread delivery, cancellation and supersession
regressions stay green.

**NOT IN SCOPE** — instant index hydration (POST-M6 / M12 startup
improvement); 10k optimization / memory profiling (M12); M9 artwork/visuals;
M7 search.

Commit record: `git log` between `a3772bb` and the FINAL HEAD.
