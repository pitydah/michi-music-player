# M9 Premium Presentation System

Implementation contract for **Michi UI Design Canon 2.0 — Feline Hi-Fi Desktop System**.

**Authority:** approved product direction, 2026-08-20.
**Boundary:** presentation only. M4–M8 domain/application behavior remains frozen.

**WORK PACKAGE:** DONE
**COMPONENT:** FROZEN
**PR:** #204 MERGED
**MERGE COMMIT:** 87c534ec2ba8fd5bfebf0f3936ae84c2acf7c05e
**ACCEPTANCE:** product owner accepted the current baseline to continue the roadmap.
**CI EVIDENCE:** Michi CI #2158 on the merge head `87c534ec2ba8fd5bfebf0f3936ae84c2acf7c05e` — SUCCESS (1245 passed; lint, Qt/QML suite and sdist+wheel build green). PR head `44158437bc34c9f6293417ccbef319b39d6dcbc0` also verified by Michi CI #2157 (SUCCESS).

## Controlled Reopening Policy

Frozen means **protected from unsolicited change, not immutable**. M9 remains
CLOSED / TESTED / FROZEN by default, and may be reopened in a controlled and
scoped way when a later milestone requires presentation work.

M9 MAY be reopened when one of these conditions applies:

1. a reproducible UI/UX regression appears;
2. a later milestone requires a presentation change;
3. a new Required-1.0 capability requires UI integration;
4. M12 performance findings require changes to presentation/QML/materials;
5. M13 packaging or desktop/platform integration requires UI adaptation;
6. Beta or RC testing exposes usability, accessibility or interaction defects;
7. an architectural change makes an existing M9 presentation contract obsolete;
8. another Player milestone has a legitimate presentation dependency.

Product-owner realignment (2026-08-21) pre-authorizes these SCOPED reopenings,
each still declared with its own REOPEN REASON / SCOPE / TRIGGERING MILESTONE /
AFFECTED COMPONENTS / NON-GOALS / TEST-ACCEPTANCE GATES / REFREEZE CONDITION:

- **M9-R1 — Playlists Sidebar / Presentation** (trigger: playlists Required-1.0):
  Playlists section in Sidebar, All Playlists access, bounded pinned/recent
  quick access, create affordance, canonical Playlist screen presentation,
  removal of duplicate Playlist presentation authority. NON-GOALS: general M9
  redesign, new visual language, unrelated Library redesign. Refreeze: M9-R1
  accepted. **STATUS: CLOSED — delivered 2026-08-21 (a87f651..96dd57c); the
  Playlists hierarchy is sealed per PLAYLIST-HIERARCHY-01..06; M9 returned to
  FROZEN.**

  **M9-R1I convergence correction (2026-08-21, b6b8311..6249cb8)**: the
  `3fdbd33` closeout is HISTORICAL/PREMATURE evidence — the follow-up
  production-convergence pass made NavigationState.playlist_id the SINGLE
  detail authority (PlaylistsBridge is projection-only, no local selection),
  composed exactly ONE production PlaylistsBridge in ApplicationContainer
  with explicit dispose, sealed search keyboard parity, deterministic
  create/rename dialog workflows and hardened card accessibility. Final
  convergence range: b6b8311..6249cb8 (suite 1437 passed). M9 remains FROZEN.

  **M9-R1J interaction & search reactivity seal (2026-08-21)**: Detail
  rename/delete route through the shared shell
  dialogs via semantic intents (PlaylistDetailView never opens dialogs nor
  references their ids); PlaylistsBridge now observes LibraryService
  (symmetrically disposed) making playlist search fully reactive;
  SearchOverlay aggregates M7 total + playlist local count
  (combinedResultCount — playlist-only searches render and activate);
  PlaylistCard no longer claims delegate focus. Dynamic QML interaction gates
  added (real menu-intent execution, ReferenceError guard) — they caught a
  real production defect: the rename_playlist QML slot was declared
  `@Slot(str, result=bool)` (missing the second arg) so QML renames would
  have failed at runtime; corrected to `@Slot(str, str, result=bool)`.
  M9 remains FROZEN.

  M9-R1J traceability:
  - implementation: 6ee9e12..7d78fab
  - implementation validation: 1449 passed
  - documentation closeout: f713a89
  - QML error-capture refinement: 79f764f (intermediate test-harness step)
  - SearchOverlay lazy-binding + real-chain dynamic-gate hardening: e4af323
  - M9-R1K P2 hardening implementation: ccb4500441d17ca5c633f29c6e9311b1042bcd6d
  - M9-R1K documentation closeout: 48d38e6a62befd2a295c556cda0a65b9e0beb601
  - M9-R1L final QA (real open→focus→close focus gate): 6af09b200075c85fca72fa263be183f68529ca6d
  - M9-R1M QML harness integrity seal: f3f9dff56ea342ae9714449c33401e40b370b0a9
    validation: 1456 passed (Ruff PASS, build PASS, QML gates PASS, product diff ZERO)
    statement: the QML test harness now distinguishes pre-existing teardown
    noise from runtime errors emitted by the component under current test; a
    deliberate runtime ReferenceError probe is regression-tested and must be
    detected.
