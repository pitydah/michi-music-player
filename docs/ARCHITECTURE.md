# Architecture

Authority for system boundaries, layer contracts, state ownership, lifecycle, and error semantics. All architectural decisions are recorded as Accepted ADRs in `docs/adr/`. This document aggregates them into one read-optimized reference.

## Stack

Python 3.11+, PySide6 (Qt 6, Qt Multimedia with FFmpeg backend), QML, SQLite (WAL). Build with setuptools (`python -m build`); tests with pytest; lint/format with Ruff; CI on GitHub Actions (lint, tests with `QT_QPA_PLATFORM=offscreen`, build). No C++ anywhere, no native-code build system, no GStreamer integration. (ADR 0001)

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
| `presentation/`   | `PlaybackBridge`, `QueueBridge`, `LibraryBridge`, `NavigationBridge`, `SettingsBridge` (read-only); QML: `main.qml`, `qml/theme/` MichiTheme, `qml/ui/` MichiButton/MichiPanel/MichiSlider/MichiTextField, `qml/shell/` AppShell/Sidebar/ContentHost, `qml/views/` NowPlaying/Library/Queue/Settings | application (services), domain (observed state), PySide6 | infrastructure                   |
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
| `PersistenceHealth` (diagnostic, read-only) | produced by `SQLiteSettingsRepository.inspect_path()`; current production consumer: `SQLiteSettingsRepository.open_for_startup()` (M11.2D TESTED) | `domain/persistence_health.py` |

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

## AudioPort Boundary

`AudioPort` (ABC in `application/ports.py`) is the audio contract. `QtMultimediaBackend` (infrastructure) implements it with Qt Multimedia (FFmpeg backend).

Operations: `load`, `play`, `pause`, `resume`, `stop`, `set_volume`, `set_muted`, `seek`, `position`, `duration`, plus end-of-media, position-changed, duration-changed, and error subscription callbacks.

- Application services depend on the port only; they never import PySide6 multimedia classes.
- The backend translates Qt signals into plain callbacks; services stay Qt-free.
- A fake backend substitutes the port in pure-pytest tests.

## SettingsRepository Boundary

`SettingsRepository` (ABC) is the persistence contract. `SQLiteSettingsRepository` (infrastructure) implements it against a single SQLite database (WAL) in the platform app-data directory.

- `SettingsService` is the only caller of repository mutations.
- The read-only health-detection capability (`inspect_path`, extended-result-code normalization) is implemented and unit-tested (M11.2A), producing a `PersistenceHealth` classification: MISSING, HEALTHY, CORRUPT_DATABASE, MALFORMED_DATA, LOCKED, ACCESS_FAILURE, IO_FAILURE, UNKNOWN_FAILURE. Inspection never mutates the file.
- Current vs target: the read-only inspection IS wired into startup via `SQLiteSettingsRepository.open_for_startup()` (M11.2D, TESTED) — preflight runs before any writable repository construction and before backend construction.
- M11.2B (TESTED, capability only): `SQLiteSettingsRepository` exposes `last_known_good_path` (`<db>.lkg`), `refresh_last_known_good` (only a HEALTHY primary may refresh; SQLite backup API from a read-only source; unique sibling temp candidate validated before atomic `os.replace` promotion; an existing LKG is preserved for all failures occurring before successful atomic promotion — a candidate is validated before `os.replace()`, so only a validated SQLite snapshot is promoted) and `stage_recovery_from_last_known_good` (healthy-LKG-only source; SQLite backup API into an exclusively reserved new destination — `O_CREAT | O_EXCL` — validated before success; `FileExistsError` on existing destinations; `ValueError` on primary/LKG aliases; foreign files never overwritten or deleted; primary and LKG never mutated).
- M11.2C (TESTED): field-level malformed-data recovery. `load()` decodes each persisted field independently; a malformed value falls back to its domain default with one logged warning while valid sibling fields are preserved; no field is silently coerced; nothing is written back to SQLite (safe read fallback, not repair). Canonical persisted `muted` representation is `"true"`/`"false"` (as written by `save()`), and `load()` and `inspect_path()` agree on it. The health classifier remains strict: a database containing malformed data still reports `MALFORMED_DATA` even though `load()` can produce a safe `SettingsState` — load tolerance is not database health.
- M11.2D (TESTED): startup preflight + recovery routing. `ApplicationContainer` calls `SQLiteSettingsRepository.open_for_startup(db_path)` before `QtMultimediaBackend` construction; the classmethod reads health first (READ FIRST, DECIDE SECOND, WRITE ONLY WHEN AUTHORIZED): HEALTHY → best-effort LKG refresh then writable open; MISSING with no recovery material → true first run (create + validate); MISSING with LKG/candidate → staged recovery into `<db>.recovery` (never installed); field-level MALFORMED_DATA (read-only structural probe passes) → writable open of the same primary, M11.2C fallback applies; structural MALFORMED/CORRUPT → recovery staging only; LOCKED/ACCESS_FAILURE/IO_FAILURE/UNKNOWN_FAILURE → `PersistenceStartupError`, no fallback, no staging, no writable open. The primary is never replaced, renamed, deleted, or repaired; staged candidates are never installed. For an initially MALFORMED_DATA primary, structural readability is probed read-only: genuine schema malformation routes to non-destructive recovery staging, while environmental/operational failures during that probe are reclassified through the existing persistence-health taxonomy — LOCKED / ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE block startup and never trigger LKG fallback.
- Conservative handling: HEALTHY/MISSING proceed to normal flow; all failure classes produce an explicit diagnostic with no silent fallback and no destructive repair. Remaining recovery work (automatic restore policy, quarantine, M11.2E) is future capability that will build on this taxonomy.
- Persisted fields: volume, muted, last_directory, recent_files. Restart gate: values apply only after a successful restart restore.

## Lifecycle

`ApplicationContainer` (bootstrap) owns the lifecycle: construct the object graph → start services → run the QML engine → shutdown.

- **Startup (current)**: create QGuiApplication; `SQLiteSettingsRepository.open_for_startup(db_path)` runs the read-only persistence health preflight before any writable repository or backend construction; then build components, load settings through `SettingsService`, register bridges, load `main.qml`.
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
| Persistence    | M11.2A read-only health inspection + M11.2B validated LKG backup / staged recovery         | M11.2A + M11.2B capability tested; M11.2D startup preflight TESTED and wired in production (terminal states block, never LKG fallback) |
| Tests          | 334 pytest tests passing; CI green (lint/test/build, offscreen)                            | Verified                                                                    |
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
