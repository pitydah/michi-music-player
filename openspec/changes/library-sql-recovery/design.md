# Design: Library SQL Recovery

## Technical Approach

Recover PR#125 (52 commits, 35 files) via a **merge-then-slice** strategy. First, merge `origin/main` into `integration/library-sql-recovery` — one conflict-resolution commit for all 16 three-way conflicts. Then cherry-pick grouped commits into 5 sequential PRs (A→B→C→D→E), each branching from the previous PR's merge commit. Each PR passes `pytest` + `ruff` + `compileall` independently before the next opens. The original `feat/library-sql-metadata-consolidation` branch is preserved as fallback.

## Architecture Decisions

| Decision | Options | Chosen | Rationale |
|----------|---------|--------|-----------|
| Merge vs rebase | Rebase 52 commits across 16 conflicts OR merge once | **Merge once** | Single conflict-resolution commit. Rebase risks silent loss in 52 cherry-picks. Preserves audit trail. |
| Slice dependency model | Independent branches from main OR sequential from prior PR merge | **Sequential A→E** | B depends on A (migrations must land before normalizer); E depends on A (filtered query service). Sequential gating catches integration regressions early. |
| Conflict resolution strategy | Per-file manual reconciliation OR automated merge tools | **Per-file manual** | 16 QML conflicts cross PR#127 convergence behavior. Each file reconciled against converged main with explicit commit message citing which conflict was resolved. |
| PR-E conflict concentration | Land E with unresolved conflicts OR resolve in reconciliation commits | **Resolve in PR-E reconciliation commits** | E has 12/16 conflicts. Landing A–D first removes 4 conflicts, leaving 12 targeted reconciliations with full understanding of converged main. |

## Branch Model

```
origin/main (post PR#127 convergence)
    │
    ├─ merge ──→ integration/library-sql-recovery  (ONE conflict commit)
    │               │
    │               ├─→ recovery/group-a-sql-migrations  (PR-A)
    │               │       └─→ merge to main, tag: recovery/group-a
    │               │
    │               ├─→ recovery/group-b-metadata  (PR-B, from group-a merge)
    │               │       └─→ merge to main, tag: recovery/group-b
    │               │
    │               ├─→ recovery/group-c-artist-folder  (PR-C, from group-b merge)
    │               │       └─→ merge to main, tag: recovery/group-c
    │               │
    │               ├─→ recovery/group-d-bridges  (PR-D, from group-c merge)
    │               │       └─→ merge to main, tag: recovery/group-d
    │               │
    │               └─→ recovery/group-e-premium-ui  (PR-E, from group-d merge)
    │                       └─→ merge to main, tag: recovery/group-e
    │
    └─ feat/library-sql-metadata-consolidation  (PRESERVED, read-only)
```

## Per-Group Conflict Strategy

### Group A — SQL Migrations (LOW risk)
- `library/migrations.py`: additive only. No conflict expected — must retain all 5 existing migrations and add PR#125 migrations.
- `core/library/library_filtered_query_service.py`: conflicts possible on filter predicate methods. **Resolution rule**: PR#127 changes to queue/NowPlaying take priority; PR#125 filter additions merged alongside. Delegate methods untouched — verify `__getattr__` passthrough intact.

