# M7 — Search: Rich Canonical Local Search — Master Plan

Status: **M7 — CLOSED / TESTED / FROZEN** (baseline `ee8c23f5f6e90d20c2902ac5ab29c639b03f7282`; current effective closeout HEAD `677468f0b0c1e102a36cd9654aca5fae73a6b715`).

> **M7.7 closeout (FINAL STATE)**
>
> **M7 — SEARCH: CLOSED / TESTED / FROZEN; SEARCH MODEL CANONICAL/LOCAL/
> OFFLINE; QUERY RAW-PRESERVED/NORMALIZED/ACCENT+CASE-INSENSITIVE/
> MULTI-TOKEN; FIELDS TITLE/ARTIST/ALBUM/ALBUM-ARTIST/GENRE/COMPOSER/
> DISPLAY-NAME; MATCHING EXACT/PREFIX/TOKEN-PREFIX/SUBSTRING; RELEVANCE
> DETERMINISTIC (score desc → canonical title → canonical ID; input-order
> independent); ENTITIES TRACKS/ALBUMS/ARTISTS/GENRES/COMPOSERS; LIBRARY
> UNIFIED SEARCH PROJECTION (Songs/Albums/Artists/Genres/Favorites/History/
> Recently-Added through the SAME matched sets; clear restores canonical
> exactly); SIX ALBUM VIEWS ONE FILTERED CANONICAL MODEL; SELECTION
> CANONICAL-SAFE (filtering never deletes; real removal still clears);
> ACTIVE SEARCH FOLLOWS STRUCTURAL CHANGES (query survives rescans; corpus
> rebuilt on structural mutation only); FTS POST-1.0; AI NOT INVOLVED;
> NO PERSISTENCE; NO FILESYSTEM/MUTAGEN ACCESS; P0=0; P1=0.**
>
> Test gates: 49 domain (query model/fields/ranking/entities) + 18 library
> integration + 8 presentation + 18 golden/scale — 1195-suite green at the
> current effective closeout HEAD. Advanced field syntax/ranges/technical
> filtering/playlist+folder search/year ranges remain FUTURE (documented
> exclusions). M12 owns performance profiling; 10k correctness +
> determinism baseline recorded (no timing claims).
>
> **M7-CANONICAL-SEMANTICS-AND-RANKING-CORRECTION (re-close):**
>
> - **Track `album_artist` = M6 CANONICAL RESOLVED ALBUM ARTIST.** M6's
>   `resolve_album_artist(track)` (explicit album_artist → compilation
>   "Various Artists" → track artist) is now PUBLIC API, used by BOTH
>   `build_music_model` and `TrackSearchDocument.from_track` — one and only
>   one source of truth; no duplicate "Various Artists" constant in search.
>   A compilation (a-ha / 80s Collection) is found by "Various Artists" as
>   BOTH a Track result and the Album result, agreeing on the same resolved
>   artist. Explicit album_artist still wins over the compilation fallback.
> - **Album entity ranking is TITLE-FIRST.** A dedicated AlbumSearchDocument
>   uses wide semantic bands (title 4000 > album artist 3000 > composer
>   2000 > genre 1000) + match bonuses (exact 400 > prefix 300 > token
>   prefix 200 > substring 100): an exact album title always outranks an
>   exact album-artist match on another album; within a field, match types
>   still order EXACT > PREFIX > TOKEN_PREFIX > SUBSTRING; AND semantics
>   across tokens preserved (miles blue → artist + title). Ranking only
>   affects ORDER — never album identity/grouping/membership.
> - **Track tie-break honors canonical sort metadata:** score desc →
>   `normalize(sort_title or title)` → track_id. sort_title is ORDERING
>   metadata only — it is NOT an eighth searchable field.
> - **Composer entity rows exposed vertically:** `LibraryBridge.composers`
>   Property (canonical passthrough; filtered by the active search; clear
>   restores) — no new tab/navigation (M9 decides rendering).
> - **Six-view invariant hardened:** every album mode (grid/cover/vinyl/
>   timeline/magazine/list) verified to consume the SAME filtered canonical
>   AlbumIds — not just the same count.
>
> Re-close gates: 24 tests (test_search_canonical_semantics.py). CI
> evidence, truthful: the first exact-HEAD CI run of the re-close
> (32286592546) FAILED — the six-view tests relied on pytest-qt's `qapp`
> fixture, which exists locally but not in CI; fixed by defining the
> module-scoped offscreen fixture (677468f); the current effective
> closeout HEAD 677468f is CI GREEN (run 32286911191, success); local
> focused gate 24/24 and local full suite 1195 green.

