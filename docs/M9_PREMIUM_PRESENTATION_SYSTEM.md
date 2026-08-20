# M9 Premium Presentation System

Implementation contract for **Michi UI Design Canon 2.0 — Feline Hi-Fi Desktop System**.

**Authority:** approved product direction, 2026-08-20.
**Boundary:** presentation only. M4–M8 domain/application behavior remains frozen.
**Current work package:** `M9-PREMIUM-01` — `IN_PROGRESS`.

## Product invariants

- Audio-only desktop player; no web-dashboard or mobile visual language.
- Backplane is near-black and visually quiet.
- Music content stays flat; smoked glass is reserved for control surfaces.
- Artwork is the main source of contextual color.
- Aurora Blue/Cyan/Purple/Green replaces the legacy pink accent.
- Library keeps exactly six album presentations: Grid, PathView, Vinyl Wall,
  Timeline, Magazine, and List.
- QML emits intent and renders projections. It does not own persistence,
  queue semantics, search ranking, or audio-engine rules.
- Deferred capabilities have no routes, placeholders, or QML shells before
  Player Stable: Michi AI, Audio Lab, Streaming/Radio, Ecosystem/Michi Link,
  Michi Sync, and Home Audio.
- Effects are bounded by `MichiMotion` and respect
  `MichiAccessibility.reducedMotion`.
- The historical Now Playing geometry remains protected until its canonical
  visual reference is available for a golden screenshot baseline.

## Delivery map

| Subphase | State | Evidence in this work package |
| --- | --- | --- |
| M9.0 UI architecture freeze | REVIEW | Layered QML tree and compatibility facade |
| M9.1 Design System 2.0 | REVIEW | Aurora tokens, typography, spacing, metrics, radii, motion, accessibility |
| M9.2 Desktop controls | REVIEW | Keyboard/focus-aware buttons, fields, segmented controls, menus, dialogs, scrolling |
| M9.3 UI Gallery | REVIEW | `dev/MichiUIGallery.qml` |
| M9.4 Application Shell | REVIEW | Floating sidebar/content islands and global search overlay |
| M9.5 Library premium UX | IN_PROGRESS | Toolbar/tabs/Grid/PathView/Vinyl/Timeline/Magazine/List migration started |
| M9.6 Album/Artist UX | IN_PROGRESS | Album detail and shared artwork migration started |
| M9.7 Playback UX | IN_PROGRESS | Visible playback error state; canonical geometry preserved |
| M9.8 Search UX | IN_PROGRESS | `Ctrl+F`, Escape, grouped local results; playlist search awaits an explicit bridge capability |
| M9.9 Motion | REVIEW | Tokenized durations/easing; permanent vinyl rotation removed |
| M9.10 Smoked Glass/Aurora | IN_PROGRESS | Control-only materiality and semantic Aurora states; real high-quality backdrop blur remains pending |
| M9.11 Responsive desktop | IN_PROGRESS | Compact sidebar breakpoint; deeper responsive audit pending |
| M9.12 Accessibility | IN_PROGRESS | focus ring, roles, keyboard controls; screen-reader audit pending |
| M9.13 UI performance | IN_PROGRESS | active-view instantiation retained; profiling belongs to M12 |
| M9.14 Capability/error audit | REVIEW | no deferred shells; empty/loading/error and playback failures visible |
| M9.15 Golden screens | BLOCKED | canonical Now Playing reference image is not present in the repository |

## Canonical QML layers

```text
presentation/qml/
├── theme/       immutable design tokens and runtime UI preferences
├── primitives/  text, icon, surface, glass, divider, focus ring
├── controls/    desktop interaction controls
├── patterns/    async states, overlays, inspector, notifications
├── media/       artwork and reusable music-specific presentation
├── shell/       application composition and navigation islands
├── views/       existing route/entity projections, migrated incrementally
└── dev/         isolated visual QA gallery
```

`MichiTheme.qml` remains a compatibility facade until every pre-M9 view has
moved to focused token singletons. Compatibility is deliberate; copying or
forking the tokens inside individual views is forbidden.

## Acceptance gates

```text
pytest -q tests/test_m9_design_canon.py
pytest -q
ruff check src tests
ruff format --check src tests
python -m build
pyside6-qmllint -I src/michi/presentation/qml src/michi/presentation/qml/**/*.qml
```

The full pytest/QML smoke suite requires a host with the Qt runtime libraries
used by CI. Static canon gates are intentionally independent from a display
server.

## Next baby steps

1. Finish migration of all list delegates to shared media primitives.
2. Add semantic sort/filter capabilities only after the bridge exposes them.
3. Implement Queue Drawer without duplicating or changing M4 semantics.
4. Complete mouse/keyboard/accessibility acceptance for every control.
5. Establish the Now Playing golden once the canonical reference is checked in.
6. Run M12 profiling for blur quality, artwork memory, startup, and large libraries.
