# Design: M0 Foundation v2

## Technical Approach

M0 is documentation-only. D1-D10 are Proposed drafts. Domain/Application use C++20 without Qt; Qt 6 stays in Infrastructure, Presentation, and bootstrap. Later milestones select tooling, audio, and persistence.

## Proposed ADR Drafts

| ID | Draft recommendation | Rationale | Status |
|---|---|---|---|
| D1 | C++20; Qt 6 only outside Domain/Application | Portable core without an arbitrary Qt floor | Proposed |
| D2 | Domain, Application, Infrastructure, Presentation; inward compile dependencies | Keeps policy independent from frameworks and I/O | Proposed |
| D3 | Playback, Queue, Library, Settings, and Application state are the five canonical authorities; UI projections are disposable | One truth per state category | Proposed |
| D4 | Bootstrap composition root, explicit wiring, constructor injection; no globals/locator | Makes the object graph visible and replaceable | Proposed |
| D5 | Explicit asynchronous lifecycle below | Prevents UI stalls and ambiguous teardown | Proposed |
| D6 | Application-owned cancellable ExecutorPort; Infrastructure worker pool; Domain mutations on UI/main thread | Keeps Qt/threading out of policy and Domain lock-free | Proposed |
| D7 | Q_PROPERTY, signals, and Q_INVOKABLE only in Presentation adapters; Application exposes plain C++ ports/results | Keeps QML replaceable and Application testable | Proposed |
| D8 | Application-owned AudioEnginePort; backend/codecs/buffers deferred to M2 Infrastructure | Avoids premature backend coupling | Proposed |
| D9 | Application-owned settings/cache/user-data ports; durable schema deferred to M5 | Preserves storage substitution and recovery design space | Proposed |
| D10 | Verified command/effect transaction below | Prevents stale success and fake cross-system atomicity | Proposed |

Each ADR MUST contain exactly seven distinct fields: Title, Date, Context, Decision, Consequences, Alternatives considered, Status. Date replaces none; Status stays Proposed until acceptance.

## Dependency And Runtime Views

Compile time only:

```text
Presentation -> Application
Infrastructure -> Application ports
Application -> Domain
Domain -> no outward dependencies
```

Runtime only:

```text
Presentation intent -> Application -> Domain mutation
Application -> port -> Infrastructure effect
Application projection -> Presentation
```

## Lifecycle And Concurrency

`Created -> Initialized -> Running <-> Backgrounded/Suspended -> Running (resume) -> ShuttingDown -> Stopped`.

Initialization completes asynchronously before Running. Background/suspend cancels nonessential work, preserves state, and releases resources; resume reacquires and verifies. Shutdown asynchronously cancels, persists, verifies, and stops workers within stage/overall deadlines. The UI never joins or blocks. Failure records diagnostics and an idempotent recovery marker, reports degradation, abandons only noncritical work, and reaches Stopped; safety-critical failure forces controlled termination.

Domain is not thread-safe. Workers return immutable results through main-thread callbacks; only Application mutates Domain.

## Command/Effect Ordering

Single-effect operations prepare, execute a compensable/idempotent effect, verify it, commit canonical state, then publish once. Multi-effect operations prepare all effects, execute compensable effects, verify all, commit canonical state, then publish once. D10 never publishes before effect verification. Partial failure compensates or idempotently reconciles completed effects and publishes only an honest failure/degraded state, never stale success.

## ADR Dependency Sequence

Only this selective sequence is approved: `D1 -> D3/D4 -> D2/D5/D6 -> D7/D9/D10 -> D8`.

## Measurable Fitness Checks

Apply runs shell assertions; M1 automates the same criteria.

| Check | Executable/planned assertion |
|---|---|
| Boundaries | Parse diagrams/ADRs; allow exactly the four compile arrows above; reject Qt tokens in Domain/Application and QML API outside Presentation |
| State/lifecycle | Count exactly five authorities; graph-check every listed lifecycle edge, resume edge, main-thread mutation rule, cancellation, and shutdown deadlines |
| Scope | Assert exactly these 11 paths: `README.md`, `.gitignore`, `docs/MASTER_ROADMAP_1.0.md`, `docs/ARCHITECTURE.md`, `docs/INVARIANTS.md`, `docs/MIGRATION_LEDGER.md`, `docs/STATUS_MATRIX.md`, `docs/DEFINITION_OF_DONE.md`, `docs/TECHNICAL_DEBT_REGISTER.md`, `docs/POST_1_0_BACKLOG.md`, `docs/adr/`; require README links every governance authority and `.gitignore` contains only stack-neutral OS/editor/environment patterns; reject code/tests/build/src/qml and all 22 spec exclusions |
| Governance | Parse M0-M16; require exact ten roadmap fields and routed test layer/scope/coverage; require exact Component/WP labels/transitions, DoR/DoD, Golden Path, invariants, six debt fields, backlog name/rationale; verify each D1-D10 says "open for autonomous Design" and architecture invariants require documentation-only M0, decisions outside deliverables, and ADR-backed closure |
| Legacy | Parse exactly 17 ledger fields; one KEEP/ADAPT/SPLIT/REWRITE/DISCARD, named SPLIT children, exact evidence label, new-tests-only, and v2-over-Legacy conflict precedence; bind migration state exactly to BACKLOG/READY/IN_PROGRESS/REVIEW/VERIFY/BLOCKED/DONE/DEFERRED; prove zero copies by hashes/paths and bind sources to read-only Git `63914a00` |
| ADR/effects | Require ten ADRs, the seven-field format, Status Proposed, exact selective sequence, and model-check no publish precedes all-effect verification; inject partial failures to require compensation/reconciliation and honest state |
| Hybrid parity | Normalize line endings/trailing space, strip Engram metadata, then byte-compare `design.md` with Engram topic `sdd/m0-foundation-v2/design` |

## Migration / Threat Matrix

No migration; rollback deletes the 11 paths. Routing, shell, subprocess, VCS/PR automation, executable classification, and process integration are N/A: M0 runs no product process. Path and Git assertions validate documentation only.
