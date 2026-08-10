# Architecture Specification

## Purpose

Boundary and decision authorities for the Michi Music Player architecture. Owns ten open dimensions routed to `docs/ARCHITECTURE.md` and the ADR directory `docs/adr/`. All dimensions remain undecided — this spec defines what must be decided, not the decisions themselves.

## Requirements

### Requirement: Architecture Dimensions

The system MUST define ten architecture dimensions in `docs/ARCHITECTURE.md`, each explicitly labeled open for autonomous Design:

| ID | Dimension | Scope |
|----|-----------|-------|
| D1 | Language/Runtime | Programming language(s), runtime, toolchain |
| D2 | Layers | Logical and physical layering of the system |
| D3 | State Authorities | Single source of truth per application-state category |
| D4 | Composition | How components, services, and modules are assembled |
| D5 | Lifecycle | Startup, shutdown, pause, resume, backgrounding |
| D6 | Concurrency | Threading model, event loops, async boundaries |
| D7 | UI Boundary | Interface contract between backend and frontend |
| D8 | Audio Port | Audio I/O abstraction, codec responsibility, buffer management |
| D9 | Persistence | Storage strategy for settings, cache, and user data |
| D10 | Errors/Effects | Error propagation, effect tracking, recovery model |

Each dimension MUST remain open — no mechanism, library, or pattern SHALL be selected during M0. The document MUST state "open for autonomous Design" adjacent to each dimension.

#### Scenario: Dimension openness

- GIVEN the `docs/ARCHITECTURE.md` document
- WHEN any D1–D10 dimension is inspected
- THEN no mechanism, library, or framework is selected

#### Scenario: Dimension completeness

- GIVEN the document
- WHEN all dimensions are counted
- THEN exactly ten are present and labeled D1 through D10

### Requirement: Architecture Invariants

The system MUST declare architecture invariants in `docs/ARCHITECTURE.md` — constraints that SHALL survive every subsequent design decision. Invariants MUST include: the documentation-only nature of M0, the separation of D1–D10 decisions from M0 deliverables, and the rule that no D-dimension MAY close without an ADR.

#### Scenario: Invariant enforcement

- GIVEN any proposed D-dimension closure
- WHEN no corresponding ADR exists
- THEN the closure SHALL NOT be accepted

### Requirement: ADR Directory

The system MUST maintain `docs/adr/` as the canonical decision record directory. Every architecture decision that closes a D-dimension or modifies an invariant MUST produce an ADR with: title, status, context, decision, consequences, and date. The directory SHALL contain only new v2 decisions; no Legacy ADR file or mechanism SHALL be reused or copied.

#### Scenario: New ADR creation

- GIVEN a design decision that closes a D-dimension
- WHEN the ADR is written
- THEN it includes all six required fields

#### Scenario: Legacy ADR exclusion

- GIVEN Legacy ADR files exist
- WHEN `docs/adr/` is inspected
- THEN zero Legacy files are present
