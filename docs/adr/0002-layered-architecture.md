# ADR 0002: Four-layer architecture with dependency inversion

## Title

Four-layer architecture: domain, application, infrastructure, presentation, wired by a bootstrap composition root. Dependencies flow inward.

## Date

2026-08-12

## Context

The rebuild needed a structure that keeps pure logic testable without Qt, isolates I/O (audio, filesystem, SQLite) behind interfaces, and gives the QML layer a thin, translation-only role. The superseded clean-rebuild governance draft already targeted this shape (Proposed draft ADRs D2/D3/D4); this ADR re-applies that shape to the Python/PySide6 stack.

## Decision

The codebase is organized into four layers plus a composition root:

- **domain/** — pure Python, no Qt, no I/O. State models and rules: `PlaybackState` (+`PlaybackStatus`), `QueueState`, `LibraryState` (+`TrackRef`), `SettingsState`, `AppRoute`/`NavigationState`, `PersistenceHealth`/`PersistenceDiagnostic`.
- **application/** — use cases and ports. Ports (`AudioPort`, `SettingsRepository`, `LibraryScannerPort`) are abstract; services (`PlaybackService`, `QueueService`, `LibraryService`, `NavigationService`, `SettingsService`) and coordinators (`PlaybackCoordinator`, `LibraryPreferencesCoordinator`) implement behavior against domain state.
- **infrastructure/** — concrete adapters implementing application ports: `QtMultimediaBackend` (AudioPort), `FilesystemLibraryScanner` (LibraryScannerPort), `SQLiteSettingsRepository` (SettingsRepository, with persistence health detection).
- **presentation/** — QML plus bridges (`PlaybackBridge`, `QueueBridge`, `LibraryBridge`, `NavigationBridge`, `SettingsBridge`). Bridges translate intents into service calls and expose read-only state projections to QML. No business rules live here.
- **bootstrap/** — `ApplicationContainer`, the composition root. Constructs every component with explicit dependency wiring, owns lifecycle, performs best-effort shutdown with first-error-wins.

Dependency direction is strictly inward: `presentation → application → domain`, and `infrastructure → application` (implementing its ports). Domain depends on nothing. Infrastructure never calls into presentation. The bootstrap layer is the only place allowed to construct infrastructure and presentation together.

## Consequences

- Domain and application are testable with pytest without a Qt event loop (pure-Python unit tests).
- Replacing the audio backend or the settings storage requires changing infrastructure only, behind the same ports.
- The layering invariant is convention-enforced; tests assert that domain/application modules import no Qt symbols.
- Any new capability must decide which layer owns it before implementation; the layer graph is the contract.

## Alternatives considered

- **Three layers (domain merged into application)**: fewer files, but state would be entangled with use-case orchestration and harder to test in isolation. Rejected.
- **Framework-first (everything QObject-based)**: fastest to prototype QML wiring, but leaks Qt into business logic and blocks pure-pytest testing. Rejected.
- **No composition root (service locator / singletons)**: global state hides dependencies and complicates lifecycle. Rejected in favor of explicit wiring in bootstrap.

## Status

Accepted
