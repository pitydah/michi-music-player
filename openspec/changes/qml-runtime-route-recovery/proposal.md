# Proposal: QML Runtime Route Recovery

## Intent
Recover the QML runtime navigation surface: declared-functional routes fail to load, the route-error UI renders duplicate authorities, and route status labels are stale. Hotfix only — no new features, no visual redesign.

## Scope

### In Scope
- Fix `MichiLibraryToolbar.qml` — missing closing `}` for `ContextToolbar` root (brace-count confirmed).
- Diagnose + fix `AudioAnalysisPage.qml` load failure via `QQmlComponent` evidence. Root cause TBD: deps exist in same dir (auto-resolve), so suspect is the orphaned `Accessible.role` line or a dependency parse error. Fix follows evidence, not assumption.
- Consolidate route-error UI to a single authority: PageStack keeps `lastError` state only; AppShell `ErrorState` becomes sole renderer (add Go Home).
- Reclassify route statuses in `route_registry.py` against `QQmlComponent` load evidence (e.g. `audio_lab.analysis` is `functional` but its source fails).
- Add runtime route-matrix test (every `functional` route source loads) + CI gate.
- Expose technical route IDs in error states.

### Out of Scope
- Mix, RecommendationService, QueueService, NowPlaying, GStreamer, MPD, sync.
- New features, visual redesign, new skips/xfails/deselects.

## Capabilities

### New Capabilities
- `qml-runtime-navigation`: route loading, single error authority, route status classification, runtime route matrix gate.

### Modified Capabilities
- None. (Only `qml-playback-queue` spec exists; unaffected.)

## Approach
Diagnose-first. Every fix backed by `QQmlComponent.errorString()`. Four commits: (1) test audit + red route-matrix, (2) QML fixes (toolbar brace + AudioAnalysisPage root cause), (3) PageStack single error authority, (4) CI gate + reclassification. Error authority chosen: AppShell `ErrorState` (already owns `fatalOverlay` and binds `pageStack.lastError`); PageStack inline overlay removed as redundant.

## Affected Areas

| Area | Impact | Description |
|------|--------|-------------|
| `ui_qml/components/MichiLibraryToolbar.qml` | Modified | Add missing `}`. |
| `ui_qml/pages/audio_lab/AudioAnalysisPage.qml` (+ deps) | Modified | Fix per QQmlComponent diagnosis. |
| `ui_qml/shell/PageStack.qml` | Modified | Remove inline error overlay; keep `lastError`. |
| `ui_qml/shell/AppShell.qml` | Modified | `ErrorState` sole authority; add Go Home. |
| `ui_qml_bridge/route_registry.py` | Modified | Reclassify stale statuses. |
| `tests/qml/test_runtime_route_matrix.py` | New | Load every functional route source. |
| CI config | Modified | Gate on route matrix. |

## Risks

| Risk | Likelihood | Mitigation |
|------|------------|------------|
| AudioAnalysisPage root cause spans dependencies | Med | Per-dependency QQmlComponent isolation. |
| Removing PageStack overlay breaks existing tests | Med | Audit `test_page_stack_surface_runtime.py` first. |
| Reclassification hides a real capability | Low | Evidence log per route in test output. |

## Rollback Plan
Revert the 4 commits in reverse order. Each is independently revertible; the matrix test pinpoints the offending route on failure.

## Success Criteria
- [ ] All `functional` route sources load via `QQmlComponent` (matrix green).
- [ ] Single error authority on route failure (one Retry, one Go Home).
- [ ] `audio_lab.analysis` loads or is honestly reclassified.
- [ ] CI gate blocks regressions on functional routes.
- [ ] 0 new skips/xfails/deselects.

## First Slice
Commit 1 — test audit + red route-matrix test enumerating registry `functional` routes and asserting `QQmlComponent.Ready` per source. Establishes the failing baseline before any fix.