### Group B — Metadata Normalization (LOW risk)
- `library/metadata_normalizer.py`: additive normalizer functions. No PR#127 surface overlap.
- `library/batch_writer.py`: column set `BATCH_COLUMNS` may conflict. **Resolution**: union both column sets; keep `ON CONFLICT(filepath) DO UPDATE` from main (PR#127 hardened this).

### Group C — Artist/Folder QML (MODERATE, 6 files)
- Reconcile against PR#127 convergence rules:
  - No `opacity` on parent containers with text
  - No blur on lists/grids
  - No per-item shadows
  - Use `MichiTheme` tokens, no hardcoded colors
  - No emoji as primary icons
  - `Accessible.name` on interactive elements
- **Per-file checklist** for each of 6 files: verify QML rules, bridge access via `CoverBridgeProxy.qml` (not direct), test offscreen rendering.

### Group D — Bridges (LOW risk)
- `cover_provider_bridge.py`: existing `CoverProviderBridge` already has `requestCover(cover_key, size)` and LRU cache. PR#125 additions must NOT add queue subscription — verify `coverReady` signal source.
- `CoverImage.qml`: uses `CoverBridgeProxy.qml` Loader pattern. PR#125 changes must not bypass this.

### Group E — Premium UI (HIGH, 12 files)
- 12 QML files cross PR#127 convergence surface. **Reconciliation order**: land A–D first, then reconcile E's 12 files against the fully converged main.
- If a QML rule violation exists in PR#125 (hardcoded color, opacity on parent, per-item shadow), **fix it in the reconciliation commit** — not in a separate follow-up.
- Verify with `tests/qml/library/test_library_premium_runtime.py` and `test_album_premium_views_runtime.py`.

## File Changes

| File | Action | Group | Description |
|------|--------|-------|-------------|
| `library/migrations.py` | Modify | A | Add PR#125 migrations (v6+) to existing 5-migration list |
| `core/library/library_filtered_query_service.py` | Modify | A | Merge PR#125 filter additions alongside PR#127 delegate methods |
| `library/metadata_normalizer.py` | Modify | B | Add PR#125 normalizer functions |
| `library/batch_writer.py` | Modify | B | Merge BATCH_COLUMNS; preserve main's ON CONFLICT logic |
| `ui_qml/pages/library/ArtistCard.qml` | Create/Modify | C | Artist card component |
| `ui_qml/pages/library/ArtistGridPage.qml` | Create/Modify | C | Artist grid browse view |
| `ui_qml/pages/library/FolderBreadcrumb.qml` | Create/Modify | C | Folder hierarchy breadcrumb |
| `ui_qml/pages/library/FolderBrowserPage.qml` | Create/Modify | C | Folder browser page |
| `ui_qml/pages/library/FolderContentView.qml` | Create/Modify | C | Folder content listing |
| `ui_qml/pages/library/FolderTreeView.qml` | Create/Modify | C | Folder tree navigation |
| `ui_qml_bridge/cover_provider_bridge.py` | Modify | D | PR#125 cover resolution additions |
| `ui_qml/components/CoverImage.qml` | Modify | D | Consume cover bridge changes |
| 12 QML files (album, toolbar, search, filter) | Modify | E | Premium library UI from PR#125 |
| `tests/test_migrations.py` | Modify | A | Test new migration versions |
| `tests/test_metadata_normalizer.py` | Modify | B | Test new normalizer functions |
| `tests/test_batch_writer.py` | Modify | B | Test merged column set |
| `tests/qml/library/test_library_filtered_query_service.py` | Modify | A | Test merged filter predicates |
| `tests/test_cover_provider_bridge.py` | Modify | D | Test bridge additions |
| `tests/qml/library/test_library_premium_runtime.py` | Modify | E | Test premium UI rendering |
| `tests/qml/library/test_album_premium_views_runtime.py` | Modify | E | Test album views rendering |
| `tests/qml/library/test_library_navigation_views_runtime.py` | Create | C | Test artist/folder view rendering |

## Testing Strategy

| Layer | What to Test | Approach |
|-------|-------------|----------|
| Unit — migrations | Idempotency, partial failure safety | `tests/test_migrations.py`: `:memory:` DB, apply/re-apply/fail scenarios |
| Unit — normalizer | Determinism, defaults, FTS5-no-LIKE | `tests/test_metadata_normalizer.py`: parameterized inputs |
| Unit — batch writer | Upsert, flush at threshold, no duplicates | `tests/test_batch_writer.py`: `:memory:` DB |
| Unit — query service | FTS5 delegation, filter column indexing | `tests/qml/library/test_library_filtered_query_service.py` |
| Unit — cover bridge | No queue subscription, missing-cover empty state | `tests/test_cover_provider_bridge.py` |
| QML integration — C | Artist/folder views offscreen | `tests/qml/library/test_library_navigation_views_runtime.py` (new) |
| QML integration — E | Premium UI offscreen, no warnings | `tests/qml/library/test_library_premium_runtime.py` + `test_album_premium_views_runtime.py` |
| Regression | Queue/NowPlaying convergence | Full suite: `QT_QPA_PLATFORM=offscreen python -m pytest tests/ -q --timeout=300` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary in the source code changes. The git merge/cherry-pick operations are human-driven recovery actions, not automated code paths.

## Migration / Rollout

No data migration — files are code-level additions/modifications to existing modules. Rollback per PR via `git revert` of merge commit. Original branch preserved as fallback.

## Open Questions

- [ ] Exact list of 12 QML files in Group E — verify against PR#125 tip to ensure none are missed
- [ ] Do PR#125 migrations (v6+) require `VACUUM` or are they all `ALTER TABLE`? Existing engine uses `executescript` for migration SQL — verify new migrations are compatible
- [ ] Are any of the 6 Group C QML files NEW (not in main yet) vs MODIFIED? New files have zero conflict risk; only modified files need reconciliation
