# Proposal: M0 Foundation v2

## Intent

Establish the documentation-only foundation for a from-scratch music player while stack and architecture remain undecided.

## Scope

### In

`README.md`; `.gitignore`; `docs/MASTER_ROADMAP_1.0.md`; `docs/ARCHITECTURE.md`; `docs/INVARIANTS.md`; `docs/MIGRATION_LEDGER.md`; `docs/STATUS_MATRIX.md`; `docs/DEFINITION_OF_DONE.md`; `docs/TECHNICAL_DEBT_REGISTER.md`; `docs/POST_1_0_BACKLOG.md`; `docs/adr/`.

### Out

Exclusions (22): playback; audio engine; queue; library; database; playlists; search; metadata editor; Audio Lab; Disc Lab; Michi AI; sync; NowPlaying; functional navigation; product QML; server integrations; home audio; recognition; radio; lyrics; Michi ecosystem features; video.

## Capabilities

### New

- `governance`: `docs/MASTER_ROADMAP_1.0.md` owns roadmap; `docs/STATUS_MATRIX.md` owns status; `docs/DEFINITION_OF_DONE.md` owns DoR, DoD, and Golden Path; `docs/INVARIANTS.md` owns freeze/reopen reasons, P0/P1 0/0 release gate, feature freeze, WIP limits, baby steps, and new-tests-only; the roadmap routes each phase’s new-test strategy.
- `architecture`: `docs/ARCHITECTURE.md` routes D1 language/runtime, D2 layers, D3 state authorities, D4 composition, D5 lifecycle, D6 concurrency, D7 QML boundary, D8 audio port, D9 persistence, and D10 errors/effects; `docs/adr/` records decisions. All D1-D10 remain open for autonomous Design; no mechanism is selected.
- `legacy-evidence`: `docs/MIGRATION_LEDGER.md` owns exactly: ID, capability/responsibility, Legacy source, functional description, Legacy state, Legacy dependencies, known problems, decision, justification, new destination, new contract, Legacy tests found (reference only), new tests required, migration state, risks, technical debt, frozen. Each responsibility receives exactly one KEEP, ADAPT, SPLIT, REWRITE, or DISCARD classification; SPLIT requires named children. Individual or section-scoped `LEGACY EVIDENCE` labels mark non-authoritative evidence; v2 specifications prevail. Zero-copy forbids duplicated Legacy files. Legacy tests are read-only references, never executed; new evidence requires new tests.

### Modified

None.

## Approach

Use an ADR-first, contract-indexed pass to create exactly the listed documents and directory. Assign one owner per obligation and verify terminology. Produce no code, tests, build files, product QML, integrations, or runtime behavior.

## Affected Areas

| Path | Impact |
|---|---|
| `README.md` | New identity and index |
| `.gitignore` | New neutral exclusions |
| `docs/MASTER_ROADMAP_1.0.md` | New roadmap authority |
| `docs/ARCHITECTURE.md` | New boundary authority |
| `docs/INVARIANTS.md` | New constraint authority |
| `docs/MIGRATION_LEDGER.md` | New evidence authority |
| `docs/STATUS_MATRIX.md` | New status authority |
| `docs/DEFINITION_OF_DONE.md` | New readiness/completion authority |
| `docs/TECHNICAL_DEBT_REGISTER.md` | New debt authority |
| `docs/POST_1_0_BACKLOG.md` | New deferral authority |
| `docs/adr/` | New decision directory |

## Risks

Terminology drift creates competing authorities; Legacy evidence could imply inherited design; documentation could claim nonexistent behavior. Exact names, canonical ownership, classifications, and documentation-only acceptance mitigate these risks.

## Rollback

Remove the 11 new paths to restore the empty product workspace; no data or runtime migration exists.

## Dependencies

Approved exploration #664, fresh init #662/#663, and the original user contract.

## Success Criteria

All routed obligations, paths, and exclusions verify exactly; Design remains open; no prohibited artifact or Legacy copy exists.
