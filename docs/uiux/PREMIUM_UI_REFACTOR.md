# Premium UI Refactor

## Baseline

- Base SHA: `1aa6231af7a70fb245adedd28fb4210da6cf19b5`
- Branch: `refactor/premium-ui-system`
- QML inventory: 451 files, 450 productive and one development gallery.
- Test baseline: 7815 passed, 2057 failed, 348 skipped, 898 errors,
  8 xfailed and 1 xpassed.

The failing baseline is dominated by stale bridge fixtures, obsolete route
expectations and legacy component assertions. New work must not increase the
failure set in the focused runtime suites.

## Inventory

| Category | Count | Canonical owner |
|---|---:|---|
| Entrypoints | 2 | `Main.qml`, `MichiApp.qml` |
| Shell | 6 | `ui_qml/shell/` |
| Theme foundations | 6 | `ui_qml/theme/` |
| Materials | 6 | `ui_qml/materials/` |
| Components | 138 | `ui_qml/components/` |
| Pages | 292 | `ui_qml/pages/` |
| Development-only | 1 | `ui_qml/dev/ComponentGallery.qml` |

Component subfamilies are foundations, layout, states, content, dialogs,
settings, Audio Lab, notifications, playback controls and root compatibility
components.

## Canonical Components

| Concern | Canonical | Compatibility wrapper | Deprecated implementation | Productive consumers before migration |
|---|---|---|---|---:|
| Card | `MichiCard` | `GlassCard` | old independent `GlassCard` implementation | 47 files / 130 instances |
| Panel | `MichiPanel` | `GlassPanel` after parity | duplicate panel implementations | 0 |
| Icon | `MichiIcon` | `IconSlot` | text-capable icon slot for primary icons | 4 canonical consumers |
| Page | `MichiPage` | `ResponsivePageLayout` after parity | manual Flickable/Column pages | 0 canonical consumers |
| Header | `MichiPageHeader` | `PageHeader` | manual page headers | 7 legacy consumers |
| Section | `MichiSection` | `SectionHeader` | header-only section composition | 73 files / 109 instances |
| Grid | `MichiResponsiveGrid` | none | manual width breakpoints | 14 files / 15 grids |
| Feature card | `MichiFeatureCard` | `GlassCard` during migration | page-local feature cards | hubs |
| Empty state | `MichiEmptyState` | `EmptyState` | none; wrapper already exists | 18 |
| Loading state | `MichiLoadingState` | `LoadingState` | independent legacy state | 30 |
| Error state | expanded `MichiErrorState` | `ErrorState` | independent legacy state | 21 |
| Planned state | `FeatureStatePage` | none | none | 9 routes |

No compatibility wrapper may be removed until content search and runtime route
tests show zero productive consumers.

## Migration Order

1. Consolidate theme tokens and harden canonical component contracts.
2. Register a physical `MichiIcon.qml` and normalize icon sources.
3. Rebuild shell geometry, sidebar interaction and global header wiring.
4. Move the Now Playing surface inside the content column.
5. Migrate Home to `MichiPage` and `MichiResponsiveGrid`.
6. Migrate static hubs to `MichiFeatureCard`.
7. Migrate bridge-backed hubs while preserving their state machines.
8. Migrate Library incrementally, retaining all models and queries.
9. Convert compatibility states and legacy headers only after parity tests.
10. Deprecate wrappers after the last productive consumer is migrated.

## Page Consumers And Risks

### Low risk

`StreamingHubPage`, `SyncHubPage`, `AudioLabHubPage`,
`AudioCaptureHubPage` and `HomeAudioHubPage` are mostly static route cards.

### Medium risk

`AudioProcessingHubPage`, `DistributionHubPage` and `RoomsHubPage` contain
ambiguous destinations or bridge-role mismatches. Visual migration must not
represent inert cards as functional.

### High risk

- Home has custom state precedence and currently reads an absent
  `ecosystemState` property.
- Mix has disconnected loading states and incorrect parameterized navigation.
- Library exposes ten domain states, selection, paging and persistent models.
- Legacy Audio Lab hubs contain invalid route IDs and inert click handlers.
- `ErrorState` carries diagnostics and retry semantics absent from the current
  canonical preset.

## Functional Defects To Preserve Or Correct Explicitly

- Header search is visually present but not wired.
- Theme toggle bypasses persistent `ThemeBridge` settings.
- Transmit has a visible empty handler.
- `PlaybackPage` expects properties absent from `PlaybackBridge`.
- `RoomsHubPage` sends `zoneId`; the registry requires `zone_id`.
- Mix passes parameters to the one-argument `navigate` slot.
- Library labels its folder tab as Genres and omits toolbar height from its
  content calculation.

These defects require focused tests; they must not be hidden by visual wrappers.

## Product Policy Cleanup

Static premium-subscription claims exist in Radio, Mix and Connections without
an entitlement contract, capability or payment route. They must be removed and
replaced with truthful dependency, configuration or bridge-state messages.

## Validation Strategy

- Instantiate canonical components and every registered route.
- Retain `test_placeholder_routes_runtime.py`.
- Validate shell geometry at seven required resolutions.
- Exercise mouse and keyboard navigation from sidebar, hubs, search,
  breadcrumbs, Home and Now Playing.
- Fail on critical QML diagnostics, missing images, anchor conflicts, polish
  loops, hardcoded page colors, empty handlers and invented paywall text.
- Capture real application screenshots only after runtime tests pass.
