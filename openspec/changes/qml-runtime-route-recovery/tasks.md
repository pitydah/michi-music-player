# Tasks: QML Runtime Route Recovery

## Review Workload Forecast

| Field | Value |
|-------|-------|
| Estimated changed lines | ~500-700 |
| 400-line budget risk | Low |
| Chained PRs recommended | No |
| Suggested split | Single PR (4 commits) |
| Delivery strategy | single-pr |

Decision needed before apply: No
Chained PRs recommended: No
Chain strategy: pending
400-line budget risk: Low

### Suggested Work Units

| Unit | Goal | Likely PR | Focused test command | Runtime harness | Rollback boundary |
|------|------|-----------|---------------------|-----------------|-------------------|
| 1 | Test audit + fixes + PageStack + CI gate | PR 1 | `pytest tests/qml/runtime/ -q --timeout=120` | `./scripts/ci_canonical.sh` step 8 | Revert 4 commits in reverse order |

## Phase 1: Test Audit — Establish Red Baseline (Commit 1: `test(qml): add productive route runtime audit`)

- [x] 1.1 Create `tests/qml/runtime/qml_component_helper.py` — `load_qml_component(path: Path) → dict` using `QQmlComponent` with `Ready`/`errors()`/`errorString()`. Add `load_all_functional_routes() → list[dict]` iterating `route_registry.ROUTES` filtered by `status="functional"`.
- [x] 1.2 Create `tests/qml/runtime/test_runtime_route_matrix.py` — parametrized over all functional routes: assert `ready=True`, `status=Ready`, `errors=[]`, source ≠ `PlaceholderPage.qml`, source file exists. Emit JSON report on completion.
- [x] 1.3 Create `tests/qml/runtime/test_library_route_runtime.py` — focused: `library`, `library.songs`, `library.albums`, `library.artists`, `library.folders`. All assert `QQmlComponent.Ready`.
- [x] 1.4 Create `tests/qml/runtime/test_audio_analysis_route_runtime.py` — focused: `audio_lab.analysis`, `audio_lab.diagnostics`, `ComparisonPanel.qml` direct. All assert `Ready`.
- [x] 1.5 Create `tests/qml/runtime/test_pagestack_error_authority.py` — inject `lastError`, assert single Retry + single Go Home visible. No duplicate error overlays from PageStack+AppShell.
- [x] 1.6 Run matrix RED: `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/runtime/ -q --timeout=120`. Expected: ~93/96; 3 failures (MichiLibraryToolbar brace, ComparisonPanel import, audio_lab.analysis cascade).

## Phase 2: QML Syntax Fixes (Commit 2: `fix(qml): restore library and audio analysis loading`)

- [x] 2.1 Fix `ui_qml/components/MichiLibraryToolbar.qml` — add `}` at EOF closing `ContextToolbar` root (brace-count confirmed: 1 missing). Verify: `test_library_route_runtime.py` → green.
- [x] 2.2 Fix `ui_qml/pages/audio_lab/ComparisonPanel.qml` — add `import QtQuick.Layouts` after line 2 (before theme imports). `RowLayout` lives in `QtQuick.Layouts`, not `QtQuick`. Verify: `test_audio_analysis_route_runtime.py` → green.

> **Parallel note**: Phase 2 tasks 2.1 and 2.2 are independent — can be done concurrently.

## Phase 3: PageStack Single Error Authority (Commit 3: `fix(navigation): enforce single PageStack error authority`)

- [x] 3.1 Remove PageStack inline error overlay: `ui_qml/shell/PageStack.qml` lines 247-299 (the `Rectangle` with error UI). Keep `lastError`/`pendingRoute` state. Verify: `test_pagestack_error_authority.py` — zero duplicate overlays.
- [x] 3.2 Fix `ui_qml/shell/AppShell.qml` line 284 — change `pageStack.currentRoute` → `pageStack.pendingRoute` in `onRetryRequested`. Add `secondaryActionText: qsTr("Ir a Inicio")` to `errorOverlay` (line 277). Wire `onSecondaryActionRequested` to `navigationBridge.navigate("home")` + `pageStack.lastError = ""`.
- [x] 3.3 Verify error authority contract: `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/runtime/test_pagestack_error_authority.py tests/qml/runtime/test_runtime_route_matrix.py -q` → all green, single Retry, single Go Home, Retry targets `pendingRoute`.

> **Parallel note**: Phase 3 is independent of Phase 2 — can be done in parallel with Phase 2 after Phase 1.

## Phase 4: CI Gate (Commit 4: `ci(qml): gate functional routes at runtime`)

- [x] 4.1 Add route matrix step to `scripts/ci_canonical.sh` after step 7 (QML compile check): `QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/runtime/test_runtime_route_matrix.py -q --timeout=120`. Must run after lint, before functional tests. Verify: `./scripts/ci_canonical.sh` → all steps green.

## Dependency Order

```
Phase 1 (tests) ──┬── Phase 2 (QML fixes) ──┐
                  │                          ├── Phase 4 (CI gate)
                  └── Phase 3 (PageStack) ───┘
```

- Phase 2 and Phase 3 are parallelizable after Phase 1.
- Phase 4 requires all prior phases to be green.
- Each commit is independently revertible in reverse order (4→3→2→1).
