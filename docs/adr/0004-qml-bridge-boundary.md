# ADR 0004: QML bridge boundary

## Title

QML talks only to bridge objects; bridges translate intents to services and expose read-only projections.

## Date

2026-08-12

## Context

PySide6 lets QML reach deeply into Python objects if exposed indiscriminately. Without a boundary, QML bindings start performing business logic and mutating state directly, duplicating rules that live in the application layer. The boundary must keep QML declarative and dumb, and keep every side effect behind a service call.

## Decision

- QML components interact exclusively with bridge objects registered as context properties: `PlaybackBridge`, `QueueBridge`, `LibraryBridge`, `NavigationBridge`, `SettingsBridge`.
- **Intents**: QML signals and calls invoke bridge methods; bridges translate them into service/coordinator calls. Bridges contain no business rules.
- **Projections**: bridges expose state to QML as properties read from owner `.state` objects. Bridges treat owner state as read-only by convention; state objects are mutable references, not immutable snapshots (see ADR 0003). Projections are never written back into domain state.
- `SettingsBridge` is read-only; settings mutations happen only through `SettingsService` from bootstrap/coordinators (restart-gated persistence contract).
- QML stays in `presentation/`: `main.qml`, `qml/theme/` (MichiTheme), `qml/ui/` primitives (MichiButton, MichiPanel, MichiSlider, MichiTextField), `qml/shell/` (AppShell, Sidebar, ContentHost), `qml/views/` (NowPlaying, Library, Queue, Settings).

## Consequences

- QML is testable in isolation; bridge translation logic is unit-testable in pure pytest.
- Side effects have one path: QML → bridge → service. Grep-verifiable.
- Bridges are the only place where Qt objects and application-layer concepts meet, keeping PySide6 details out of services.
- Adding a new QML screen requires a bridge decision: either extend an existing bridge or add a new one with its own projection contract.

## Alternatives considered

- **Expose services directly to QML (via @Slot/@Property on services)**: fewer files, but business objects become QObject-coupled and untestable without Qt. Rejected.
- **QML reads a single global context object tree**: one big surface area, implicit coupling, and no clear ownership. Rejected.
- **Web channels / JSON-RPC to a separate process**: cleanest isolation, but grossly disproportionate for a local desktop player. Rejected.

## Status

Accepted