- **M9-R2 — Audio Output UX** (trigger: M11.3/M11.4 audiophile output):
  engine selector, DAC selector, Output Profile selector, output state,
  actual format telemetry, Signal Path, DSD mode, BitPerfectState, hotplug/
  unavailable/error state. The canonical NowPlayingBar geometry stays
  protected (reserved `audioEngineIndicator`/`outputZone`/`outputDeviceButton`
  are activated; transport controls are not moved). Refreeze: M9-R2 accepted.
- **M9-R3 — Library Hierarchy, Contextual Actions & Playlist Convergence**
  (trigger: Required-1.0 Library and Playlist workflows): one responsive Library
  toolbar, application-owned sorting, shared technical track projections,
  capability-driven Track/Album/Artist context actions, batch playlist
  targeting, and converged Library/Queue/Playlist track presentation. The
  canonical material tokens and NowPlayingBar remain protected. **STATUS:
  IMPLEMENTED LOCALLY — acceptance gates pending publication.**

Every reopening MUST be scoped and MUST declare:

- **REOPEN REASON**
- **SCOPE**
- **TRIGGERING MILESTONE**
- **AFFECTED COMPONENTS**
- **NON-GOALS**
- **TEST / ACCEPTANCE GATES**
- **REFREEZE CONDITION**

Example: M12 Performance discovers an expensive visual effect → scoped M9
reopening → replace/tune the visual implementation → tests + acceptance →
M9 refrozen.

M9 MUST NOT be reopened merely for: aesthetic experimentation, opportunistic
redesign, trying a newer visual style, replacing a working component without a
release/product requirement, or endless polishing unrelated to the current
Stable path. Non-critical visual refinement remains possible later (especially
after Player Stable), but that does not prevent justified scoped reopening
before Stable.

### M9 FREEZE POLICY

M9 is CLOSED / TESTED / FROZEN after PR #204.

Frozen means protected from unsolicited change, not immutable.

A later milestone may trigger a scoped M9 reopening when presentation work is
required to satisfy a functional, performance, packaging, accessibility, Beta,
RC, architectural, or regression requirement.

Every reopening must declare its triggering milestone, exact scope, non-goals
and re-freeze gate.

Purely discretionary aesthetic refinement does not justify reopening M9 during
the current path to Stable.

After the scoped work passes its acceptance gates, M9 returns to FROZEN.

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

All M9.0–M9.15 subphases below belong to the accepted PR #204 baseline and are
DONE within the work package. They are recorded as delivered evidence, not as
open review items.

