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

| Layer | Contents | May import | Forbidden |
| --- | --- | --- | --- |
| `domain/` | `PlaybackState`, `QueueState`, `LibraryState` (+`TrackRef`), `SettingsState`, `AppRoute`/`NavigationState`, `PersistenceHealth` | Python stdlib only | Qt, I/O, application |
| `application/` | Ports: `AudioPort`, `SettingsRepository`, `LibraryScannerPort`. Services: `PlaybackService`, `QueueService`, `LibraryService`, `NavigationService`, `SettingsService`. Coordinators: `PlaybackCoordinator`, `LibraryPreferencesCoordinator` | domain | Qt, infrastructure, presentation |
| `infrastructure/` | `QtMultimediaBackend`, `FilesystemLibraryScanner`, `SQLiteSettingsRepository` (+ `inspect_path` health detection) | application (ports), domain, PySide6, SQLite, filesystem | presentation |
| `presentation/` | `PlaybackBridge`, `QueueBridge`, `LibraryBridge`, `NavigationBridge`, `SettingsBridge` (read-only); QML: `main.qml`, `qml/theme/` MichiTheme, `qml/ui/` MichiButton/MichiPanel/MichiSlider/MichiTextField, `qml/shell/` AppShell/Sidebar/ContentHost, `qml/views/` NowPlaying/Library/Queue/Settings | application (services), domain (snapshots), PySide6 | infrastructure |
| `bootstrap/` | `ApplicationContainer` composition root | everything (the only layer allowed to) | — |

Rules:

- Dependencies flow inward: `presentation → application → domain`; `infrastructure → application` implements ports.
- `domain/` has no outward dependencies and no Qt imports.
- `infrastructure` never calls `presentation`; `presentation` never calls `infrastructure`.
- `bootstrap` is the only place that constructs infrastructure and presentation together.

## State Ownership

Exactly one service owns each state model. Every mutation routes through the owner (ADR 0003).

| State model | Owner (application layer) | Location |
| --- | --- | --- |
| `PlaybackState` | `PlaybackService` | `domain/playback.py` |
| `QueueState` | `QueueService` | `domain/queue.py` |
| `LibraryState` (+ `TrackRef`) | `LibraryService` | `domain/library.py` |
| `SettingsState` | `SettingsService` | `domain/settings.py` |
| `AppRoute` / `NavigationState` | `NavigationService` | `domain/navigation.py` |
| `PersistenceHealth` (diagnostic, read-only) | produced by infrastructure inspection, consumed by `SettingsService`/bootstrap | `domain/persistence_health.py` |

- **Ingress rule**: no subsystem writes to a state model directly; all mutations are owner method calls.
- **Coordinator rule**: `PlaybackCoordinator` composes `PlaybackService` + `QueueService` for cross-cutting flows (auto-advance, play_index) and `LibraryPreferencesCoordinator` composes `LibraryService` + `SettingsService` (`last_directory`). Coordinators drive owners through public APIs; they never mutate state directly.
- **Projection rule**: owners expose read-only snapshots consumed by bridges for QML. Projections are never written back.
- Bootstrap configures owners through public APIs only; it never mutates domain state.

## QML Bridge Boundary

QML never touches services or domain objects directly (ADR 0004).

```
QML                     Bridge (presentation)            Application
──                      ───────────────────────          ───────────
MichiButton.clicked  →  bridge.on_play_clicked()      →  PlaybackService.play()
Label text           ←  bridge.title (property)       ←  PlaybackState snapshot
```

- **Intents**: QML signals call bridge methods; bridges translate to service/coordinator calls. Bridges hold no business rules.
- **Projections**: bridges expose read-only properties backed by owner snapshots.
- **Read-only settings**: `SettingsBridge` exposes state for display only; settings mutations go through `SettingsService` (bootstrap/coordinators), never through QML.
- Bridges are the only place Qt types and application concepts meet.

## AudioPort Boundary

