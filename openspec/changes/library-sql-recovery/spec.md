# Delta: Library SQL Recovery

Change `library-sql-recovery` recovers stranded PR#125 (52 commits, 35 files) onto converged `main` (post PR#127) via 5 sequential PR slices A→B→C→D→E. This spec consolidates the deltas for every capability touched by each slice. Group D is ADDED to the existing `qml-playback-queue` capability (new cover-resolution behavior, no existing requirement rewritten); Groups A/B, C, and E define new capabilities.

## Capability Mapping

| Slice | Capability | Delta type | Key files |
|-------|-----------|------------|-----------|
| A | library-sql-metadata | New | `library/migrations.py`, `core/library/library_filtered_query_service.py` |
| B | library-sql-metadata | New (extends A) | `library/metadata_normalizer.py`, `library/batch_writer.py` |
| C | library-artist-folder-views | New | 6 QML: ArtistCard, ArtistGridPage, FolderBreadcrumb, FolderBrowserPage, FolderContentView, FolderTreeView |
| D | qml-playback-queue | ADDED | `ui_qml_bridge/cover_provider_bridge.py`, `ui_qml/components/CoverImage.qml` |
| E | library-premium-ui | New | 12 QML: album views, toolbar, search, filter, header, host |

## ADDED Requirements

### Requirement: Idempotent SQL migration engine (Group A)

The system MUST provide `library/migrations.py` as an idempotent, forward-only migration engine. Re-applying an applied migration MUST be a no-op. Applied migrations MUST be recorded. A failed migration MUST leave the database at the last fully-applied state.

#### Scenario: Fresh database applies all migrations in order
- GIVEN an empty SQLite library database
- WHEN the migration engine runs
- THEN every migration applies once in declared order and is recorded as applied

#### Scenario: Re-running migrations is a no-op
- GIVEN a database where all migrations are already applied
- WHEN the migration engine runs again
- THEN no migration re-executes and the schema is unchanged

#### Scenario: Partial failure halts safely
- GIVEN a migration that fails mid-execution
- WHEN the engine encounters the failure
- THEN the database remains at the last successful migration and the failure is reported

### Requirement: Filtered library query service (Group A)

The system MUST provide `core/library/library_filtered_query_service.py` serving library queries through indexed columns. Text search MUST delegate to FTS5 and MUST NOT use `LIKE`. The service MUST expose filtered queries by artist, album, folder, format, and year.

#### Scenario: Filtered query uses indexed columns
- GIVEN an indexed library database
- WHEN a filtered query is requested
- THEN results are returned via indexed columns without a full table scan

#### Scenario: Text search uses FTS5
- GIVEN a free-text library search
- WHEN the query service executes it
- THEN it resolves through the FTS5 index and never emits a `LIKE` clause

### Requirement: Centralized metadata normalization (Group B)

The system MUST provide `library/metadata_normalizer.py` as the single normalization source for artist, album, title, and genre. Normalization MUST be deterministic: identical raw input MUST always yield identical output. Missing or empty fields MUST normalize to defined defaults.

#### Scenario: Normalization is deterministic
- GIVEN the same raw metadata tag
- WHEN normalization runs repeatedly
- THEN every run yields the identical normalized value

#### Scenario: Missing fields use defined defaults
- GIVEN a track whose artist or album tag is empty or absent
- WHEN normalization runs
- THEN the missing field resolves to the documented default without raising

### Requirement: Batch writer persists normalized records (Group B)

`library/batch_writer.py` MUST persist normalized records in batches of at most 100 and MUST flush at the threshold. Re-indexing MUST upsert by album/track key and MUST NOT create duplicate rows.

#### Scenario: Batch flushes at threshold
- GIVEN 100 normalized records queued
- WHEN the 100th record is added
- THEN the batch is flushed to the database in one write

#### Scenario: Re-index upserts instead of duplicating
- GIVEN a track already present from a prior index
- WHEN the same track is re-indexed
- THEN the existing row is updated and no duplicate row is created

### Requirement: Artist browse surface (Group C)

The system MUST provide QML artist views (ArtistCard, ArtistGridPage) that render an artist grid and navigate from an artist to their albums. Views MUST render offscreen without QML warnings.

#### Scenario: Artist grid navigates to albums
- GIVEN a populated library rendered in ArtistGridPage
- WHEN an ArtistCard is activated
- THEN the artist's albums are shown

#### Scenario: Empty artist state
- GIVEN a library with no artists
- WHEN ArtistGridPage renders
- THEN an empty state is shown without warnings

