# Architecture

Authority for system boundaries, layer contracts, state ownership, lifecycle, and error semantics. All architectural decisions are recorded as Accepted ADRs in `docs/adr/`. This document aggregates them into one read-optimized reference.

Product scope note: Michi AI and ecosystem integrations (Audio Lab, Streaming, Radio, Sync, Michi Link/Mobile/Micro Server/Big Server/Music Stream, Home Audio) are RETAINED product capabilities implemented AFTER PLAYER STABLE — this codebase carries no AI, streaming, or ecosystem code. CoverFlow is RETIRED; its successor PathView is pre-Stable local work. See MASTER_ROADMAP_1.0.md Product Scope.

## Stack

Python 3.11+, PySide6 (Qt 6, Qt Multimedia with FFmpeg backend), QML, SQLite (WAL). Build with setuptools (`python -m build`); tests with pytest; lint/format with Ruff; CI on GitHub Actions (lint, tests with `QT_QPA_PLATFORM=offscreen`, build). No C++ anywhere, no native-code build system. (ADR 0001 — the original "no GStreamer integration" stack decision is SUPERSEDED by the 2026-08-21 product-owner realignment: GStreamer and a managed MPD become Required-1.0 audio engines behind AudioPort, scheduled M11.3, per docs/M11_3_MULTI_ENGINE_AUDIO_RUNTIME.md; GStreamer/MPD are runtime dependencies, never C++ build targets)

## Layers and Dependency Direction

```
        ┌───────────────────┐        ┌───────────────────┐
        │   presentation/   │        │  infrastructure/  │
        │  QML + bridges    │        │  Qt, SQLite, FS   │
        └─────────┬─────────┘        └─────────┬─────────┘
                  │ intents / projections      │ implements
                  ▼                            ▼
        ┌─────────────────────────────────────────────┐
        │              application/                    │
        │   services · coordinators · ports (ABCs)     │
        └──────────────────────┬──────────────────────┘
                               ▼
        ┌─────────────────────────────────────────────┐
        │                 domain/                      │
        │      pure Python state models and rules      │
        └─────────────────────────────────────────────┘

        bootstrap/ — composition root, wires everything above
```

| Layer             | Contents                                                                                                                                                                                                                                                                                             | May import                                               | Forbidden                        |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------- | -------------------------------- |
| `domain/`         | `PlaybackState` (+`PlaybackStatus`), `QueueState`, `LibraryState` (+`TrackRef`), `SettingsState`, `AppRoute`/`NavigationState`, `PersistenceHealth`/`PersistenceDiagnostic`                                                                                                                          | Python stdlib only                                       | Qt, I/O, application             |
| `application/`    | Ports: `AudioPort`, `SettingsRepository`, `LibraryScannerPort`. Services: `PlaybackService`, `QueueService`, `LibraryService`, `NavigationService`, `SettingsService`. Coordinators: `PlaybackCoordinator`, `LibraryPreferencesCoordinator`                                                          | domain                                                   | Qt, infrastructure, presentation |
| `infrastructure/` | `QtMultimediaBackend`, `FilesystemLibraryScanner`, `SQLiteSettingsRepository` (+ `inspect_path` health detection)                                                                                                                                                                                    | application (ports), domain, PySide6, SQLite, filesystem | presentation                     |
| `presentation/`   | `PlaybackBridge`, `QueueBridge`, `LibraryBridge`, `NavigationBridge`, `SettingsBridge` (read-only); QML: `main.qml`, `qml/theme/` tokens, `qml/ui/` compatibility controls, `qml/player/` canonical NowPlayingBar, `qml/shell/` AppShell/Sidebar/ContentHost, `qml/views/` routed content | application (services), domain (observed state), PySide6 | infrastructure                   |
| `bootstrap/`      | `ApplicationContainer` composition root                                                                                                                                                                                                                                                              | everything (the only layer allowed to)                   | —                                |

Rules:

- Dependencies flow inward: `presentation → application → domain`; `infrastructure → application` implements ports.
- `domain/` has no outward dependencies and no Qt imports.
- `infrastructure` never calls `presentation`; `presentation` never calls `infrastructure`.
- `bootstrap` is the only place that constructs infrastructure and presentation together.

