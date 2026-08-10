# Design: M0 Foundation v2

## Technical Approach

M0 is documentation-only. D1-D10 are resolved autonomously as Proposed ADR drafts. Domain/Application use C++20 without Qt; Qt 6 stays in Infrastructure, Presentation, and bootstrap. Later milestones select tooling and backends.

## Proposed ADRs

**D1: C++20 Domain Core, Qt 6 Infrastructure** (2026-08-10, Proposed) — Context: portable core independent of UI framework. Decision: C++20 for Domain/Application without Qt; Qt 6 only in Infrastructure/Presentation/bootstrap. Consequences: Domain compiles without Qt; build enforces boundary. Alternatives: pure Qt rejected for coupling; Rust rejected for QML interop gaps.

**D2: Four-Layer Architecture, Inward Dependencies** (2026-08-10, Proposed) — Context: protect domain purity. Decision: Presentation→Application→Domain, Infrastructure inward implementing Application ports. Compile: Presentation→Application, Infrastructure→Application ports, Application→Domain, Domain→no outward deps. Consequences: Domain unaware of I/O or UI. Alternatives: three-layer rejected for forcing orchestration into domain.

**D3: Five Canonical State Authorities** (2026-08-10, Proposed) — Context: state duplication produces divergence. Decision: PlaybackState, QueueState, LibraryState, SettingsState, ApplicationState. UI projections are disposable read-only views. Consequences: one truth per category; mutations route through Application. Alternatives: distributed state rejected for consistency; monolithic rejected for coupling.

**D4: Composition Root, Constructor Injection** (2026-08-10, Proposed) — Context: implicit wiring hides dependencies. Decision: bootstrap composition root wires full object graph via constructor injection; no locator, singleton, or God. Consequences: all deps visible; any substitutable for testing. Alternatives: singleton rejected for hidden deps; locator rejected for runtime ambiguity.

**D5: Asynchronous Lifecycle, Bounded Shutdown** (2026-08-10, Proposed) — Context: handle platform pause/resume and clean teardown. Decision: Bootstrap→Init→Create→Running⇄Pause→ShuttingDown→Stopped. Init async before Running. Pause cancels nonessential work, preserves state; resume reacquires. ShuttingDown cancels, persists, verifies, stops workers within deadlines; UI never blocks. Failure records diagnostics, reaches Stopped. Alternatives: sync shutdown rejected for UI stalls.

**D6: Application Executor Port, Worker Pool** (2026-08-10, Proposed) — Context: async work must not block UI or leak threads into Domain. Decision: Application owns cancellable executor port; Infrastructure provides bounded worker pool; Domain mutations only on UI/main thread; workers return immutable results via main-thread callbacks. Consequences: Domain lock-free; I/O isolated. Alternatives: internal threading rejected for lock complexity.

**D7: QML Intent, Read-Only State Boundary** (2026-08-10, Proposed) — Context: QML must not leak into Application. Decision: QML sends intent, receives read-only projections. Q_PROPERTY, signals, Q_INVOKABLE only in Presentation adapters. Application exposes plain C++ ports. Consequences: Application testable without QML; adapters are thin layers. Alternatives: direct QML access rejected for testability.

**D8: Application-Owned IAudioEngine Port** (2026-08-10, Proposed) — Context: backend selection locks codecs and platform deps early. Decision: Application owns IAudioEngine port (play, pause, seek, stop, volume); backend, codecs, buffers deferred to M2. Consequences: M0-M1 test against port; M2 selects backend without Application changes. Alternatives: selecting now rejected for premature coupling.

**D9: Application-Owned Persistence Ports, Domain Unaware** (2026-08-10, Proposed) — Context: storage constrains future upgrades. Decision: Application owns persistence ports; Domain unaware of storage. Settings use JSON key-value schema; app data uses SQLite with versioned migrations. Consequences: backends swappable; schema evolution explicit; domain not DB-coupled. Alternatives: opaque file rejected for query complexity.

**D10: Verified Command/Effect Pipeline** (2026-08-10, Proposed) — Context: multi-effect ops must not claim success before effect verification. Decision: prepare→execute→verify→publish pipeline. Single-effect: prepare, execute compensable effect, verify, commit, publish. Multi-effect: prepare all, execute compensables, verify all, commit, publish once. Never publish before all-effect verification. Partial failure compensates or idempotently reconciles; publishes honest failure, never stale success. Consequences: no fake atomicity. Alternatives: two-phase commit rejected for non-transactional systems.

## Dependency Views

Compile time:

```
Presentation → Application
Infrastructure → Application ports
Application → Domain
Domain → no outward dependencies
```

Runtime:

```
Presentation intent → Application → Domain mutation
Application → port → Infrastructure effect
Application projection → Presentation
```

## ADR Dependency Sequence

`D1 → D3/D4 → D2/D5/D6 → D7/D9/D10 → D8`

## Fitness Gates

| Check           | Assertion                                                                                                                             |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Boundaries      | Four compile arrows; no Qt in Domain/Application; no QML outside Presentation                                                         |
| State/Lifecycle | Five canonical authorities; lifecycle graph complete; main-thread mutation; cancellation/shutdown deadlines                           |
| Scope           | Exactly 11 paths; README links all governance; .gitignore stack-neutral; reject all 22 exclusions                                     |
| Governance      | M0-M16 ten roadmap fields; Component/WP states; DoR/DoD/Golden Path; invariants; six debt fields; D1-D10 "open for autonomous Design" |
| Legacy          | 17 ledger fields; one classification; named SPLIT children; v2-over-Legacy; WP-state binding; zero copies; ref `63914a00`             |
| ADR/Effects     | Ten ADRs, seven fields, Proposed; selective sequence; effect verification before publish; partial failure compensation                |
| Parity          | Byte-compare normalized `design.md` with Engram `sdd/m0-foundation-v2/design`                                                         |

## Open Implementation Decisions

Concrete executor and thread pool sizing; worker pool capacity and rejection strategy; JSON settings schema; SQLite migration framework; audio backend candidates for M2; shutdown timeout values; cancellation granularity within effects.

## Migration / Rollout

No data migration. Apply creates documentation artifacts. Revert removes all 11 paths before M1. Threat matrix: N/A — M0 runs no product process.