## 0. Contract Reconciliation (M7.0)

**Current search state (audited at M7.0 open):**

- `LibraryState.query: str` — stores the NORMALIZED lowercase query
  (`LibraryService.search` does `query.strip().lower()`), which DESTROYS the
  user's written form (raw query is not preserved for presentation).
- `LibraryState.visible_tracks` — getter with embedded substring search over
  `display_name` ONLY; no title/artist/album/album_artist/genre/composer.
- No album/artist/genre/composer results: those views always show the full
  canonical model.
- `LibraryBridge.searchQuery` → `state.query`; `search(query)` slot →
  `service.search`; `LibraryToolbar.qml` binds a `MichiTextField` with
  `onTextEdited: library.search(text)`.
- `_commit_scan_result` currently RESETS `state.query = ""` on every
  successful scan (search lost on rescan).
- Selection is already canonical-safe: `LibraryBridge.select_album` validates
  against `state.albums` (canonical), never filtered rows.

**Canonical decisions:**

| Decision | Value |
|---|---|
| M7 1.0 | RICH CANONICAL IN-MEMORY SEARCH (pure derived projection) |
| SQLite FTS | POST-1.0 |
| Search authority | Canonical M6 model (TrackRef/AlbumRef/ArtistRef/GenreRef/ComposerRef) |
| Search persistence | NONE (query starts empty on restart) |
| External services / AI / embeddings / vector | NONE |
| Filesystem / Mutagen access | NONE (operates only on loaded canonical data) |
| Search model | Single derived corpus rebuilt on structural change; no second musical truth |

**Architecture:**

```
Filesystem → M6 Library → Canonical Model → M7 Search Projector
            → SearchProjection → LibraryService/Search boundary
            → LibraryBridge → QML
```

**Boundaries:** pure normalization/matching/ranking/projection live in
`domain/search.py`; library integration and lifecycle in
`application/library_service.py`; bridge/QML only project (no matching,
no scoring, no normalization in Presentation). No Infrastructure changes.

## 1. Query Model (M7.1)

- `SearchQuery(raw, normalized, tokens)` — frozen dataclass; raw preserved
  verbatim; normalized = Unicode NFKD → strip combining marks (accent-
  insensitive) → casefold → collapse whitespace → strip; tokens = the
  normalized text split on whitespace (never empty tokens).
- `normalize_search_text` is THE single normalization helper — never
  repeated inline.

## 2. Track Search + Matching (M7.2)

Searchable fields (all already on TrackRef — NO re-extraction):

`title, artist, album, album_artist, genre, composer, display_name`

`TrackSearchDocument` = search representation (canonical ID + normalized
fields) — NOT a new musical entity. Multi-token semantics: AND across
tokens; each token must match at least one searchable field (any field);
cross-field matching allowed (`miles blue` → miles:artist + blue:album).

Match types: EXACT > PREFIX > TOKEN_PREFIX > SUBSTRING > NONE. No fuzzy.

## 3. Deterministic Ranking (M7.3)

Score = best field+type per token, summed across tokens.

Field priority: title (600) > artist (500) ≈ album_artist (500) > album
(400) > composer (300) > genre (250) > display_name (100).

Match-type bonus: EXACT 1000 > PREFIX 700 > TOKEN_PREFIX 500 > SUBSTRING 300.

Per-token: best (field, type) score wins (first-field-wins on exact ties,
fixed field order — deterministic). A garbage multi-field substring can
never outrank an exact title (2 tokens max ≈ 2×700 < exact title 1600).

Tie-break: score desc → canonical display sort (title/sort_title casefold,
then path) → canonical ID. NEVER input order.

## 4. Entity Search (M7.4)

`SearchProjection(query, tracks, albums, artists, genres, composers)` —
frozen; counts derived. Entities consumed DIRECTLY from M6 model:

