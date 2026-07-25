# Spec: QML Runtime Route Recovery

**Change**: `qml-runtime-route-recovery`
**Mode**: hybrid (openspec + engram `sdd/qml-runtime-route-recovery/spec`)
**Type**: Hotfix — no new features, no visual redesign, no new skips/xfails/deselects.

## Constraints (apply to every requirement)

- Every fix MUST be backed by `QQmlComponent.errorString()` / `status()` evidence.
- AGENTS.md (root): MUST NOT touch playback, `PlayerService`, GStreamer, MPD, sync, Mix, QueueService, NowPlaying.
- AGENTS.md (`ui_qml/`): QML emits intention, Python executes; foundations are presentational; no direct bridge/service/SQLite access from QML; use `MichiTheme` tokens.
- `audio_lab.analysis` and `audio_lab.diagnostics` MUST load — honest reclassification is NOT an escape hatch for these two routes (see R4/R5).
- Zero new skips, xfails, or deselects.

## Domain: library-qml-syntax

### Requirement: R1 — MichiLibraryToolbar compiles

The `MichiLibraryToolbar.qml` component SHALL compile without `QQmlError`. The diagnosed root cause (unbalanced braces on the `ContextToolbar` root) MUST be resolved; the fix follows `QQmlComponent` evidence, not assumption.

#### Scenario: Load toolbar via QQmlComponent
- GIVEN `ui_qml/components/MichiLibraryToolbar.qml` exists on disk
- WHEN a `QQmlComponent` loads it through the standard QML test harness
- THEN `component.status()` equals `QQmlComponent.Ready`
- AND `component.errors()` is empty

#### Scenario: Brace balance
- GIVEN the toolbar source
- WHEN parsed by the QML engine
- THEN every opening `{` has a matching closing `}` and no `QQmlError` is emitted

### Requirement: R2 — LibraryPage instantiates through toolbar dependency

The `library` route source `LibraryPage.qml` SHALL instantiate without `QQmlError`, including its `MichiLibraryToolbar` dependency.

#### Scenario: Load library route source
- GIVEN `LibraryPage.qml` declares `MichiLibraryToolbar`
- WHEN a `QQmlComponent` loads `LibraryPage.qml`
- THEN `status` is `Ready` with no `QQmlError`
- AND a `LibraryPage` instance is created

#### Scenario: Dependency failure surfaces, not silenced
- GIVEN the toolbar dependency were broken
- WHEN `LibraryPage.qml` is loaded
- THEN the `QQmlComponent` reports the dependency error explicitly (no silent fallback to `PlaceholderPage`)

## Domain: audio-lab-qml-imports

### Requirement: R3 — ComparisonPanel compiles

`ComparisonPanel.qml` SHALL compile without `QQmlError`. The diagnosed missing `import QtQuick.Layouts` (required by its `RowLayout` usage) MUST be present.

#### Scenario: Load ComparisonPanel
- GIVEN `ComparisonPanel.qml` uses `RowLayout`
- WHEN a `QQmlComponent` loads `ComparisonPanel.qml`
- THEN `status` is `Ready`
- AND no `RowLayout is not a type` / `module not installed` error is emitted

### Requirement: R4 — AudioAnalysisPage instantiates

`AudioAnalysisPage.qml` SHALL instantiate without `QQmlError`, including its `ComparisonPanel` dependency.

#### Scenario: Load AudioAnalysisPage
- GIVEN `AudioAnalysisPage.qml` instantiates `ComparisonPanel`
- WHEN a `QQmlComponent` loads `AudioAnalysisPage.qml`
- THEN `status` is `Ready` with no `QQmlError`

#### Scenario: No orphaned Accessible reference
- GIVEN the previously suspected orphaned `Accessible.role` line
- WHEN the page loads
- THEN no `ReferenceError` is emitted at instantiation

### Requirement: R5 — audio_lab.analysis and audio_lab.diagnostics routes load

Both `audio_lab.analysis` and `audio_lab.diagnostics` routes SHALL reach `Loader.Ready` when navigated.

#### Scenario: Navigate to each route
- GIVEN registry routes `audio_lab.analysis` and `audio_lab.diagnostics` with `status="functional"`
- WHEN `PageStack.loadRoute()` resolves each source
- THEN the incoming `Loader` reaches `Ready` for both
- AND `pageStack.lastError` remains `""`

## Domain: qml-navigation-error-authority

### Requirement: R6 — Single error authority

`AppShell` `ErrorState` SHALL be the sole renderer of route-load errors. `PageStack` MUST NOT render its own error overlay when `AppShell` already provides one; `PageStack` retains `lastError` state only.

#### Scenario: Route load failure
- GIVEN `AppShell` provides an `ErrorState` overlay bound to `pageStack.lastError`
- WHEN a route source fails to load (`Loader.Error`)
- THEN `PageStack` renders no error overlay of its own
- AND only the `AppShell` `ErrorState` is visible

### Requirement: R7 — Exactly one Retry button

On a route error, exactly one Retry control SHALL be visible and reachable.

#### Scenario: Single retry surface
- GIVEN a route error state is shown
- WHEN the error UI is rendered
- THEN exactly one Retry button is present in the accessibility/visual tree

