# M6-EXT — Library Evolution Program: R4–R7 Master Specification (Reconciled)

> Status: **SPECIFICATION** — reconciled against repo HEAD `2cfe45e` (2026-08-29).
> Execution scope of this program: **M6-EXT-R4 only**. R5/R6/R7 are
> specification-only during the R4 run so later work cannot invent
> incompatible designs. **AUDIO LAB IS OUT OF SCOPE.**

## 1. Reconciliation with the actual repository

The original program prompt was written against an older snapshot. The
following deltas were confirmed by direct audit of HEAD `2cfe45e` and are the
authoritative reconciliation.

| Prompt assumption | Actual repo state at `2cfe45e` | Consequence |
| --- | --- | --- |
| `make_track_id(file_path)` is canonical track identity | Confirmed: `domain/library.py:227` returns `str(Path(file_path))`; used by `track_projection.py:24` (`"trackId": make_track_id(ref.file_path)`) | R4-F must quarantine it (legacy-compat only) |
| `TrackRef` drops totals/date/sort fields | Confirmed: `TrackRef` lacks `track_total/disc_total/date/sort_artist/sort_album/sort_album_artist`; `TrackMetadata` has them | R4-E metadata-carrier parity |
| `AlbumRef.track_paths` is album membership | Confirmed: `tuple[Path, ...]` | R4-F: canonical membership → `track_ids`; path projection derived |
| `Playlist.track_paths` is playlist authority (V2) | Confirmed: `domain/playlist.py:72`; V2 JSON `{"id","name","track_paths"}` in `infrastructure/playlists.py` | R4-H: V3 `track_ids` + `fallback_path`; V1/V2 decoders stay |
| Favorites/history/recent are path tuples, best-effort | Confirmed: `LibraryPrefs(favorite_paths/history_paths/recently_added_paths)`; `SqliteLibraryPrefsRepository` never raises (fake durability) | R4-G: `LibraryUserStateRepository` truthful writes; caps `HISTORY_CAP=50`/`RECENT_CAP=50` stay |
| Session snapshot V2 path-only entries | Confirmed: `PersistedQueueEntry{file_path,title}`; `FORMAT_VERSION=2`; strict V1 migration | R4-I: V3 adds `library_track_id`/`fallback_path`; V1/V2 decoders preserved |
| Search `track_id` = path | Confirmed: `domain/search.py:157` `str(self.track.file_path)`; `matched_track_ids` = `frozenset(str(t.file_path))` | R4-F: stable-ID property with `legacy-path::` fallback; ranking unchanged |
| Track sort tie-break by path | Confirmed: `_canonical_track_sort_key` ends `str(track.file_path)` | R4-F: tie-break by `track_id` |
| Destructive TRACK_MISSING removal | Confirmed: `library_service.py:624-625` removes the track from `state.tracks` | R4-L: mark availability, preserve identity |
| Single-directory scan authority | Confirmed: `current_directory` drives scan; `LibraryService.scan(directory)` replaces state | R4-K: multi-source union; `current_directory` → deprecated compat projection |
| Playback `source_id` semantics | Confirmed: `PlaybackSessionState.source_id` = playback context source (album/playlist/queue) — NOT storage | Must never be renamed/reused as `LibrarySourceId` |
| M11.2 recovery authoritative tables | `_AUTHORITATIVE_TABLES = ("settings", "library_prefs")`; `library_prefs` optional | R4-O: catalog + user-state tables join the authoritative set |
| Playback commit event | `PlaybackService` emits path-based committed event | R4-I/J: add richer `subscribe_entry_committed` parallel event |
| Baseline suite | 1 pre-existing failure (`test_m9_r5_1_1_qml_runtime.py::test_empty_icon_removes_its_width_and_spacing_at_runtime`) + 3 Ruff I001 import-order errors (published R5.1.1/R5.2 commits) | R4-Q must remediate the pre-existing baseline defects (separate documented commit) before the freeze gate; not R4 scope creep |

## 2. R4 architecture (authoritative)

### 2.1 Identity model