| Subphase | State | Evidence in this work package |
| --- | --- | --- |
| M9.0 UI architecture freeze | DONE | Layered QML tree and compatibility facade |
| M9.1 Design System 2.0 | DONE | Aurora tokens, typography, spacing, metrics, radii, motion, accessibility |
| M9.2 Desktop controls | DONE | Keyboard/focus-aware buttons, fields, segmented controls, menus, dialogs, scrolling |
| M9.3 UI Gallery | DONE | `dev/MichiUIGallery.qml` |
| M9.4 Application Shell | DONE | Floating sidebar/content islands and global search overlay |
| M9.5 Library premium UX | DONE | Shared media rows, runtime density, six canonical views, common playing state and desktop context actions |
| M9.6 Album/Artist UX | DONE | Responsive album detail, technical inspector, canonical artist detail projection, artist albums/tracks and activation |
| M9.7 Playback UX | DONE | Canonical persistent NowPlayingBar with real metadata/artwork, seek, volume, mute, shuffle, repeat, queue and transport; Artwork Focus Mode remains available |
| M9.8 Search UX | DONE | `Ctrl+F`, Escape, Up/Down/Enter and actionable grouped Tracks/Albums/Artists/Playlists; M7 ranking remains frozen |
| M9.9 Motion | DONE | Tokenized durations/easing; permanent vinyl rotation removed |
| M9.10 Smoked Glass/Aurora | DONE | Control-only materiality, semantic Aurora states and High/Normal/Low material quality; expensive real backdrop blur is intentionally gated to M12 profiling |
| M9.11 Responsive desktop | DONE | Compact sidebar, responsive inspectors/artwork, density controls and contextual right Queue drawer |
| M9.12 Accessibility | DONE | Roles/names, keyboard-vs-pointer visual focus, tooltips, PageUp/PageDown, transient scrollbars, high contrast and reduced motion |
| M9.13 UI performance | DONE | Library tabs, album modes, Queue and Focus Mode instantiate on demand; performance profiling remains owned by M12 |
| M9.14 Capability/error audit | DONE | no deferred shells; empty/loading/error and playback failures visible |
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
  technical badge reports the canonical quality projection for the current
  file without implying output selection, bit-perfect or Hi-Res state.
- The supplied reference lives at
  `tests/golden/now_playing_bar_reference.png`; its checksum and 1920×154
  canvas are pinned, while the runtime QML smoke gate asserts measured track,
  timeline, transport, Queue, volume, and quality-badge landmarks.
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
- NowPlayingBar keeps its canonical geometry while metadata, transport,
  technical quality and volume remain distinct semantic zones. Its local
  colors, along with the refined shell and row states, are sourced from
  semantic tokens rather than hardcoded values.

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

## M9-PREMIUM-09 Library control hierarchy

- Library section navigation is embedded in the primary toolbar rather than
  occupying a second floating surface. It remains a dedicated component and
  emits intents instead of mutating its parent-owned selection binding.
- Search uses bounded responsive geometry. At wide desktop widths it leaves
  room for all section tabs; at the minimum supported window size the tab rail
  scrolls horizontally and Scan collapses to an accessible icon-only action.
- The album view selector is driven by the active Library context. Its six
  canonical modes gain labels on wide layouts and compact to icon buttons at
  narrower breakpoints; sections with one implemented projection do not show
  a meaningless selector.
- Density remains global but is visually compact in the header. Every segment
  preserves its accessible label, tooltip, focus ring and medium control hit
  target.
- NowPlayingBar identity is title, artist and album. Technical quality moves to
  the right-side badge using `qualityLabel`, while the volume rail loses its
  nested glass card and shares the timeline's track height and gradient.
- Album list title and artist columns use matched responsive proportions in
  both header and rows, avoiding the previous oversized empty title span while
  keeping year, track count, duration and precision metadata aligned.

## M9-R3 Library and collection convergence

- Library scanning has one `performScan()` intent. Folder selection supplies a
  `QUrl`, which `LibraryBridge` adapts before invoking the existing application
  flow. Scan remains available before a directory has been selected.
- `LibraryTrackQueryService` and `LibraryAlbumQueryService` own sorting and
  query policy. QML renders their projections and never sorts domain data.