- Albums: title, album_artist, genres, composers (year text optional —
  NOT included in M7 1.0; technical summary excluded).
- Artists: name only (no relation expansion).
- Genres: name. Composers: name.
- Per-entity scorer: exact > prefix > token-prefix > substring; tie-break
  canonical.

## 5. Library Integration (M7.5)

- `LibraryState` gains `search_projection: SearchProjection | None` and
  `search_active` (derived). `query` becomes the RAW string.
- `LibraryService.search(raw)`: normalize → if no tokens → clear projection
  (canonical passthrough); else project from the corpus. Notify once.
- `clear_search()`: raw "" + projection None (canonical collections
  restored exactly).
- **Corpus**: `SearchCorpus` derived from canonical state, rebuilt ONLY on
  structural change (centralized `_refresh_search_projection` called from
  `_commit_scan_result` and `_rebuild_derived_library_state`); query changes
  only match the pre-normalized corpus. `_commit_scan_result` NO LONGER
  clears the query — active search follows the new canonical library.
- Favorites/history/recently-added: filtered by `matched_track_ids ∩
  paths` when search is active (same matching, no duplicate logic).
- Playlists and folders: UNAFFECTED in M7 1.0 (documented as future).
- Six album views consume THE SAME `SearchProjection.albums` (bridge rows);
  timeline = `build_timeline_projection(filtered albums)`.
- Selection stays canonical-safe: `select_album` keeps validating against
  canonical `state.albums` — filtering is never deletion.

## 6. Presentation (M7.6)

- Bridge: `searchQuery` (RAW), `searchActive`, `searchTrackCount`,
  `searchAlbumCount`, `searchArtistCount`, `searchGenreCount`,
  `searchComposerCount`, `searchTotalCount`, `clear_search()` slot.
  NO normalization/ranking in the bridge.
- Toolbar: search field shows the raw query, placeholder "Search...",
  clear action; deterministic "No results" state when active and total == 0.
  Functional only (M9 styles). Debounce optional (presentation-only);
  Application search stays synchronous and immediate.
- No search business logic in QML (no filter/includes/score).

## 7. Golden + Scale + Closeout (M7.7)

Golden dataset: Blue/Joni Mitchell, So What/Miles Davis (Kind of Blue),
Time/Hans Zimmer (Inception), Cornfield Chase/Hans Zimmer (Interstellar),
plus accented artist/title, compilation/Various Artists, same-title
different album artists, unknown metadata, filename fallback, multidisc,
genre collisions, composer-only matches. Required goldens: case/accent
insensitivity, exact-title precedence, artist/album/album-artist/genre/
composer queries, multi-token AND semantics, input permutation
determinism, six-view same-model, clear restores canonical, active-search
rescan/metadata-modification rebuilds, selection safety.

10k scale: correctness + determinism + no filesystem + no extraction +
no crash; baseline recorded only (M12 owns performance).

## Exclusions (locked)

FTS5, persistent search index, Elasticsearch/Lucene, AI/semantic/vector
search, NLP, recommendations, online metadata, Navidrome/ecosystem,
streaming/radio, Audio Lab, GStreamer/MPD, M9 redesign, M12 profiling,
advanced field syntax (`artist:`/ranges/boolean), technical-metadata
filtering, playlist/folder search, year ranges.

## Closeout state (target)

**M7 — SEARCH: CLOSED / TESTED / FROZEN; SEARCH MODEL CANONICAL/LOCAL/
OFFLINE; QUERY RAW-PRESERVED/NORMALIZED/ACCENT+CASE-INSENSITIVE/MULTI-TOKEN;
FIELDS TITLE/ARTIST/ALBUM/ALBUM-ARTIST/GENRE/COMPOSER/DISPLAY-NAME;
MATCHING EXACT/PREFIX/TOKEN-PREFIX/SUBSTRING; RELEVANCE DETERMINISTIC;
ENTITIES TRACKS/ALBUMS/ARTISTS/GENRES/COMPOSERS; LIBRARY UNIFIED SEARCH
PROJECTION; SIX ALBUM VIEWS ONE FILTERED CANONICAL MODEL; FTS POST-1.0;
AI NOT INVOLVED; P0=0; P1=0.**
