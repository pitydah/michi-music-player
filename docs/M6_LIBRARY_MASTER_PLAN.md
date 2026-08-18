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
5. **M6.4 Async Library Pipeline** — scan off the UI thread; `scan_status` / `generation` / `processed` / `total` / `progress`; cooperative cancellation; supersession — a stale generation never commits. **OWNS TD-009; NOT M12.**
6. **M6.5 Artwork Pipeline v2** — front-cover preference; `cover.*` / `folder.*` / `front.*` local fallbacks; digest-aware cache invalidation; no premium processing.
7. **M6.6 Canonical Library Projections** — one canonical album model for the six views; `selectedAlbumId` survives view switches; bridge audit — musical rules move down.
8. **M6.7 Library Presentation Architecture** — LibraryView decomposition per the target tree; Loader/Host; preserve objectNames or migrate explicitly; structural tests.
9. **M6.8 Golden / Scale / Closeout** — golden dataset; golden restart / incremental / async / six-views runs; 10k-scale baseline; error/degradation contract; closeout gate §69 of the original M6 contract.

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
4. **Scale baseline evidenced** — 10k-file scan baseline recorded (time, memory, determinism).
5. **Error/degradation contract honored** — typed diagnostics; stale generations never commit; no silent failures.
6. **Bridge audit clean** — no musical rule lives in the bridge; QML is projection-only.
7. **Contract complete** — the ORIGINAL M6 contract is declared complete, not a reduced subset.

## 7. Final State Definition

M6 is CLOSED / TESTED / FROZEN when the §6 closeout gate passes. **ORIGINAL CONTRACT COMPLETE.** The next phase is **M7 — SEARCH**, entered explicitly and intentionally, NOT automatically.

Status: **M6.0 — OPEN / IN PROGRESS** (baseline `9c02e640`).
