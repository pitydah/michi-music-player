# Proposal: M0 Foundation v2

## Intent

Establish documentation-only foundation for from-scratch music player. Stack, architecture undecided; M0 produces no code, tests, build, QML, or runtime behaviour.

## Scope

### In

`README.md`; `.gitignore`; `docs/MASTER_ROADMAP_1.0.md`; `docs/ARCHITECTURE.md`; `docs/INVARIANTS.md`; `docs/MIGRATION_LEDGER.md`; `docs/STATUS_MATRIX.md`; `docs/DEFINITION_OF_DONE.md`; `docs/TECHNICAL_DEBT_REGISTER.md`; `docs/POST_1_0_BACKLOG.md`; `docs/adr/`.

### Out

playback; audio engine; queue; library; database; playlists; search; metadata editor; Audio Lab; Disc Lab; Michi AI; sync; NowPlaying; functional navigation; product QML; server integrations; home audio; recognition; radio; lyrics; Michi ecosystem features; video.

## Capabilities

### New

- `governance`: `docs/MASTER_ROADMAP_1.0.md` routes M0-M16, each with 10 fields: objective, scope, out-of-scope, dependencies, deliverables, new-test strategy, entry/exit criteria, acceptance gate, risks. `docs/MIGRATION_LEDGER.md` routes 17-field records. `docs/STATUS_MATRIX.md` routes component states (UNKNOWN→AUDITED→FUNCTIONAL→TESTED→STABLE→FROZEN; BROKEN, PARTIAL exceptional) and WP states (BACKLOG→READY→IN_PROGRESS→REVIEW→VERIFY→DONE; BLOCKED interrupt resumes prior; DEFERRED via scope-change only). `docs/DEFINITION_OF_DONE.md` routes DoR, DoD, Golden Path. `docs/INVARIANTS.md` routes P0/P1=0, feature freeze, WIP limits, baby steps, new-tests-only, freeze/reopen reasons.
- `architecture`: `docs/ARCHITECTURE.md` routes D1 language/runtime, D2 layers, D3 state authorities, D4 composition, D5 lifecycle, D6 concurrency, D7 QML boundary, D8 audio port, D9 persistence, D10 errors/effects. `docs/adr/` records decisions. All D1-D10 open; no mechanism preselected.
- `legacy-evidence`: `docs/MIGRATION_LEDGER.md` routes 17 fields: ID, capability/responsibility, Legacy source, functional description, Legacy state, Legacy dependencies, known problems, decision, justification, new destination, new contract, Legacy tests found (reference only), new tests required, migration state, risks, technical debt, frozen. One KEEP, ADAPT, SPLIT, REWRITE, DISCARD per responsibility. KEEP never copies; SPLIT requires named children. `LEGACY EVIDENCE` labels (individual/section-scoped) mark non-authoritative evidence; v2 specifications prevail. Legacy tests are reference-only, never executed.

### Modified

None.

## Approach

ADR-first, contract-indexed. One obligation, one owner. Documentation-verifiable; zero runtime.

## Affected Areas

| Path                              | Impact                |
| --------------------------------- | --------------------- |
| `README.md`                       | Identity, index       |
| `.gitignore`                      | Exclusions            |
| `docs/MASTER_ROADMAP_1.0.md`      | Phase authority       |
| `docs/ARCHITECTURE.md`            | Boundary authority    |
| `docs/INVARIANTS.md`              | Invariant authority   |
| `docs/MIGRATION_LEDGER.md`        | Evidence authority    |
| `docs/STATUS_MATRIX.md`           | State authority       |
| `docs/DEFINITION_OF_DONE.md`      | DoR, DoD, Golden Path |
| `docs/TECHNICAL_DEBT_REGISTER.md` | Debt authority        |
| `docs/POST_1_0_BACKLOG.md`        | Deferral authority    |
| `docs/adr/`                       | Decision directory    |

## Risks

| Risk                                        | Likelihood | Mitigation                             |
| ------------------------------------------- | ---------- | -------------------------------------- |
| Terminology drift                           | Medium     | Canonical field and state names        |
| Legacy evidence implies design authority    | Medium     | Labels, classifications, v2 precedence |
| Documentation claims nonexistent capability | Low        | Documentation-verifiable acceptance    |

## Rollback

Delete 11 paths. No data or runtime state.

## Dependencies

Exploration #664, init #662/#663, user contract.

## Success Criteria

- [ ] 11 scope-in paths exist, obligations routed
- [ ] 22 exclusions absent
- [ ] D1-D10 all open
- [ ] No code, tests, build, src/, qml/, AGENTS.md, review-package
- [ ] No Legacy file copy
