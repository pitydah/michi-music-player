# Design: QML Runtime Route Recovery

## Technical Approach

Diagnose-first hotfix: every change backed by `QQmlComponent.status()` / `errorString()` evidence. Two QML syntax fixes (brace + import), one error-surface consolidation (dual→single authority), one runtime gate. Four commits: red matrix → fixes → PageStack → CI gate.

## Architecture Decisions

### Decision: Brace-count fix for MichiLibraryToolbar

| Option | Tradeoff | Verdict |
|--------|----------|---------|
| Add `}` at EOF | Minimal, brace-count confirmed | **Chosen** |
| Refactor to fix indentation | Risky — touches 200+ lines | Rejected |

**Evidence**: Counted `{`/`}` from line 7 (`ContextToolbar {`) through line 218. The `Rectangle` closes at 218, `GridLayout` at 217. `ContextToolbar` has no matching `}`. One `}` at EOF resolves.

### Decision: Add `import QtQuick.Layouts` to ComparisonPanel.qml

| Option | Tradeoff | Verdict |
|--------|----------|---------|
| Add import line 3 | Explicit, follows QML convention | **Chosen** |
| Move `RowLayout` to `QtQuick` | Implicit, fragile | Rejected |

**Evidence**: `ComparisonPanel.qml` line 72 uses `RowLayout` but the file imports only `QtQuick` and `QtQuick.Controls`. The `RowLayout` type lives in `QtQuick.Layouts`. Position: after `import QtQuick.Controls` (line 2→3), before theme imports.

### Decision: Single error authority — AppShell ErrorState

| Option | Tradeoff | Verdict |
|--------|----------|---------|
| Keep AppShell, remove PageStack overlay | One retry + one Go Home surface | **Chosen** |
| Keep PageStack, remove AppShell | Loses `fatalOverlay` reuse | Rejected |
| Keep both | Two Retry buttons, two Go Home (dual authority) | Rejected — violates R7/R8 |

**PageStack retains**: `lastError`, `pendingRoute` state only. Inline overlay (lines 247-299) removed.

**AppShell ErrorState additions**:
- `secondaryActionText: qsTr("Ir a Inicio")` — uses existing `secondaryActionRequested` signal
- `onRetryRequested` changed from `pageStack.currentRoute` (wrong — never updated on failure) to `pageStack.pendingRoute` (the route that failed)

### Decision: Route matrix uses parametrized `QQmlComponent` per source

| Option | Tradeoff | Verdict |
|--------|----------|---------|
| Parametrized pytest over all `functional` routes | One test per route, clear failures | **Chosen** |
| Single test iterating all routes | First failure hides rest | Rejected |
| `qmlscene`/`qml` binary | Not available in CI | Rejected |

### Decision: `audio_lab.diagnostics` shares source with `audio_lab.analysis`

Both routes point to `AudioAnalysisPage.qml`. The spec constrains both MUST load. Fixing `ComparisonPanel.qml` (dependency of `AudioAnalysisPage.qml`) fixes both. No reclassification (explicitly forbidden by spec R4/R5).

## Data Flow — Error Recovery

```
User navigates to route X
        │
        ▼
PageStack.loadRoute(X)
  └─ _incomingLoader.source = source
        │
   ┌────┴────┐
   ▼         ▼
Ready      Error
   │         │
   │    lastError = msg     pendingRoute = X
   │    currentRoute unchanged (stays at previous)
   │         │
   │    AppShell ErrorState visible (bound to lastError)
   │         │
   │    ┌────┴────────────────────┐
   │    ▼                         ▼
   │  [Retry]                  [Go Home]
   │    │                         │
   │    ▼                         ▼
   │ loadRoute(pendingRoute)   nav.navigate("home")
   │    │                       lastError = ""
   │    └── back to top
   │
currentRoute = X
lastLoadedRoute = X
transition animation
```

## Files Changed

| File | Action | Description |
|------|--------|-------------|
| `ui_qml/components/MichiLibraryToolbar.qml` | Modify | Add `}` at EOF (brace fix) |
| `ui_qml/pages/audio_lab/ComparisonPanel.qml` | Modify | Add `import QtQuick.Layouts` after line 2 |
| `ui_qml/shell/PageStack.qml` | Modify | Remove inline error overlay (lines 247-299); keep `lastError`/`pendingRoute` state |
| `ui_qml/shell/AppShell.qml` | Modify | ErrorOverlay: fix retry→`pendingRoute`, add `secondaryActionText` for Go Home |
| `tests/qml/runtime/test_runtime_route_matrix.py` | Create | Parametrized `QQmlComponent.Ready` gate for all functional routes |
| `.github/workflows/ci.yml` | Modify | Add route matrix step to functional-tests job |

## Interfaces / Contracts

### Helper: `load_qml_component(path) → dict`

```python
def load_qml_component(source: Path) -> dict:
    """Load a single QML source via QQmlComponent. Returns structured result."""
    engine = QQmlEngine()
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(source)))
    return {
        "source": str(source),
        "ready": component.isReady(),
        "status": component.status(),
        "errors": [e.toString() for e in component.errors()],
    }
```

### PageStack contract (unchanged API, internal only)
- `lastError: string` — set on `Loader.Error`, cleared on `loadRoute()`
- `pendingRoute: string` — the canonical route being attempted (NOT cleared on error)
- `currentRoute: string` — updated only on `Loader.Ready`
- Inline overlay: REMOVED

### AppShell ErrorState contract (extended)
- `secondaryActionText: string` — set to `"Ir a Inicio"` for route-error overlay
- `onSecondaryActionRequested` — navigates to `home` and clears `lastError`
- `onRetryRequested` — now calls `pageStack.loadRoute(pageStack.pendingRoute)`

## Testing Strategy

| Layer | What | Approach |
|-------|------|----------|
| Unit (QML) | Toolbar, ComparisonPanel compile | `QQmlComponent` per file; assert `Ready` |
| Integration | library, audio_lab.* routes load | `QQmlComponent` on route source files |
| Gate | All functional routes compile | Parametrized pytest over `route_registry.ROUTES` filtered by `status="functional"` |
| Contract | No functional route→PlaceholderPage | Assert source ≠ `PlaceholderPage.qml` |
| Contract | Error authority | Assert PageStack has no error overlay (test child count), AppShell has exactly one Retry + one Go Home |
| CI | Gate blocks regressions | `ci.yml` step: `pytest tests/qml/runtime/test_runtime_route_matrix.py -q` |

## Threat Matrix

N/A — no routing, shell, subprocess, VCS/PR automation, executable-file classification, or process-integration boundary touched. All changes are QML syntax fixes, component composition, and CI test additions.

## Migration / Rollout

No migration required. Each commit is independently revertible: revert in reverse order. Route matrix test pinpoints the offending route on failure.

## Open Questions

- None. All decisions resolved by brace-count evidence, import analysis, and spec constraints.