- `LibraryTrackColumnState` is the session authority for shared track-column
  widths, minimums, and visibility. `MichiTrackTable` is used by Songs,
  Favorites, History, Recently Added, Album Detail, and Artist Detail.
- Format badges report file facts only: normalized container/codec labels and
  explicit DSD rates. They never infer Hi-Res, lossless, bit-perfect, selected
  output, or active output state.
- `LibraryQueueCoordinator` and `LibraryPlaylistCoordinator` resolve canonical
  track, album, and artist identities before mutating Queue or Playlist owners.
  Batch playlist additions preserve source order, deduplicate paths, persist at
  most once, and publish at most one notification.
- Track, album, and artist menus are capability-driven. They expose only wired
  intents. Queue adds move/remove actions; Playlist adds move/remove and a
  real playlist-target picker; unavailable persisted tracks retain truthful
  fallback metadata and disable actions that require Library membership.
- Search, Queue, and Playlist rows reuse the same technical projection as
  Library surfaces. `trackId` is the STABLE Library identity; `path` is the
  current factual media location (explicit `legacy-path::` fallback only for
  pre-catalog records) — never a second identity authority. Navigation uses
  `albumKey`, `artistKey`, and `playlistId`.
- The removed global Precision Mode has no replacement. Technical facts remain
  visible where useful without becoming an output-quality claim.

### M9-R3-R1 correction and hardening

- Playlist targeting uses semantic payloads (`trackIds`, `albumKey`, or
  `artistKey`) and one shell-owned picker. The picker presents deduplicated
  Pinned, Recent, and All sections, supports search, and can create a playlist
  while adding the original selection in one application publication.
- Queue and Playlist rows use specialized context menus. Track, album, artist,
  and genre targets acquire focus before pointer or keyboard context-menu
  actions; Menu and Shift+F10 invoke the same target-specific commands.
- Track Properties reports identity, audio, and file facts. Album Properties
  derives its format, sample-rate, bit-depth, and DSD-rate summary only when
  requested, avoiding an eager per-album scan in the normal projection.
- Genre activation resolves a canonical `genreKey` and opens the shared Songs
  projection with an application-owned filter. Selecting Songs again clears
  that filter; search and entity navigation also clear incompatible selection.
- The Library toolbar uses a responsive grid rather than a user-resizable
  navigation split. All six album projections preserve Open and context-menu
  behavior and expose a real album Play action; no view redirects album Play to
  the whole visible Library projection.
- The shared mini-Library picker reuses `MichiTrackTable` selection and column
  behavior. Missing Library metadata still does not disable Queue or Playlist
  playback; only Library-dependent actions are withheld.

### M9-R3-R4 hierarchy, interaction, and visual hardening

- Album and artist delegates always resolve selected and default backgrounds
  to semantic colors. Library cards no longer scale on hover.
- The Library toolbar keeps responsive navigation in `GridLayout`. Search has
  a clamped mouse and keyboard resize handle on desktop widths. Scan and source
  selection share one `MichiSplitButton`: the primary segment scans the current
  source or opens the native picker when no source exists; the secondary
  segment opens the source menu, where the current folder is visible and can be
  changed through the native picker.
- Vinyl Wall reuses `VinylDisc`, preserves the sleeve/disc hierarchy without
  groove repeaters or infinite rotation, and opens the canonical `albumKey` on
  the first primary tap. Keyboard and exact-target context actions remain.
- Artists use circular `ArtistPortraitCard` delegates with local representative
  artwork as fallback. Instantiated gallery delegates may request external
  portraits only when Online Library Enrichment is enabled.
- `EnrichmentBridge.artistPortraits` is separate from detail knowledge state.
  Portrait requests are cache-first, deduplicated, capped at 12 pending items,
  limited to two concurrent operations, and delivered through the Qt owner-
  thread relay. They never change `activeKind`, `activeKey`, review state, or
  scan/search behavior. Cached portraits remain available while offline.
- Artist context menus now include an identity header and only wired actions.
  No synthetic Play Artist or Artist Properties command was introduced.