## State Ownership

Exactly one service owns each state model. Every mutation routes through the owner (ADR 0003).

| State model                                 | Owner (application layer)                                                                                                                            | Location                       |
| ------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------ |
| `PlaybackState`                             | `PlaybackService`                                                                                                                                    | `domain/playback.py`           |
| `QueueState`                                | `QueueService`                                                                                                                                       | `domain/queue.py`              |
| `LibraryState` (+ `TrackRef`)               | `LibraryService`                                                                                                                                     | `domain/library.py`            |
| `SettingsState`                             | `SettingsService`                                                                                                                                    | `domain/settings.py`           |
| `AppRoute` / `NavigationState`              | `NavigationService`                                                                                                                                  | `domain/navigation.py`         |
| Playlist collection (`Playlist`)            | `PlaylistService` (sole authority; name is display-only, `playlist_id` is identity)                                                                  | `domain/playlist.py`           |
| Pinned/recent (`PlaylistNavigationState`)   | `PlaylistService` (navigation metadata; normalized SAFE-READ at startup, no load writeback)                                                           | `domain/playlist.py`           |
| `PersistenceHealth` (diagnostic, read-only) | produced by `SQLiteSettingsRepository.inspect_path()`; current production consumer: `SQLiteSettingsRepository.open_for_startup()` (M11.2D routing + M11.2E automatic recovery, TESTED) | `domain/persistence_health.py` |

- **Ingress rule**: no subsystem writes to a state model directly; all mutations are owner method calls.
- **Coordinator rule**: `PlaybackCoordinator` composes `PlaybackService` + `QueueService` for cross-cutting flows (auto-advance, play_index) and `LibraryPreferencesCoordinator` composes `LibraryService` + `SettingsService` (`last_directory`). Coordinators drive owners through public APIs; they never mutate state directly.
- **Projection rule**: owners expose state for observation via `.state`; mutation authority remains exclusively with the owner service. Presentation bridges treat exposed state as read-only by convention. State objects are mutable references, NOT immutable snapshots. Projections are never written back.
- Bootstrap configures owners through public APIs only; it never mutates domain state.

## QML Bridge Boundary

QML never touches services or domain objects directly (ADR 0004).

```
QML                     Bridge (presentation)            Application
──                      ───────────────────────          ───────────
MichiButton.clicked  →  bridge.on_play_clicked()      →  PlaybackService.play()
Label text           ←  bridge.title (property)       ←  PlaybackState (observed read-only)
```

- **Intents**: QML signals call bridge methods; bridges translate to service/coordinator calls. Bridges hold no business rules.
- **Projections**: bridges expose state to QML as properties read from owner `.state` objects, treated read-only by convention. State objects are mutable references, not immutable snapshots.
- **Read-only settings**: `SettingsBridge` exposes state for display only; settings mutations go through `SettingsService` (bootstrap/coordinators), never through QML.
- Bridges are the only place Qt types and application concepts meet.
## Playlists hierarchy (M9-R1, sealed)

- **PLAYLIST-HIERARCHY-01**: Playlists is a first-class Shell feature — it is
  NOT a Library navigation entity.
- **PLAYLIST-HIERARCHY-02**: Library may invoke Playlist actions (Add-to-
  Playlist by canonical id) but does not contain Playlists.
- **PLAYLIST-HIERARCHY-03**: all canonical Playlist navigation resolves
  through `AppRoute.PLAYLISTS`; QML opens playlists only via the validated
  `open_playlist` intent (PlaylistNavigationCoordinator).
- **PLAYLIST-HIERARCHY-04**: Playlist detail = `PLAYLISTS` + playlist_id;
  All Playlists = `PLAYLISTS` + None. No extra playlist routes.
- **PLAYLIST-HIERARCHY-05**: `PlaylistsBridge` owns the canonical Playlist
  presentation projection; `LibraryBridge` does not expose playlist screen
  state.
- **PLAYLIST-HIERARCHY-06**: Queue and Playlists remain independent
  authorities (QueueService / PlaylistService).

