# M9 Premium Presentation System

Implementation contract for **Michi UI Design Canon 2.0 — Feline Hi-Fi Desktop System**.

**Authority:** approved product direction, 2026-08-20.
**Boundary:** presentation only. M4–M8 domain/application behavior remains frozen.
**Current work package:** `M9-PREMIUM-08` — `REVIEW` (material composition,
bounded album-card geometry, richer Library information hierarchy and a
responsive album-detail hero without adding non-portable UI dependencies).

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
- The historical Now Playing geometry is protected by the canonical 1920×154
  screenshot, its checksum, and production-QML landmark assertions.

## Delivery map

| Subphase | State | Evidence in this work package |
| --- | --- | --- |
| M9.0 UI architecture freeze | REVIEW | Layered QML tree and compatibility facade |
| M9.1 Design System 2.0 | REVIEW | Aurora tokens, typography, spacing, metrics, radii, motion, accessibility |
| M9.2 Desktop controls | REVIEW | Keyboard/focus-aware buttons, fields, segmented controls, menus, dialogs, scrolling |
| M9.3 UI Gallery | REVIEW | `dev/MichiUIGallery.qml` |
| M9.4 Application Shell | REVIEW | Floating sidebar/content islands and global search overlay |
| M9.5 Library premium UX | REVIEW | Shared media rows, runtime density/Precision Mode, six canonical views, common playing state and desktop context actions |
| M9.6 Album/Artist UX | REVIEW | Responsive album detail, technical inspector, canonical artist detail projection, artist albums/tracks and activation |
| M9.7 Playback UX | DONE | Canonical persistent NowPlayingBar with real metadata/artwork, seek, volume, mute, shuffle, repeat, queue and transport; Artwork Focus Mode remains available |
| M9.8 Search UX | REVIEW | `Ctrl+F`, Escape, Up/Down/Enter and actionable grouped Tracks/Albums/Artists/Playlists; M7 ranking remains frozen |
| M9.9 Motion | REVIEW | Tokenized durations/easing; permanent vinyl rotation removed |
| M9.10 Smoked Glass/Aurora | REVIEW | Control-only materiality, semantic Aurora states and High/Normal/Low material quality; expensive real backdrop blur is intentionally gated to M12 profiling |
| M9.11 Responsive desktop | REVIEW | Compact sidebar, responsive inspectors/artwork, density controls and contextual right Queue drawer |
| M9.12 Accessibility | REVIEW | Roles/names, keyboard-vs-pointer visual focus, tooltips, PageUp/PageDown, transient scrollbars, high contrast and reduced motion |
| M9.13 UI performance | REVIEW | Library tabs, album modes, Queue and Focus Mode instantiate on demand; performance profiling remains owned by M12 |
| M9.14 Capability/error audit | REVIEW | no deferred shells; empty/loading/error and playback failures visible |
| M9.15 Golden screens | DONE | Project-supplied 1920×154 reference pinned byte-for-byte; production QML landmarks verified at the canonical canvas |

## Canonical QML layers