- Michi Legacy informed the sleeve/disc offset and circular portrait hierarchy;
  its hover scaling, groove decoration, and infinite spin were intentionally
  rejected by the current motion and material canon.

### M9-R5 Library premium UI/UX refinement

- Library headings now pair the active section with factual collection counts.
  The redundant `VIEWS` label is removed, and PathView is presented to users as
  **Cover Flow** without changing the canonical six-view model.
- Search and Scan have independent geometry. Search keeps a bounded,
  keyboard-operable desktop resize handle; Scan uses one compact split-button
  silhouette with a dedicated source menu.
- Artist galleries and details use `ArtistPortraitArtwork`, which applies a
  true circular `MultiEffect` mask. Gallery prefetch is debounced to the visible
  rows plus one row of overscan and remains cache-first, online-gated,
  deduplicated, and bounded to 12 pending requests and two inflight requests.
- Album and artist details follow a music-first order: back intent, identity,
  concise local facts, contextual enrichment, related albums, then tracks.
  Empty knowledge surfaces do not render, and one inline component owns status
  and enrichment actions.
- Album cards no longer promote technical summaries. Vinyl Wall uses restrained
  grooves, a real artwork center label, and a physical sleeve reveal without
  infinite rotation. Cover Flow reduces peripheral fragmentation and keeps one
  focal selection surface.
- `MichiTrackTable` supports `songs`, `album`, and `artist` profiles while
  preserving the shared column authority. Artwork is capped at 52 px, Duration
  remains at least 76 px, Actions is fixed, and cache buffering is never
  negative during layout transitions.
- Context menus use `MichiMenuItem` for deterministic 36 px rows. Artist menu
  identity uses the same true portrait treatment; Queue and Playlist removal
  copy remains context-specific.
- Track artwork is projected in `LibraryBridge` once per represented canonical
  album, so artist and album track tables do not perform QML-side album scans.
- Local acceptance evidence: **3036 passed, 1 skipped** under isolated XDG
  state; Ruff, formatting, qmllint, compileall, wheel build, production QML
  runtime, responsive captures at 1920/1646/1440/1200/800, and all canonical
  palette/material/glass/NowPlaying firewalls pass. The branch is published;
  PR creation and PR-triggered CI remain pending, so the work package stays in
  `VERIFY`.

### M9-R5.1 surgical Library and playback hardening

- The toolbar now lays out navigation, the Search resize handle, Search, and
  the Scan split button directly in one responsive grid. Search is the flexible
  utility surface; Scan no longer participates in a manually budgeted wrapper.
- Track-title resizing starts from the persisted width and compensates through
  the nearest visible data column. This removes the wide-viewport dead zone,
  keeps header and row geometry aligned, and leaves Actions non-resizable.
- Playback duration is reset when a new source is accepted, queried once from
  the active transport, normalized at the application boundary, and still
  accepts later backend duration events. Unknown duration disables seeking,
  renders an empty timeline, and displays an em dash without changing the
  frozen `NowPlayingBar` geometry.
- `AudioEngineBridge` projects one live per-engine selection decision for both
  quick selection and Settings. Active playback uses the application-layer
  `stop_and_switch_to()` transaction, which validates the target before Stop,
  revalidates quiescence, reuses the existing lease/snapshot/rehydration path,
  and never autoplays.
- Album and Artist detail playlist actions now propagate as signals rather than
  writing through bound relay properties. Artist return restores gallery
  focus; detail sizing is content-led; Album detail uses `MichiFormat` as the
  formatting authority.
- Local acceptance evidence: **3049 passed, 1 skipped** under isolated XDG
  state; Ruff, formatting, qmllint, compileall, wheel build, production QML
  runtime, and toolbar geometry checks at 1920/1646/1440/1200/800 are green.
  Canonical palette, semantic color, material texture, glass, and openspec
  firewalls remain unchanged. Only timeline state/wiring changed inside
  `NowPlayingBar`; its geometry remains frozen. Remote CI remains pending.