- `PlaylistNavigationCoordinator` (application layer, M8-R1F) is the
  canonical application seam for the OPEN PLAYLIST product intent:
  validate against PlaylistService → mark recent → navigate through
  NavigationService. It is NOT a state authority: it owns no state, no
  persistence, no Qt; PlaylistService and NavigationService remain the sole
  owners of their states.

## AudioPort Boundary

`AudioPort` (ABC in `application/ports.py`) is the audio contract. `QtMultimediaBackend` (infrastructure) implements it with Qt Multimedia (FFmpeg backend).

Operations: `load`, `play`, `pause`, `resume`, `stop`, `set_volume`, `set_muted`, `seek`, `position`, `duration`, plus end-of-media, position-changed, duration-changed, and error subscription callbacks.

- Application services depend on the port only; they never import PySide6 multimedia classes.
- The backend translates Qt signals into plain callbacks; services stay Qt-free.
- A fake backend substitutes the port in pure-pytest tests.

### Multi-engine target (M11.3 — product-owner realignment 2026-08-21)

`AudioPort` remains the playback backend boundary. PlaybackService stays the
sole PlaybackState owner and QueueService the sole QueueState owner; new
engines adapt TO Michi contracts, never the reverse:

```
                  AudioPort
                     │
          ┌──────────┼──────────┐
          │          │          │
          ▼          ▼          ▼
    QtMultimedia  GStreamer    MPD (managed/private)
```

- **Qt Multimedia** — REFERENCE / SAFE engine (current backend; desktop-shared
  only; never a DIRECT bit-perfect VERIFIED claim — honest limitation).
- **GStreamer** — FULL PIPELINE ENGINE CANDIDATE (ALSA/PipeWire sinks; caps
  truth for telemetry). No GStreamer types outside infrastructure.
- **MPD** — MANAGED AUDIO TRANSPORT ENGINE (private instance, generated
  config). MPD MUST NOT own canonical Michi Queue/Repeat/Shuffle/Playlist
  semantics; it is an engine behind AudioPort only.
- Engine selection uses an Application-owned semantic plan. Preference-only
  changes never churn the runtime. Explicit runtime changes accept canonical
  STOPPED/PAUSED/PLAYING state and perform a controlled stop-and-rehydrate
  transition that preserves logical media/position and ends STOPPED. Selection
  is persisted; no seamless/autoplaying handover occurs.
- **Owners (M11.3A)**: `AudioEngineService` → AudioEngineState (sole
  authority; SELECTED != ACTIVE); `AudioEngineRegistry` → provider set (one
  per canonical id, deterministic order); providers (`AudioEngineProviderPort`)
  own engine lifecycle (probe/open/close). `AudioTransportRouter` implements
  AudioPort + AudioTransportBindingPort — PlaybackService/Coordinator keep
  subscribing to the SAME router object across engine switches.
  **M11.3F — `AudioEngineSelectionCoordinator`** is the single explicit
  switch transaction (application layer, framework-free, providers only via
  the registry): semantic plan → atomic Playback snapshot/lease → persist
  SELECTED (SettingsService, durable BEFORE destructive work) → privileged
  controlled stop when needed → closing → router unbind → source close →
  invalidate old backend acceptance → initializing → target open → bind +
  validate → restore volume/mute → READY → bounded stopped-media load/seek
  rehydration without autoplay. SELECTED != ACTIVE is truthful during the window and
  after restart (F restart contract: persisted selected restored, active stays
  Qt READY until explicit switching — M11.3G owns automatic convergence).
  No fallback, no reopen, no auto-select.
  Backend-specific device strings live only in adapter bindings; the domain
  never persists `hw:N`/card-index as canonical identity.
  ADR: docs/adr/0007-multi-engine-audio-runtime.md.

  **Wiring truth (M11.3B + M11.3B-R1)**: the router IS PRODUCTIVE — the
  current graph connects PlaybackService/PlaybackCoordinator through ONE
  AudioTransportRouter bound to the Qt provider's single owned backend.
  The registry holds the SAME canonical Qt provider instance
  (registry.provider(QT_MULTIMEDIA) is qt_provider); reference startup is
  transactional (PROBE→CAN_ACTIVATE→INITIALIZING→OPEN→BIND→VALIDATE→READY
  with UNAVAILABLE/FAILED convergence). The GStreamer adapter (M11.3C)
  attaches behind the same router: GStreamerEngineProvider →
  GStreamerAudioPort (playbin3, lazy GI, own GLib pump + Qt bridge
  dispatch, generation-guarded stale isolation) — available when the GI
  runtime exists, never the default. MPD attaches behind the same AudioTransportRouter through MpdEngineProvider → MPDAudioPort: managed/private MPD child, private AF_UNIX socket, Michi-owned lifecycle, engine-local queue slot only — never QueueService authority.