### Requirement: Folder browse surface (Group C)

The system MUST provide QML folder views (FolderBreadcrumb, FolderBrowserPage, FolderContentView, FolderTreeView) that render a folder hierarchy, breadcrumb, and content. Navigation MUST reflect the current folder path.

#### Scenario: Breadcrumb navigates hierarchy
- GIVEN a folder tree deeper than one level
- WHEN a breadcrumb segment is activated
- THEN the view navigates to that folder and the breadcrumb updates

#### Scenario: Folder content renders offscreen
- GIVEN a populated folder
- WHEN FolderContentView renders offscreen
- THEN files are listed without QML warnings, list blur, or per-item shadows

### Requirement: Cover provider bridge (Group D — qml-playback-queue)

The system MUST provide `ui_qml_bridge/cover_provider_bridge.py` exposing cover resolution by `coverKey` to QML. The bridge MUST NOT cache or subscribe to queue state (preserving single-queue-observation), and MUST return a stable empty result for missing covers. `CoverImage.qml` MUST consume this bridge and MUST NOT resolve covers through `NowPlayingBridge`.

#### Scenario: Cover resolves by key
- GIVEN a queue item with a valid coverKey
- WHEN QML requests the cover through the bridge
- THEN the corresponding cover image is returned

#### Scenario: Missing cover renders empty state
- GIVEN a queue item whose coverKey has no artwork
- WHEN CoverImage.qml renders via the bridge
- THEN an empty placeholder is shown without QML warnings

#### Scenario: Bridge does not duplicate queue observation
- GIVEN the cover provider bridge is active
- WHEN queue state changes
- THEN no second queue projection or subscription is created in the bridge

### Requirement: Premium library UI (Group E)

The system MUST provide premium QML surfaces (album views, toolbar, search, filter, header, host) driven by the filtered query service (Group A). The UI MUST use theme tokens, MUST NOT display fake data as real, and MUST preserve no-parent-opacity, no-list-blur, and no-per-item-shadow constraints.

#### Scenario: Album view driven by filtered query service
- GIVEN the premium album view is shown
- WHEN a filter or search is applied
- THEN results come from the filtered query service and the view updates

#### Scenario: Premium UI renders offscreen without fake data
- GIVEN the premium host composes album, toolbar, search, and filter
- WHEN it renders offscreen
- THEN no QML warnings, fake data, or convergence regressions occur

## Non-functional Requirements (all slices)

- Each PR slice MUST independently pass `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300`, `ruff check .`, and `python -m compileall -q -x '.venv/|\.tmpl\.' .` before the next slice opens.
- Each PR slice MUST NOT regress PR#127 queue/NowPlaying convergence behavior (single queue projection, single playlist save, distinct ingress semantics).
- The 16 conflicting QML files MUST be reconciled against converged `main` (PR#127) via explicit per-PR reconciliation commits.
- `origin/main` MUST be merged (not rebased) into `integration/library-sql-recovery` as one conflict-resolution commit.
- Slices MUST land in strict order A → B → C → D → E; each MUST be gated green before the next begins.
- The final `main` diff MUST be semantically equivalent to the original PR#125 tip — same 35 files, no lost functionality.

## Acceptance Criteria per PR Slice

| PR | Slice | Verification gate | Convergence check | Exit criteria |
|----|-------|-------------------|-------------------|---------------|
| A | SQL migrations | pytest + ruff + compileall green | No queue/NowPlaying surface touched | Merge tagged `recovery/group-a`; migrations idempotent; FTS5 (no `LIKE`) verified |
| B | Metadata normalization | green | No queue/NowPlaying surface touched | Normalization deterministic; batch writer upserts; `test_metadata_normalizer.py` + `test_batch_writer_metadata.py` pass |
| C | Artist/folder views | green + `tests/qml/library/test_library_navigation_views_runtime.py` | 6 QML reconciled vs PR#127; no convergence regression | Views render offscreen without warnings |
| D | Bridges | green + `tests/test_cover_provider_bridge.py` | Cover wiring adds no second queue projection/subscription | CoverImage resolves via bridge; empty state for missing covers |
| E | Premium UI | green + 3 premium test files | 12 of 16 conflicts reconciled vs PR#127; no convergence regression | Final `main` diff == PR#125 tip (35 files), semantically equivalent |

## Rollback

Each PR is independently revertible via `git revert` of its merge commit. `integration/library-sql-recovery` is disposable; on failure, delete the branch and restart from `origin/main`. The original PR#125 branch is preserved as fallback reference — no destructive history rewrite.
