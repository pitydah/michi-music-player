# Tasks: Library SQL Recovery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~7,000 (5,335+ / 1,748− across 52 commits, 35 files) |
| 400-line budget risk | High |
| Chained PRs recommended | Yes |
| Suggested split | PR A (7 commits) → B (8) → C (8) → D (3) → E (25) |
| Delivery strategy | auto-chain |
| Chain strategy | stacked-to-main |

Decision needed before apply: Yes
Chained PRs recommended: Yes
Chain strategy: stacked-to-main
400-line budget risk: High

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|----------------------|-----------------|-------------------|
| 1 | SQL migration framework + filtered query service | PR A | `pytest tests/test_migrations.py tests/qml/library/test_library_filtered_query_service.py -q` | `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=120` | `git revert` merge commit |
| 2 | Metadata normalizer + batch writer upserts | PR B | `pytest tests/test_metadata_normalizer.py tests/test_batch_writer.py -q` | `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=120` | `git revert` merge commit |
| 3 | Artist/folder QML views × 6 files reconciled | PR C | `pytest tests/qml/library/test_library_navigation_views_runtime.py -q` | `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=120` | `git revert` merge commit |
| 4 | Cover provider bridge + CoverImage wiring | PR D | `pytest tests/test_cover_provider_bridge.py -q` | `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=120` | `git revert` merge commit |
| 5 | Premium library UI × 12 files reconciled | PR E | `pytest tests/qml/library/test_library_premium_runtime.py test_album_premium_views_runtime.py -q` | `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` | `git revert` merge commit |

## Phase 0: Merge + Conflict Resolution

- [ ] 0.1 `git merge origin/main` into `integration/library-sql-recovery` from `feat/library-sql-metadata-consolidation`
- [ ] 0.2 Resolve `core/library/library_filtered_query_service.py`: keep PR#127 delegate methods; merge PR#125 filter predicates alongside
- [ ] 0.3 Resolve 15 QML conflicts: reconcile PR#125 view additions with PR#127 convergence rules (no parent opacity, no list blur, no per-item shadows, theme tokens, no emoji)
- [ ] 0.4 Commit merge resolution with message: `merge: resolve 16 three-way conflicts vs converged main (PR#127)`
- [ ] 0.5 Verify: `ruff check .`, `compileall`, `pytest tests/ -q --timeout=300`

## Phase 1: PR A — SQL Migrations (7 commits)

- [ ] 1.1 Cherry-pick Group A commits onto `recovery/group-a-sql-migrations` from `integration/library-sql-recovery`
- [ ] 1.2 Verify `library/migrations.py`: all 5 existing migrations + PR#125 v6+ present, idempotent re-run is no-op
- [ ] 1.3 Verify `core/library/library_filtered_query_service.py`: FTS5 delegation intact, no `LIKE` fallback, `__getattr__` passthrough unbroken
- [ ] 1.4 Gate: `pytest tests/test_migrations.py tests/qml/library/test_library_filtered_query_service.py -q`
- [ ] 1.5 Full suite: `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` + `ruff check .` + `compileall`
- [ ] 1.6 Open PR A → merge to main, tag `recovery/group-a`

## Phase 2: PR B — Metadata Normalization (8 commits)

- [ ] 2.1 Cherry-pick Group B commits onto `recovery/group-b-metadata` from PR A merge commit
- [ ] 2.2 Verify `library/metadata_normalizer.py`: deterministic output, defined defaults for empty fields
- [ ] 2.3 Verify `library/batch_writer.py`: union both BATCH_COLUMNS sets, preserve main's `ON CONFLICT(filepath) DO UPDATE`, upsert no duplicates
- [ ] 2.4 Gate: `pytest tests/test_metadata_normalizer.py tests/test_batch_writer.py -q`
- [ ] 2.5 Full suite: `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` + `ruff check .` + `compileall`
- [ ] 2.6 Open PR B → merge to main, tag `recovery/group-b`

## Phase 3: PR C — Artist/Folder Views (8 commits)

- [ ] 3.1 Cherry-pick Group C commits onto `recovery/group-c-artist-folder` from PR B merge commit
- [ ] 3.2 Reconcile 6 QML files vs PR#127: ArtistCard, ArtistGridPage, FolderBreadcrumb, FolderBrowserPage, FolderContentView, FolderTreeView
- [ ] 3.3 Per-file QML check: no parent opacity, no list blur, no per-item shadows, MichiTheme tokens, no emoji icons, Accessible.name present
- [ ] 3.4 Gate: `pytest tests/qml/library/test_library_navigation_views_runtime.py -q` (new, for offscreen rendering)
- [ ] 3.5 Full suite: `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` + `ruff check .` + `compileall`
- [ ] 3.6 Open PR C → merge to main, tag `recovery/group-c`

## Phase 4: PR D — QML Bridges (3 commits)

- [ ] 4.1 Cherry-pick Group D commits onto `recovery/group-d-bridges` from PR C merge commit
- [ ] 4.2 Verify `cover_provider_bridge.py`: coverKey resolution, no queue subscription added, LRU cache intact
- [ ] 4.3 Verify `CoverImage.qml`: uses CoverBridgeProxy.qml Loader pattern, not NowPlayingBridge
- [ ] 4.4 Gate: `pytest tests/test_cover_provider_bridge.py -q`
- [ ] 4.5 Full suite: `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` + `ruff check .` + `compileall`
- [ ] 4.6 Open PR D → merge to main, tag `recovery/group-d`

## Phase 5: PR E — Premium UI (25 commits)

- [ ] 5.1 Cherry-pick Group E commits onto `recovery/group-e-premium-ui` from PR D merge commit
- [ ] 5.2 Reconcile 12 QML files vs PR#127: album views, toolbar, search, filter, header, host
- [ ] 5.3 Per-file QML check (same rules as Phase 3); fix any PR#125 rule violations in reconciliation commit
- [ ] 5.4 Gate: `pytest tests/qml/library/test_library_premium_runtime.py tests/qml/library/test_album_premium_views_runtime.py -q`
- [ ] 5.5 Full suite: `QT_QPA_PLATFORM=offscreen pytest tests/ -q --timeout=300` + `ruff check .` + `compileall`
- [ ] 5.6 Final verification: diff `main` vs original PR#125 tip semantically equivalent (35 files, no lost functionality)
- [ ] 5.7 Open PR E → merge to main, tag `recovery/group-e`