`AudioPort` (ABC in `application/ports.py`) is the audio contract. `QtMultimediaBackend` (infrastructure) implements it with Qt Multimedia (FFmpeg backend).

Operations: `load`, `play`, `pause`, `resume`, `stop`, `set_volume`, `set_muted`, `seek`, `position`, `duration`, plus end-of-media and position-changed subscription callbacks.

- Application services depend on the port only; they never import PySide6 multimedia classes.
- The backend translates Qt signals into plain callbacks; services stay Qt-free.
- A fake backend substitutes the port in pure-pytest tests.

## SettingsRepository Boundary

`SettingsRepository` (ABC) is the persistence contract. `SQLiteSettingsRepository` (infrastructure) implements it against a single SQLite database (WAL) in the platform app-data directory.

- `SettingsService` is the only caller of repository mutations.
- Startup runs read-only `inspect_path` **before any write**, producing a `PersistenceHealth` classification: MISSING, HEALTHY, CORRUPT_DATABASE, MALFORMED_DATA, LOCKED, ACCESS_FAILURE, IO_FAILURE, UNKNOWN_FAILURE.
- Conservative handling: HEALTHY/MISSING proceed to normal flow; all failure classes produce an explicit diagnostic with no silent fallback and no destructive repair. Repair/recovery (M11.2B-E) is a future capability that will build on this taxonomy.
- Persisted fields: volume, muted, last_directory, recent_files. Restart gate: values apply only after a successful restart restore.

## Lifecycle

`ApplicationContainer` (bootstrap) owns the lifecycle: construct the object graph → start services → run the QML engine → shutdown.

- **Startup**: create QGuiApplication, build all components with explicit constructor wiring, run read-only persistence health inspection, load settings through `SettingsService`, register bridges as QML context properties, load `main.qml`.
- **Runtime**: single UI thread; services mutate their state models synchronously (no worker threads in current scope).
- **Shutdown**: best-effort; every component's shutdown is attempted, and failures are collected. First error wins the shutdown result; subsequent errors are still attempted and logged, never swallowed silently.
- Explicit ownership: the container holds all long-lived objects; no global service locators or singletons.

## Error Propagation Principles

- **No silent exceptions**: every expected failure path is caught, classified, and surfaced (service result, typed diagnostic, or logged shutdown error).
- **First-error-wins at shutdown**: the first shutdown failure is reported as the dominant result; later failures are recorded but do not mask it.
- **Typed diagnostics**: persistence failures carry a `PersistenceHealth` value plus a human-readable message; never a bare boolean.
- **No silent fallback**: a failed load does not quietly continue with default state; the failure is explicit to the user and to the caller.
- Errors cross layers by value (results/diagnostics), not by Qt signals or exceptions leaking through ports.

## Fitness Evidence

| Check | Assertion | Status |
| --- | --- | --- |
| Layering | `domain/` and `application/` import no Qt; `presentation/` never imports `infrastructure/` | Enforced by convention + tests |
| Ownership | One owner per state model per ADR 0003 | Verified in code review |
| Audio boundary | Services depend on `AudioPort` ABC only | Verified |
| Persistence | Read-only inspection before write; conservative taxonomy | Tested (M11.2A) |
| Tests | 154 pytest tests passing; CI green (lint/test/build, offscreen) | Verified |
| QML boundary | QML → bridges → services only | Verified |

## ADR Index

| ADR | Decision | File |
| --- | --- | --- |
| 0001 | Python 3.11+ with PySide6 / Qt 6 stack | `docs/adr/0001-python-pyside6-stack.md` |
| 0002 | Four-layer architecture with dependency inversion | `docs/adr/0002-layered-architecture.md` |
| 0003 | Single state owner per domain model | `docs/adr/0003-single-state-owner.md` |
| 0004 | QML bridge boundary | `docs/adr/0004-qml-bridge-boundary.md` |
| 0005 | SQLite settings persistence with health detection | `docs/adr/0005-sqlite-settings-persistence.md` |
| 0006 | Legacy is evidence only | `docs/adr/0006-legacy-evidence-only.md` |
