# Proposal: Library SQL Recovery

## Intent

Recover PR#125 (`feat/library-sql-metadata-consolidation`, 52 commits, 5335+/1748-, 35 files) onto the clean `main` branch by slicing it into 5 sequential PRs along its natural dependency boundaries. PR#125 stranded when PR#127 (queue convergence) landed first; 16 files now carry three-way conflicts to reconcile against converged main.

## Scope

### In Scope
- Merge `origin/main` into `integration/library-sql-recovery` (single conflict-resolution commit)
- Re-land 5 commit groups as 5 sequential PRs in order A → B → C → D → E
- Reconcile 16 conflicting QML files (6 in Group C, 12 in Group E)
- Preserve original PR#125 branch as fallback reference

### Out of Scope
- New features beyond PR#125's existing content
- Schema re-architecture or normalization model redesign
- Touching PR#127 convergence behavior

## Capabilities

### New Capabilities
- `library-sql-metadata`: SQL migration framework + metadata normalization pipeline (Groups A+B)
- `library-artist-folder-views`: QML artist/folder browse surfaces (Group C)
- `library-premium-ui`: Album/toolbar/search/filter premium QML (Group E)

### Modified Capabilities
- `qml-playback-queue`: cover/bridge wiring touches shared QML surfaces (Group D)

## Approach

1. **Merge, don't rebase** — `git merge origin/main` into `integration/library-sql-recovery` preserves commit history and yields one explicit conflict-resolution commit. Rebasing 52 commits across 16 conflicts is fragile and loss-prone.
2. **Slice into 5 PRs** in dependency order; each is a reviewable work unit:
   - **PR-A** Group A (7 commits): SQL migrations — foundation, LOW conflict risk
   - **PR-B** Group B (8 commits): Repos/normalization — depends on A, LOW risk
   - **PR-C** Group C (8 commits): Artist/folder QML — depends on B, MODERATE (6 conflicts)
   - **PR-D** Group D (3 commits): Bridges — depends on C, LOW risk
   - **PR-E** Group E (25 commits): Premium UI — depends on D, HIGH (12 of 16 conflicts)
3. **Per PR**: cherry-pick group commits onto fresh branch from previous PR's merge commit, run `pytest` + `ruff` + `compileall`, gate green before opening next PR.

## Affected Areas

| Area | Impact | Group |
|------|--------|-------|
| `library/migrations.py`, `core/library/library_filtered_query_service.py` | New | A |
| `library/metadata_normalizer.py`, `library/batch_writer.py` | Modified | B |
| `ui_qml/pages/` ArtistCard, ArtistGridPage, FolderBreadcrumb, FolderBrowserPage, FolderContentView, FolderTreeView | New | C |
| `ui_qml_bridge/cover_provider_bridge.py`, `ui_qml/components/CoverImage.qml` | Modified | D |
| 12 QML files (album views, toolbar, search, filter) | Modified | E |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| 16 QML three-way conflicts vs PR#127 convergence | High | Merge main once; per-PR explicit reconciliation commits |
| Group E: 12 of 16 conflicts concentrated here (HIGH) | High | Land E last after A–D de-risk the foundation |
| Group C: 6 QML files overlap PR#127 | Medium | Manual diff against converged main per file |
| Cherry-pick misordering breaks dependencies | Medium | Strict A→B→C→D→E; gate each PR green before next |
| Lost commits during slicing | Medium | Verify each PR's commit set matches original group before opening |
| Rebasing instead of merging (avoided) | High (avoided) | Use merge; never rebase the 52-commit history |

## Rollback Plan
- Each PR is independent and revertible via `git revert` of its merge commit
- `integration/library-sql-recovery` is disposable; on failure delete branch and restart from `origin/main`
- Original PR#125 branch preserved — no destructive history rewrite

## Dependencies
- `origin/main` HEAD (post PR#127 convergence) as merge base
- Existing openspec spec `qml-playback-queue` (Group D touches its surface)
- Docs commit (1) bundled with Group E or landed alongside

## Success Criteria
- [ ] All 5 PRs merged to `main` in order A → B → C → D → E
- [ ] `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300` green after each PR merge
- [ ] `ruff check .` clean after each PR merge
- [ ] `python -m compileall -q -x '.venv/|\.tmpl\.' .` clean after each PR merge
- [ ] Final diff of `main` vs original PR#125 tip is semantically equivalent (same 35 files, no lost functionality)
- [ ] No regression in PR#127 convergence behavior

## First Slice: Group A (SQL Migrations)

**Branch**: `recovery/group-a-sql-migrations` (branched from `integration/library-sql-recovery` after the main merge)

**Contents (7 commits)**:
- `library/migrations.py` — new SQL migration framework
- `core/library/library_filtered_query_service.py` — filtered query service

**Conflict risk**: LOW — additive files, minimal overlap with PR#127 convergence surface

**Why first**: Foundation for Groups B–E. Group B (normalization) needs the migration framework to land its schema changes safely; Group E (premium UI) needs the filtered query service to drive album/toolbar views. Landing A first de-risks every subsequent slice.

**Verification gate (must pass before opening PR-A)**:
```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=120
ruff check . --output-format concise
python -m compileall -q -x '.venv/|\.tmpl\.' .
```

**Exit criteria for PR-A**: green CI, no new test regressions vs `origin/main`, merge commit tagged `recovery/group-a` to anchor the next slice's branch base.