```
LibrarySourceId  — user-configured storage root (UUID4 new / UUIDv5 legacy)
MediaFileId      — physical audio object (UUID4 new / UUIDv5 legacy)
TrackId          — durable logical music identity (UUID4 new / UUIDv5 legacy)
Path             — current physical location ONLY
```

- New entities: `uuid.uuid4()` once, persisted forever.
- Legacy migration: deterministic `uuid.uuid5(namespace, f"legacy-track::{canonical_path}")`
  with THREE fixed project namespaces (source/media/track). UUID5-from-path is
  migration machinery ONLY — never the future ID algorithm.
- `PlaybackSessionState.source_id` stays PLAYBACK CONTEXT SOURCE. Never
  renamed, never reused as `LibrarySourceId`.

### 2.2 Domain types (`domain/library_catalog.py`)

`SourceLifecycle` (ACTIVE/RETIRED), `SourceAvailability`
(UNKNOWN/AVAILABLE/OFFLINE/MISSING_ROOT/ACCESS_DENIED/IO_ERROR/DISABLED),
`MediaAvailability` (UNKNOWN/AVAILABLE/MISSING/SOURCE_OFFLINE/ACCESS_DENIED/
IO_ERROR), frozen `LibrarySource`, `MediaFileRecord` (media_file_id,
library_source_id|None, relative_path|None, last_known_path, availability),
`TrackRecord` (track_id, media_file_id, created_at_ms). NO musical metadata in
`TrackRecord` — metadata is cache, not identity.

### 2.3 Catalog vs cache (non-negotiable)

| Layer | Contents | Durability |
| --- | --- | --- |
| `LibraryCatalogRepository` (NEW, main DB) | sources, media files, tracks, user state references | AUTHORITATIVE, fail-closed schema, truthful writes |
| `library_index` + metadata cache (existing/evolved) | fingerprints, metadata read cache | REBUILDABLE |
| artwork cache mapping (R4-M) | album_key → cached file | REBUILDABLE |

### 2.4 Catalog schema (main `michi.db`)

`library_catalog_meta(key,value)`; `library_sources(library_source_id PK,
display_name, root_path, enabled CHECK 0/1, lifecycle, created_at_ms,
updated_at_ms)`; `library_media_files(media_file_id PK, library_source_id
NULL FK RESTRICT, relative_path NULL, last_known_path NOT NULL, availability
NOT NULL, created_at_ms, updated_at_ms, UNIQUE(library_source_id,
relative_path))`; `library_tracks(track_id PK, media_file_id NOT NULL FK
RESTRICT, created_at_ms)`. `PRAGMA foreign_keys=ON` per connection. NO
CASCADE on user authority. Fail closed: unknown future version, malformed
version, or missing table in a supposedly-current schema → `LibraryCatalogSchemaError`.

### 2.5 User state tables

`library_favorites(track_id PK FK RESTRICT)`;
`library_history(position INTEGER PK, track_id FK RESTRICT)`;
`library_recently_added(position INTEGER PK, track_id FK RESTRICT)`.
Caps remain 50/50. Recently-Added semantic: ONLY new TrackId allocation
enters it — move/modify/relink/root-relocation/unchanged-rescan do NOT.

### 2.6 Migration (R4-D)

One `LibraryIdentityMigration` owner; ONE `BEGIN IMMEDIATE … COMMIT` covering
catalog + user state + playlist rewrite + session snapshot upgrade; typed
failure → ROLLBACK → retry-safe; idempotent (no-op on current schema; never
rewrites IDs); legacy path → TrackId map built from every path reference
(index, favorites, history, recent, playlists, queue/session snapshot,
playback current path); `last_directory` is a MIGRATION HINT only; no
guessed `commonpath` roots.

### 2.7 Scan (R4-K/L)

Serialized per-source scans; `LibrarySourceScannerPort.discover(source)`;
per-source commit only; source-level availability probe BEFORE enumeration
(offline source ⇒ zero child MISSING rows); fingerprint change ⇒ MODIFIED
(never new identity); same-source move relink only when unique & unambiguous
(device/inode + quick signature bounded evidence); missing file ⇒
`MediaAvailability.MISSING`, identity preserved; pressing Play NEVER deletes
identity.

### 2.8 Startup order (R4-O)