### Requirement: R8 — Exactly one Go Home button

On a route error, exactly one "Go Home" control SHALL be visible and reachable. `AppShell` `ErrorState` MUST provide Go Home (previously only `PageStack`'s removed overlay had it).

#### Scenario: Single go-home surface
- GIVEN a route error state is shown
- WHEN the error UI is rendered
- THEN exactly one "Go Home" button is present
- AND activating it navigates to `home` and clears `lastError`

### Requirement: R9 — currentRoute unchanged on failure

A failed route load SHALL NOT mutate `currentRoute`. `currentRoute` is updated only on `Loader.Ready`.

#### Scenario: Failed navigation preserves current route
- GIVEN `currentRoute` is `home` and the user navigates to `library`
- WHEN the `library` source fails to load
- THEN `currentRoute` remains `home`
- AND `lastError` is set to a message naming the failed route and source

### Requirement: R10 — Retry loads the failed route

The Retry action SHALL reload the failed route, not the previously active route. Retry MUST target `pendingRoute` (the route that failed), not `currentRoute`.

#### Scenario: Retry targets failed route
- GIVEN a failed navigation to route `X` (`pendingRoute=X`, `currentRoute=previous`)
- WHEN the user activates Retry
- THEN `loadRoute(X)` is invoked
- AND `loadRoute(previous)` is NOT invoked

### Requirement: R11 — Error cleared on valid navigation

Navigating to a valid route SHALL clear any prior `lastError`.

#### Scenario: Navigate away from error
- GIVEN `lastError` is set from a prior failure
- WHEN the user navigates to a valid route `Y`
- THEN `lastError` is reset to `""` at the start of `loadRoute`
- AND route `Y` loads to `Ready`

## Domain: qml-runtime-gate

### Requirement: R12 — CI loads every functional route source

CI SHALL load every route with `status="functional"` from `route_registry.py` via `QQmlComponent`.

#### Scenario: Matrix enumerates functional routes
- GIVEN `route_registry.ROUTES` enumerates all routes
- WHEN the route matrix test runs in CI
- THEN each `status="functional"` route's `source` is loaded with a `QQmlComponent`

### Requirement: R13 — CI fails on any QQmlError

CI SHALL fail the gate if any functional route source produces a `QQmlError` or `status != Ready`.

#### Scenario: Functional route fails to compile
- GIVEN a functional route source
- WHEN `QQmlComponent` reports `status != Ready` or a non-empty `errors()`
- THEN the CI gate fails
- AND the failure message includes the route id and `errorString()`

### Requirement: R14 — No functional route uses PlaceholderPage source

No `status="functional"` route SHALL resolve its `source` to `PlaceholderPage.qml`. A functional route pointing at `PlaceholderPage.qml` is a classification defect and MUST fail the gate.

#### Scenario: Functional route must have a real source
- GIVEN a route with `status="functional"`
- WHEN its resolved `source` is inspected
- THEN the source MUST NOT be `PlaceholderPage.qml`
- AND the source file MUST exist on disk

#### Scenario: Missing source fails gate
- GIVEN a functional route whose source file is missing
- WHEN the matrix inspects it
- THEN the gate fails with the route id and missing path

### Requirement: R15 — CI produces a machine-readable report

The route matrix SHALL emit a JSON or JUnit XML report listing each functional route, its load status, and any error.

#### Scenario: Report on success
- GIVEN the matrix runs to completion with all routes `Ready`
- WHEN it finishes
- THEN a JSON or JUnit XML report is written listing every functional route with `status=ready`

#### Scenario: Report on failure
- GIVEN one or more routes fail
- WHEN the matrix finishes
- THEN the report lists each failing route with its `errorString`
- AND the gate exits non-zero

## Acceptance Criteria

- [ ] R1–R2: `library` route source and `MichiLibraryToolbar` load via `QQmlComponent` with zero errors.
- [ ] R3–R5: `ComparisonPanel`, `AudioAnalysisPage`, and both `audio_lab.analysis` / `audio_lab.diagnostics` routes load via `QQmlComponent`.
- [ ] R6–R11: Single error authority in `AppShell`; `PageStack` retains `lastError` only; exactly one Retry and one Go Home; `currentRoute` unchanged on failure; Retry targets `pendingRoute`; error cleared on valid navigation.
- [ ] R12–R15: `tests/qml/test_runtime_route_matrix.py` exists, loads all functional routes, fails on any `QQmlError`, rejects `PlaceholderPage.qml` sources, and emits a JSON/JUnit report.
- [ ] Functional route load count: 96/96 (baseline 93/96).
- [ ] CI gate is green and blocks regressions on functional routes.
- [ ] Zero new skips, xfails, or deselects.
- [ ] No changes to Mix, QueueService, NowPlaying, GStreamer, MPD, or sync.
- [ ] `ruff check .` clean and `python -m compileall -q` clean for touched files.

## Out of Scope

- Mix, RecommendationService, QueueService, NowPlaying, GStreamer, MPD, sync.
- New features, visual redesign, new skips/xfails/deselects.
- Sidebar layout, NowPlayingBar layout, CoverFlow, PlayerService public API.