- **Audio Lab boundary**: a future DSP stage (CamillaDSP-style external
  process) may insert between Engine and Output Policy AFTER PLAYER STABLE;
  the architecture leaves the seam, the stage is not implemented.

## SettingsRepository Boundary

`SettingsRepository` (ABC) is the persistence contract. `SQLiteSettingsRepository` (infrastructure) implements it against a single SQLite database (WAL) in the platform app-data directory.

- `SettingsService` is the only caller of repository mutations.
- The read-only health-detection capability (`inspect_path`, extended-result-code normalization) is implemented and unit-tested (M11.2A), producing a `PersistenceHealth` classification: MISSING, HEALTHY, CORRUPT_DATABASE, MALFORMED_DATA, LOCKED, ACCESS_FAILURE, IO_FAILURE, UNKNOWN_FAILURE. Inspection never mutates the file.
- Current vs target: the read-only inspection IS wired into startup via `SQLiteSettingsRepository.open_for_startup()` (M11.2D, TESTED) — preflight runs before any writable repository construction and before backend construction.
- M11.2B (TESTED): `SQLiteSettingsRepository` exposes `last_known_good_path` (`<db>.lkg`), `refresh_last_known_good` (only a HEALTHY primary may refresh; SQLite backup API from a read-only source; unique sibling temp candidate validated before atomic `os.replace` promotion; an existing LKG is preserved for all failures occurring before successful atomic promotion — a candidate is validated before `os.replace()`, so only a validated SQLite snapshot is promoted) and `stage_recovery_from_last_known_good` (healthy-LKG-only source; SQLite backup API into an exclusively reserved new destination — `O_CREAT | O_EXCL` — validated before success; `FileExistsError` on existing destinations; `ValueError` on primary/LKG aliases; foreign files never overwritten or deleted; primary and LKG never mutated). M11.2E automatic recovery is the production consumer of these primitives (`stage_recovery_from_last_known_good` stages the candidate that M11.2E validates and installs).
- M11.2C (TESTED): field-level malformed-data recovery. `load()` decodes each persisted field independently; a malformed value falls back to its domain default with one logged warning while valid sibling fields are preserved; no field is silently coerced; nothing is written back to SQLite (safe read fallback, not repair). Canonical persisted `muted` representation is `"true"`/`"false"` (as written by `save()`), and `load()` and `inspect_path()` agree on it. The health classifier remains strict: a database containing malformed data still reports `MALFORMED_DATA` even though `load()` can produce a safe `SettingsState` — load tolerance is not database health.
- M11.2D (TESTED): startup preflight + recovery routing. `ApplicationContainer` calls `SQLiteSettingsRepository.open_for_startup(db_path)` before `QtMultimediaBackend` construction; the classmethod reads health first (READ FIRST, DECIDE SECOND, WRITE ONLY WHEN AUTHORIZED): HEALTHY → best-effort LKG refresh then writable open; MISSING with no recovery material → true first run (create + validate); MISSING with LKG/candidate → staged recovery into `<db>.recovery` (M11.2D itself did not install candidates; M11.2E installs them after validation for recoverable states); field-level MALFORMED_DATA (read-only structural probe passes) → writable open of the same primary, M11.2C fallback applies; structural MALFORMED/CORRUPT → recovery staging (installed by M11.2E after validation); LOCKED/ACCESS_FAILURE/IO_FAILURE/UNKNOWN_FAILURE → `PersistenceStartupError`, no fallback, no staging, no writable open. M11.2D itself never replaced, renamed, deleted, or repaired the primary and never installed staged candidates; the validated atomic install is M11.2E's responsibility. For an initially MALFORMED_DATA primary, structural readability is probed read-only: genuine schema malformation routes to non-destructive recovery staging, while environmental/operational failures during that probe are reclassified through the existing persistence-health taxonomy — LOCKED / ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE block startup and never trigger LKG fallback.
- M11.2E (TESTED): validated automatic restore + quarantine. Recoverable primaries (MISSING / CORRUPT_DATABASE / structural MALFORMED_DATA) with a healthy LKG are auto-restored: a candidate (`<db>.recovery`, staged from the LKG via the SQLite backup API or a pre-existing trusted candidate) is installed only after it is HEALTHY, its logical AUTHORITATIVE rows exactly match the LKG rows (M6-FINAL-CROSS-PERSISTENCE-GATE: settings AND library_prefs — see "michi.db Durability Ownership" below), and it has no `-wal`/`-shm` sidecars; the original primary artifacts are quarantined first as byte-exact evidence into a fresh `<db>.quarantine/recovery-*` generation (0o600 copies verified by size + streaming SHA-256; quarantine is evidence only, never a recovery source); original primary sidecars are strictly removed before the atomic `os.replace(candidate, primary)` install; the installed primary is re-inspected HEALTHY before the writable repository is constructed; the LKG is preserved; terminal states (LOCKED/ACCESS/IO/UNKNOWN) remain non-recovering and field-level MALFORMED_DATA stays on the M11.2C path. The LKG is never mutated by recovery: committed WAL-visible LKG state is preserved, and LKG -wal/-shm sidecars are not recovery housekeeping targets.
- Conservative handling: HEALTHY/MISSING proceed to normal flow; all failure classes produce an explicit diagnostic with no silent fallback and no destructive repair. M11.2E (TESTED) implements automatic restore + quarantine on top of this taxonomy for recoverable states only; terminal environmental failures remain non-recovering.
- Persisted fields: volume, muted, last_directory, recent_files. Restart gate: values apply only after a successful restart restore.