Persistence preflight → recovery/quarantine → library identity schema
discovery → legacy migration → construct repositories/services → load
catalog/user state → cached offline library renderable → async probing.

## 3. R4 work packages (execution order, one reversible commit each)

R4-A Architecture + docs + compatibility audit → R4-B identity domain →
R4-C LibraryCatalogRepository → R4-D transactional migration → R4-E TrackRef
parity → R4-F search/tie-break/projection convergence → R4-G user-state
persistence → R4-H playlist V3 + seam → R4-I queue/session V3 → R4-J
LibraryTrackResolver + playback/history → R4-K source-aware scanner +
multi-source → R4-L offline/missing/relink → R4-M artwork offline cache →
R4-N source management presentation → R4-O M11 recovery → R4-P golden/
failure/restart tests → R4-Q full suite + KILLCRITIC + freeze.

Commit style: `feat(library): …` / `refactor(library): …` / `fix(library): …`,
one per package.

## 4. R5 — Collection Management (SPECIFICATION ONLY during R4)

Multi-selection by TrackIds/Album keys/Artist keys (never row index);
`TrackSelectionState{selected_track_ids, anchor_track_id}`; selection
survives recycling/sorting/resize; filter removes hidden items from selection;
context menu preserves/replaces selection; `BulkOperationResult{requested,
succeeded, failures}`; drag & drop MIME `application/x-michi-library-entities`
with id payload; Library Health diagnostic surface; duplicate taxonomy
(BYTE_IDENTICAL_FILE full SHA-256 cache / POSSIBLE_SAME_RECORDING metadata-only
/ DIFFERENT_EDITION — never merged, persisted ignore-groups by stable IDs);
edition identity from LOCAL evidence only (release id, edition tag, catalog
number, user override — never bitrate/samplerate/bitdepth/codec, never
downloaded knowledge); multi-disc canonical ordering + DISC groups; compilation
policy (explicit album_artist wins, else compilation → Various Artists, else
track artist; never inferred from differing artists); Artwork Manager
(AUTO/CUSTOM; CUSTOM authoritative with hardened validation — size, extension,
MIME, magic bytes, decode, atomic write; separate from enrichment store);
album rekey (TrackId stable; one-to-one rekey may transfer compatible state;
split/merge → review required).

## 5. R6 — Metadata & Navigation (SPECIFICATION ONLY during R4)

Three layers (SOURCE / USER OVERRIDE / EFFECTIVE; MusicModel+Search consume
EFFECTIVE); technical facts never editable (codec/container/rates/bitdepth/
channels/bitrate/size); `OverrideState{SET,CLEAR}` + field-absent = INHERIT;
pure `apply_metadata_override`; editor saves to Michi Library by default
(physical tag writer optional, explicit, `TagWriterPort`); batch edits with
explicit MIXED state + one transaction; undo/redo command journal (override
state only); classical fields via versioned metadata codec v2 + format-aware
readers (ID3/Vorbis/MP4) with fixture-verified mappings; WorkRef/Composer
navigation (ARTISTS|COMPOSERS secondary mode); advanced search EXTENDS M7
(plain queries byte-identical; `artist:"…"`, `year:1959`, `year:1950..1960`,
`bitdepth:>=24`, `source:"NAS"`, `available:true`, `favorite:true`; unknown
`foo:bar` stays plain text); facets (cross-group AND, same-group OR,
disjunctive counts); parser in DOMAIN.

## 6. R7 — Advanced Local Library (SPECIFICATION ONLY during R4)

CUE model (MediaFile → N Tracks; no fake audio files); `TrackMediaSegment`
(start/end frames, integer 75fps); `PlaybackTarget{track_id,file_path,
start_ms,end_ms}`; `CueSheetParserPort` fixture-driven dialects; single-image
CUE hides raw track; ambiguous multi-CUE claims → Library Health conflict;
Smart Collections (persist collection_id/name/raw_query/sort_spec/view_profile
— membership derived, never copied); Saved Searches (raw query only);
ListeningSessionRecord facts (monotonic PLAYING-only accumulation; pause adds
nothing; seeks never fabricate/remove time); export USER/NON-REBUILDABLE state
only (catalog IDs, sources, media mapping, favorites, history refs, playlists,
navigation, overrides, custom artwork, saved searches, smart collections,
listening events, UI prefs); import security (reject absolute paths,
traversal, symlink escape, oversized manifest/assets, malformed/future
schema; stage → validate → preview → map → commit DB → commit assets →
verify; cross-database staging journal, never claim one transaction);
large-library benchmarking (10k/50k/100k: startup hydration, memory,
unchanged scan, one-file modification, offline startup, search, facets, Songs
load, scroll, models, artwork) before any QML scale work; FTS5 candidate
acceleration only (canonical → FTS candidate TrackIds → M7 scorer →
deterministic order; never a second search truth).

