# ADR 0003: Single state owner per domain model

## Title

Each domain state model has exactly one owning service; every mutation routes through that owner.

## Date

2026-08-12

## Context

Early implementations of a music player tend to accumulate scattered mutations: the UI toggles playback flags, the queue helper reorders items, and a settings writer overwrites preferences — producing divergent state and untestable behavior. The rebuild needs a canonical writer for each state category so that state transitions are predictable, auditable, and testable in isolation.

## Decision

Each domain model has exactly one owner at the application layer:

| State model | Owner |
| --- | --- |
| `PlaybackState` | `PlaybackService` |
| `QueueState` | `QueueService` |
| `LibraryState` | `LibraryService` |
| `SettingsState` | `SettingsService` |
| `NavigationState` (`AppRoute`) | `NavigationService` |

- The owner is the only component that mutates its model. All other components call owner methods (use cases) to request changes.
- `PlaybackCoordinator` composes `PlaybackService` and `QueueService` for cross-cutting flows (queue auto-advance) but does not mutate either state directly — it drives the owners through their public APIs.
- `LibraryPreferencesCoordinator` links `LibraryService` and `SettingsService` (persisting `last_directory` on scan) through public APIs only.
- Bootstrap never mutates domain state directly; it configures owners via their public interfaces.
- Owners expose read-only projections (snapshots) for the presentation bridges; projections are never written back.

## Consequences

- State transitions are centralized: debugging a playback bug means reading one service, not tracing UI writes.
- Unit tests exercise each owner against pure domain models without Qt.
- Cross-cutting behavior is confined to named coordinators, keeping individual services focused.
- New state categories require a new owner decision; ad-hoc state kept outside the ownership table is a review failure.

## Alternatives considered

- **State owned by the bridge layer (presentation)**: closest to the UI, but state dies with the UI and cannot be tested headlessly. Rejected.
- **Event-sourced / reducer-style global store**: stronger history guarantees, but disproportionate complexity for a single-user desktop player. Rejected.
- **Shared mutable models with multiple writers**: fastest to write initially, but produces the divergent-state bugs this decision exists to prevent. Rejected.

## Status

Accepted