## michi.db Durability Ownership (M6-FINAL-CROSS-PERSISTENCE-GATE, TESTED)

M6 introduced NEW authoritative durable state inside the SAME `michi.db` that
M5/M11.2 recovery protects. The cross-persistence contract (verified by
`tests/test_persistence_cross_context.py`):

| Region | Classification | Rationale |
| ------ | -------------- | --------- |
| `settings` (incl. `session_snapshot` row) | **AUTHORITATIVE** application/session state | user/application decisions; NOT reconstructable |
| `library_prefs` (favorites/history/recently_added/playlists) | **AUTHORITATIVE** user library state | user decisions; NOT reconstructable |
| `library_index` | **REBUILDABLE CACHE** | the FILESYSTEM is the authority over file existence; the index is cached musical knowledge reconstructable by scanning + extraction |
| `library_meta` | **CACHE SCHEMA METADATA** | versioning for the rebuildable index |

Consequences:

- **LKG = FULL DATABASE SNAPSHOT**: `refresh_last_known_good` /
  `stage_recovery_from_last_known_good` use the SQLite backup API on the
  COMPLETE database — every table (including M6's) rides along and survives
  recovery.
- **PROVENANCE = AUTHORITATIVE LOGICAL STATE**: `_candidate_matches_lkg`
  compares ordered `(key, value)` rows of `_AUTHORITATIVE_TABLES`
  (`settings`, `library_prefs`) — never binary bytes, never WAL layout,
  never settings-only, never cache equality. The table set is centralized in
  ONE place (`_AUTHORITATIVE_TABLES`); future authoritative tables are added
  there.
- **Absence semantics**: an ABSENT optional authoritative table (`library_prefs`
  in pre-M6 databases) is logically equivalent to an EMPTY one; a NON-empty
  table is never equivalent to a missing one. Backward compatible, tested.
- **Cache divergence never invalidates recovery**: a candidate whose
  `library_index` differs from the LKG's is authorized (provenance passes);
  the full-database install preserves whichever cache the candidate carries,
  and a missing/cleared index is safely rebuilt from the filesystem.
- **Failure semantics**: a `library_index` durability failure degrades
  performance (re-extraction) but MUST NOT corrupt authoritative user data;
  `library_prefs`/`playlists` durability failures keep their best-effort
  load/save contracts.
- **Hydration note**: instant index hydration (cached library shown at
  startup, async filesystem reconciliation) is NOT implemented — classified
  as POST-M6 / M12 startup improvement. The filesystem remains the authority
  over physical existence.

**Authoritative user data decoding (M6-AUTHORITATIVE-DATA-DECODE-GATE,
TESTED)** — library user state is authoritative but decoded DEFENSIVELY.
AUTHORITATIVE means "the user's persisted state is not reconstructable from
the filesystem" — it does NOT mean "malformed bytes must crash the app".

Valid shapes (the ONLY accepted ones):

- `favorites` / `history` / `recently_added`: JSON `list[str]`
- `playlists`: JSON `list` of `{"name": str, "track_paths": list[str]}`

Malformed values (scalars, JSON strings, objects, null, booleans, mixed
lists like `["A", 42]`, invalid JSON) degrade with SAFE EMPTY FALLBACK:
- `LOAD NEVER RAISES` — no persisted shape can escape TypeError/ValueError/
  KeyError/AttributeError/IndexError;
- NO FABRICATION — a JSON string never iterates into characters, a JSON
  object never yields its keys as paths;
- NO PARTIAL SALVAGE — `["A", 42, "B"]` -> `()`, never `("A", "B")`;
- malformed playlist ROOT -> whole collection `()`; malformed playlist ENTRY
  -> that entry discarded, valid siblings preserved;
- the storage contract accepts ONLY SQLite TEXT for these JSON payloads: a
  non-text SQLite value (BLOB/number) is malformed, never decoded as JSON
  text;
- warnings fire ONLY for real malformed persisted data: a valid empty list
  (`[]`) and a missing row are normal state — never logged as corruption
  (M6-FINAL-DECODE-LOGGING-MICROFIX);
- NO WRITEBACK during load (read tolerance, not repair — same philosophy as
  M11.2C);
- malformed rows are still compared RAW by provenance (provenance answers
  "did the candidate originate from the trusted LKG?"; semantic load safety
  is owned by the repository decoders — PROVENANCE ≠ SEMANTIC VALIDATION).

**Required vs optional authoritative tables** — `_AUTHORITATIVE_TABLES` is
`("settings", "library_prefs")`; `_OPTIONAL_AUTHORITATIVE_TABLES` is
`{"library_prefs"}` (pre-M6 compatibility: absent == empty). A missing
REQUIRED table (`settings`) makes the authoritative read raise and the
candidate provenance FAIL CLOSED — a settings-less database is never
treated as an empty settings database. Future authoritative tables must be
added to `_AUTHORITATIVE_TABLES` AND declared optional explicitly if
pre-existing databases may lack them (optionality is never implicit).

## Library Filesystem Boundary

`LibraryService` → `LibraryScannerPort` → `FilesystemLibraryScanner`. Filesystem authority is infrastructure: application code never calls `Path.exists`/`is_file`/`stat`/`os.stat`/`os.access` for runtime authority. Missing and empty directories are distinct (missing raises a typed `LibraryFilesystemError`; a valid empty directory returns `[]`). Scan failures preserve the last valid library state and publish a typed `LibraryDiagnostic` (DIRECTORY_MISSING / ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE). Same-directory rescans reconcile stale entries (STALE_ENTRIES_REMOVED + affected_count). Activation validates the selected `TrackRef` through the port before any queue mutation: TRACK_MISSING removes the exact reference and never reaches the queue; ACCESS/IO/UNKNOWN preserve the entry. Diagnostics are typed state owned by `LibraryState`; presentation (bridge/QML) only projects them. No continuous filesystem watcher exists. **Async ownership (M6-AUTHORITATIVE-DATA-DECODE-GATE correction): M6 owns async scanning, incremental scanning, cancellation, supersession, progress and owner-thread commit (TD-009 resolved by M6.4); M12 owns profiling, performance tuning, memory optimization, startup optimization, the 10k performance target and index-hydration optimization (instant canonical Library from the persisted index + async filesystem reconciliation — classified POST-M6 / M12, NOT implemented).**

Library preferences (favorites, play history, recently added) are REFERENCE PERSISTENCE: they survive library membership changes and temporary filesystem unavailability, and are never erased by scans, missing-track removal, or scan failures. Current library membership is `LibraryState.tracks`; missing files fall out of the derived views but not of the persisted references (TD-013 activation only removes the stale membership entry).

## Lifecycle

`ApplicationContainer` (bootstrap) owns the lifecycle: construct the object graph → start services → run the QML engine → shutdown.

- **Startup (current)**: create QGuiApplication; `SQLiteSettingsRepository.open_for_startup(db_path)` runs the read-only persistence health preflight before any writable repository or backend construction; then build components, load settings through `SettingsService`, register bridges, load `main.qml`.
- **Startup persistence flow (M11.2D + M11.2E, TESTED)**: inspect → M11.2D deterministic routing → M11.2E automatic recovery for explicitly recoverable states (validated LKG → validated/trusted candidate → quarantine original artifacts → atomic install → installed-primary health verification → writable repository) → START. Quarantine is evidence only, never a recovery source.
- **Runtime**: single UI thread; services mutate their state models synchronously (no worker threads in current scope).
- **Shutdown**: best-effort; every component's shutdown is attempted, and cleanup continues after failures. The first exception is retained and re-raised; subsequent exceptions do not replace it and are not currently accumulated or logged.
- Explicit ownership: the container holds all long-lived objects; no global service locators or singletons.

## Error Propagation Principles

- **No swallowed exceptions**: failures are either propagated explicitly or classified and surfaced; silent `except: pass` is prohibited.
- **Runtime side-effect failures use exceptions**: PlaybackService operations (play/pause/seek/load) may raise through the AudioPort boundary; state mutation occurs only after a successful side effect where atomicity is defined.
- **Typed diagnostics for persistence**: persistence failures carry a `PersistenceHealth` value plus a human-readable message; never a bare boolean.
- **First-error-wins at shutdown**: the first shutdown failure is re-raised as the dominant result; later failures do not replace it and are not currently retained.
- **Field-level malformed-data recovery (M11.2C, TESTED)**: `load()` decodes each persisted field independently — a malformed value falls back to its domain default with one logged warning, valid sibling fields are preserved, and no value is silently coerced or written back. `load()` tolerance is safe read fallback, not database health: `inspect_path()` still reports `MALFORMED_DATA` for the same content, and the startup reaction to that distinction is M11.2D.

## Fitness Evidence

| Check          | Assertion                                                                                  | Status                                                                      |
| -------------- | ------------------------------------------------------------------------------------------ | --------------------------------------------------------------------------- |
| Layering       | `domain/` and `application/` import no Qt; `presentation/` never imports `infrastructure/` | Enforced by convention; no automated import-guard test yet (documented gap) |
| Ownership      | One owner per state model per ADR 0003                                                     | Per-service and coordinator tests                                           |
| Audio boundary | Services depend on `AudioPort` ABC only                                                    | Verified                                                                    |
| Persistence    | M11.2A read-only health inspection + M11.2B validated LKG backup / staged recovery         | M11.2A + M11.2B capability tested; M11.2D startup preflight TESTED and wired in production (terminal states block, never LKG fallback); M11.2E automatic restore + quarantine TESTED |
| Tests          | Full suite passes; CI green (lint/test/build, offscreen) — test counts are derived evidence and are not copied into secondary documents | Verified                                                                    |
| QML boundary   | QML → bridges → services only                                                              | Verified (M9 QML tests)                                                     |

## ADR Index

| ADR  | Decision                                          | File                                           |
| ---- | ------------------------------------------------- | ---------------------------------------------- |
| 0001 | Python 3.11+ with PySide6 / Qt 6 stack            | `docs/adr/0001-python-pyside6-stack.md`        |
| 0002 | Four-layer architecture with dependency inversion | `docs/adr/0002-layered-architecture.md`        |
| 0003 | Single state owner per domain model               | `docs/adr/0003-single-state-owner.md`          |
| 0004 | QML bridge boundary                               | `docs/adr/0004-qml-bridge-boundary.md`         |
| 0005 | SQLite settings persistence with health detection | `docs/adr/0005-sqlite-settings-persistence.md` |
| 0006 | Legacy is evidence only                           | `docs/adr/0006-legacy-evidence-only.md`        |