## 7. KILLCRITIC matrix (pre-implementation, R4)

| CURRENT FACT | PROBLEM | TARGET CONTRACT | COMPATIBILITY IMPACT | MIGRATION IMPACT | TEST REQUIRED |
| --- | --- | --- | --- | --- | --- |
| `make_track_id(path)` = path | path identity; move/rename breaks refs | `TrackRef.track_id` stable | keep helper, quarantine + structural ban | path→TrackId map | structural + behavioral |
| TrackRef drops 7 metadata fields | metadata loss | parity with TrackMetadata | additive fields w/ defaults | none (cache) | parity test |
| AlbumRef.track_paths membership | path membership | track_ids membership + derived paths | `track_paths` derived projection | derived from catalog | golden move |
| Playlist V2 path authority | playlist refs break on move | V3 track_ids + fallback_path | V1/V2 decoders stay | rewrite in migration TX | migration + idempotence |
| prefs best-effort path save | fake durability | user-state repo truthful | old prefs rows migrate | cross-state atomic | failure injection |
| session V2 path entries | restore needs old path | V3 library_track_id | V1/V2 decode stays | upgrade entries in TX | V3 restore + V1/V2 |
| search/projection path ids | search breaks on move | stable ids + legacy fallback | ranking unchanged | none | M7 regression |
| sort tie-break path | reorder on move | tie-break by track_id | stable order | none | golden move |
| TRACK_MISSING removes track | Play deletes identity | mark MISSING, preserve | old behavior removed | availability state | missing-file golden |
| single-directory scan | source B wiped by A | per-source union | current_directory deprecated | catalog sources | two-source golden |
| M11.2 authoritative set | catalog not protected | + catalog/user tables | recovery checks extend | none | recovery golden |

## 8. Compatibility seam inventory

| Seam | Purpose |
| --- | --- |
| `make_track_id()` kept | legacy tests pin it; docstring marks LEGACY-PATH-IDENTITY-COMPATIBILITY-ONLY |
| `TrackRef(file_path=…)` defaults | frozen legacy construction keeps working (ids default `""`) |
| `Playlist(track_paths=…)` | legacy field retained as fallback snapshot; new ops resolve `track_ids` first |
| `AlbumRef.track_paths` derived | projection via resolver for legacy consumers; membership = track_ids |
| `LibraryBridge` path properties | `favoritePaths/historyPaths/recentlyAddedPaths/songPaths` derived via resolver; new ID properties added |
| `activate_path/toggle_favorite(path)` wrappers | delegate to ID-based canonical intents |
| Session V1/V2 decoders | preserved; migration upgrades persisted rows to V3 |
| `current_directory` | deprecated compat projection only |

## 9. R4 Definition of Done (checklist — tracked per work package)

Stable TrackId/MediaFileId/LibrarySourceId; source_id not repurposed;
TrackRef stable IDs + metadata parity; Album membership TrackId-based; Search
stable IDs + M7 ranking intact; stable tie-break; catalog separate from cache;
versioned fail-closed schema; truthful writes; transactional migration;
favorites/history/recent/playlists migrated; queue + sequence + session V3;
rich entry-committed event; history by TrackId; multi-source with isolation;
offline/missing zero identity loss; Play cannot delete; root relocation and
same-source rename preserve IDs; recently-added ignores
move/modify/relink; offline cached browse + artwork + M7 search; production/
test graph parity; M11 recovery includes new authority; new tests pass; full
suite passes; P0=0; P1=0 → freeze. R5/R6/R7/Audio Lab NOT implemented.