```text
presentation/qml/
├── theme/       immutable design tokens and runtime UI preferences
├── primitives/  text, icon, surface, glass, divider, focus ring
├── controls/    desktop interaction controls
├── patterns/    async states, overlays, inspector, notifications
├── media/       artwork and reusable music-specific presentation
├── player/      canonical NowPlayingBar and future player-only surfaces
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

## M9-PREMIUM-04 closure evidence

- `LibraryBridge` exposes artist detail and local playlist-name search without
  altering M7 scoring or canonical entity identity.
- `PlaybackBridge` and `QueueBridge` enrich presentation from the canonical
  library while leaving playback and M4 Queue semantics untouched.
- Queue is a contextual, on-demand right drawer with reorder, remove, clear,
  repeat, shuffle, duration, and the universal playing indicator.
- Track context menus expose only implemented actions: Play, Favorite,
  Add to playlist, Properties, and Remove where available.
- Search result navigation covers every required actionable group.
- The Now Playing route and Artwork Focus Mode render only current artwork and
  metadata. Progress, transport and volume remain exclusively in the canonical
  persistent NowPlayingBar, so entering the route never creates a second player.
- `player/NowPlayingBar.qml` preserves the supplied geometry and control
  distribution while binding only to real playback/Queue capabilities. The
  fixed local-output controls are explicitly unavailable; the badge reports
  the real local source and file format.
- The supplied reference lives at
  `tests/golden/now_playing_bar_reference.png`; its checksum and 1920×154
  canvas are pinned, while the runtime QML smoke gate asserts measured track,
  timeline, transport, Queue, volume, and output-badge landmarks.
- Every animation path is reduced-motion aware. Custom media delegates
  distinguish pointer focus from keyboard visual focus.
- Static canon/golden/bridge gates: **24 passed**. Ruff check/format and package build
  pass locally. The full Qt smoke/full pytest gate runs in GitHub Actions.

## Remaining external/future gates

1. Run M12 profiling before enabling costly real backdrop blur and tune artwork
   memory, startup, and 10k/50k/100k library behavior there.
2. Add semantic sort/filter controls only when their application-layer
   capabilities exist; M9 deliberately does not fabricate them.

## M9-PREMIUM-05 detail pass

- Smoked-glass surfaces now share directional material depth, inner edge
  lighting and opt-in Aurora accent rails without introducing costly blur.
- Buttons, icon buttons, tabs, switches, cards and rows have restrained
  reduced-motion-aware hover, press, selection and focus feedback.
- Library scanning uses a semantic status chip and animated Aurora progress;
  playlist targeting is a proper control surface instead of loose text links.
- Search communicates its keyboard shortcut and result summary as compact
  technical instrumentation; Queue enters as a contextual right-side panel.
- Empty, error and Inspector states use the same visual grammar as the main
  shell and remain explicit and actionable.
- NowPlayingBar gains refined Aurora progress, volume, hover and edge-lighting
  while every golden landmark and visible control remains unchanged.

## M9-PREMIUM-07 workspace refinement

- Library now has one contextual toolbar: its title, result count, search hint,
  source controls and precision tools adapt to the active tab instead of
  presenting a permanently expanded strip of unrelated actions.
- The six canonical album presentations live in one icon-first view switcher.
  Each option retains an accessible name and tooltip; the duplicate selector
  previously rendered by the Albums view has been removed.
- Density selection is compact and visual, while its labels remain available
  to assistive technology. Icon-only controls share a square hit target,
  focus treatment and tooltip behavior through `MichiButton`.
- Audio collections share a semantic table header and column contract. Album
  and artist detail hide redundant columns without forking the row component,
  and row actions remain quiet until hover, focus or selection.
- Sidebar navigation has one active-route rail and stronger optical alignment;
  Settings uses the shared page header and a centered desktop content width.
- Queue is constrained above the persistent NowPlayingBar, so opening the
  contextual drawer can never create or obscure a second transport surface.
- NowPlayingBar keeps its canonical geometry while local-output status and
  device selection use distinct icons and descriptions. Its local colors,
  along with the refined shell and row states, are sourced from semantic
  tokens rather than hardcoded values.

## M9-PREMIUM-08 material and Library refinement

- The shell uses a low-cost material stack inspired by acrylic systems:
  directional surface gradients, two restrained shadow layers, inner edge
  light and a tiny precomposed grain tile. `glassQuality=low` removes grain,
  preserving a deterministic fallback without runtime shaders.
- Album cards now use bounded minimum and maximum widths instead of stretching
  to consume every spare pixel. Grid density changes card geometry while the
  card keeps artwork square and exposes only real year, track and technical
  metadata supplied by `LibraryBridge`.
- Album selection has explicit hover, press, keyboard focus and selected
  states. Artwork decoding stays asynchronous, cached and source-size bounded.
- Album detail follows a hero/table hierarchy: breadcrumb and back intent,
  artwork, identity, quality, duration and track count occupy one elevated
  surface; the track table remains a quieter subordinate surface.
- External references were used as evidence, not dependencies:
  PowerBlur's layer recipe informed material token separation;
  pyqt-liquidglass was rejected because its glass path is macOS/Qt Widgets
  specific; Ergosign shader effects were rejected because they require a
  compiled plugin; Kirigami's bounded cards and adaptive action hierarchy were
  translated into project-native QML. FluentUI, PyHuskarUI and Rin-UI remain
  study references only, so Michi does not inherit another design system or
  runtime theme owner.
- Native `MultiEffect`/custom shader blur remains behind the M12 profiling gate.
  Effects are not multiplied across virtualized album delegates; the material
  treatment must remain usable on software and low-power scenegraph backends.
