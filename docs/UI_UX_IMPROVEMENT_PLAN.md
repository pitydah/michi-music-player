# UI/UX Improvement Plan

Consolidated plan from four UI/UX audits of the QML presentation layer
(2026-08). Tracks work on branch `antigravity/m9-r2-ui-ux-refinement`
(PR #207). **Scope note:** the Now Playing surface (sidebar route →
`NowPlayingView`, `ArtworkFocusMode`, `NowPlayingBar`, and the unused
`components/NowPlayingPanel`, `PlaybackControls`, `VolumeControl`,
`PlaybackProgress`) is intentionally **out of scope** — it will be
redesigned separately. Do not touch it in these phases.

## Status

| Phase | Items | State |
|---|---|---|
| 1 — Accessibility & micro-interactions | 30 findings | ✅ Done (PR #207, CI green) |
| 2 — Critical functional bugs | 5 items | 🔄 In progress |
| 3 — Visual consistency & copy | 10 items | ⬜ Pending |
| 4 — Opportunity (larger scope) | 6 items | ⬜ Pending |
| 5 — Final polish | 4 items | ⬜ Pending |

---

## Phase 1 — ✅ COMPLETED (PR #207)

Commits `40965e4` → `bf329df` (plus `d8e0c45` format and `6c6efc2` flaky
test fix). CI green at head `bf329df`, 1575 tests + 13 structural tests in
`tests/test_m9_r2_2_audit_accessibility.py`.

- Keyboard a11y: global transport shortcuts gated on `activeFocusControl`;
  playlists grid arrow-key nav; MagazineView editorial cards focusable;
  playlist cover keyboard-operable; `MichiAlbumRow` input-modality tracking
- Contrast: `textMuted` raised to `#8A90A0` (WCAG AA ≥4.5:1 on
  obsidian/graphite/smoke)
- Empty states for Songs/Favorites/History/RecentlyAdded/Genres/Folders +
  "Choose Music Folder" CTA on empty library
- Touch targets: TrackRow/LibraryHeader action buttons → `controlMedium`
  (36px); `TrackTableHeader` 36px
- `MichiScrollBar` attached to 9 flat/detail lists
- Album table header click-to-sort wired (mode + direction ↑↓)
- Popup family: enter/exit fade+slide for Menu/ContextMenu/Dialog/Combo;
  pressed states + pointing cursors; `MichiSeparator` (theme-correct);
  `MichiPopup` outCubic easing
- Glyphs: `repeat-one` vector lines (was illegible 8px fillText);
  `chevron-down` added
- Micro-interactions: slider/checkbox hover; button press-snap/release-ease;
  toast fade; motion tokens in LoadingState/equalizer; entity divider
  aligned; AlbumCard play button → `controlLarge`; search-field reflow eased

---

## Phase 2 — 🔴 CRITICAL: functional bugs (~3.5 h)

| # | Finding | Evidence | Fix | Effort |
|---|---|---|---|---|
| 1 | **Infinite spinner on failed scan** — "Building your library…" spins forever when `fileCount === 0` and scan FAILED; ErrorState renders simultaneously | `views/LibraryContentHost.qml` LoadingState | Exclude FAILED/CANCELLED from LoadingState; ErrorState covers FAILED with retry | 30 min |
| 2 | **Queue unusable by keyboard** — ListView lacks `keyNavigationEnabled`; Up/Down dead; global Left/Right shortcuts skip tracks while focused in queue | `components/QueuePanel.qml:68-114` | `keyNavigationEnabled` + Up/Down keys + visual currentIndex feedback | 1 h |
| 3 | **QueueView no close/focus** — no Esc, no focus grab, no exit animation; scrim MouseArea at opacity 0 still swallows input | `views/QueueView.qml:12-21` | Esc + `onOpened` focus + animated exit + `enabled` gate on scrim | 30 min |
| 4 | **Cover-flow: click breaks drag** — full-delegate MouseArea swallows press; PathView flick dies when gesture starts on a cover; click has no pressed state or `forceActiveFocus` | `views/AlbumPathView.qml:171-176` | TapHandler + pressed + focus retention | 1 h |
| 5 | **Vinyl wall: selected state unreachable by mouse** — tap opens instantly; rich selected visual (disc offset, cyan label) only via keyboard | `views/VinylWallView.qml:204-210` | Tap 1 = select, Tap 2 / Enter = open | 30 min |

**Commit A (done):** items 1 + scan-retry portion of item 6 — `LibraryContentHost`
ErrorState gains "Retry scan" action; LoadingState excludes FAILED/CANCELLED.

**Commit B (done):** items 2 + 3 + 12 — QueuePanel ListView gains
`keyNavigationEnabled` + keyboard-selection feedback (`queueList.isCurrentItem`)
+ scrollbar; QueueView dismisses with Escape, grabs focus, gates the scrim on
`revealed` and animates its exit before teardown; Clear queue now requires a
`MichiDialog` confirmation.

**Commit C (done):** items 4 + 5 + 22 — cover-flow covers use TapHandler
(keeps PathView drag, pressed feedback, focus retention, double-click opens);
vinyl wall first tap selects / second tap opens; timeline adds `reuseItems`,
4px-grid margins (20/28/48), an opaque floating section header, and animated
row background.

**Commit D (done):** items 6 + 7 + 9 + 10 + 15 — one accent per surface
(timeline years neutral, vinyl labels neutral when unselected, cover-flow
border unified to cyan); ArtistDetail hero elevated to glass like the album
hero; MichiScrollBar on vinyl/timeline; section headers DemiBold; album
detail metadata no longer duplicated at ≥960px (chips <960, stats column
≥960). Item 8 (badge geometry) deferred — the deviating badge lives in the
excluded Now Playing surface.

**Commit E (done):** items 11 + 13 + 14 + part of 24 — copy fixes
(" track"/" tracks" lowercase in cover-flow, `qsTr("Delete \"%1\"?")` no
longer concatenates, "Rename…"/"Delete…" ellipsis); PlaylistCard title role
fixed (`cardTitle` → `section`, was silently falling back to body 14px);
status dots (pinned, library-ready) expose Accessible names;
`Accessible.selected` on timeline/vinyl/path delegates (QueueView
`Accessible.dialog` was already added in Commit B).

**Commit F (done):** items 23 + 25 — queue reorder buttons reveal on row
hover (matching TrackRow's trash), queue drawer glass → `subtle`; dead
`Behavior on y` removed from cover-flow card; 36px buttons → `controlMedium`;
legacy `ui/` wrapper layer (`MichiButton/Panel/Slider/TextField`) and unused
`AsyncStateView` deleted — SettingsView migrated to real controls
(`Controls.MichiButton/MichiTextField/MichiSlider`, `MichiGlassSurface`).
`MichiDivider` kept (single SearchOverlay use dimensions it). Note:
`components/NowPlayingPanel.qml` still imports `../ui` — dead code reserved
for the Now Playing redesign.

**Commit G (done):** items 21 + 19 — high-contrast mode now lifts
textSecondary/textMuted/textDisabled (~7:1 on obsidian) instead of borders
only; new `MichiFormat` singleton (theme/qmldir) replaces the 6 in-scope
formatTime/formatDuration/formatFileSize copies (TrackRow, MichiAlbumRow,
PlaylistCard, PlaylistsView, PlaylistTrackList, AlbumDetailView). Now
Playing copies stay untouched (out of scope).

**Commit H (done):** items 16 + 17 + 20 (partial) — the library header now
names the active tab (wayfinding); ToastHost gains an optional action button
and is wired globally (`window.showToast` / `showToastWithAction` via
AppShell) with feedback for add-to-playlist, queue remove, queue clear and
pin/unpin, plus an **Undo** action for remove-from-playlist (re-adds by
path). Queue undo deferred — the queue service has no insert API.

**Commit I (done):** item 18 — full qsTr coverage across the in-scope
surfaces (toolbar, library host, sidebar, header, tabs/options popup,
source popover, search overlay, settings, media headers/rows, immersive
views, detail views, pattern defaults, magazine/playlist mixes). Only Now
Playing strings remain untranslated (out of scope). Canon tests updated.

## Phase 3 — 🟠 WARNING: visual consistency & copy (~5 h)

| # | Finding | Evidence | Fix | Effort |
|---|---|---|---|---|
| 6 | **Aurora accent overload** — every timeline year cyan; every vinyl label purple; cover-flow blue vs cyan fighting in one focal area | `TimelineView:181`, `VinylWallView:131`, `AlbumPathView:127/199` | One accent per surface; rest to `textSecondary` | 1-2 h |
| 7 | **ArtistDetail hero flat vs AlbumDetail glass** — same hierarchy, opposite weight | `ArtistDetailView:22-64` vs `AlbumDetailView:82-91` | Elevated glass hero | 30 min |
| 8 | **Quality badge three geometries** — 28px/purple vs 24px/cyan | `ArtworkFocusMode:62-64` vs `AudioQualityBadge:8-10`, `MichiStatusChip:17-19` | Unify 24px pill cyan | 30 min |
| 9 | **Mixed scrollbars** — bare ScrollBar in Vinyl/Timeline vs MichiScrollBar elsewhere | `VinylWallView:46`, `TimelineView:43` | `MichiScrollBar` | 15 min |
| 10 | **Section headers Bold vs DemiBold**; legacy `MichiTheme.space12` | `TimelineView:80`, `NowPlayingView:30` | DemiBold; `MichiSpacing.md` | 15 min |
| 11 | **Copy** — " TRACK"/" TRACKS" uppercase; `qsTr` string concatenation; "Rename"/"Delete" missing "…" | `AlbumPathView:228`, `ContentHost:183`, `PlaylistsView:388-392` | lowercase + `%1` + ellipsis | 30 min |
| 12 | **Clear queue without confirmation** (destructive) | `QueuePanel:52-57` | Confirm dialog | 30 min |
| 13 | **Invalid `role: "cardTitle"`** — silently falls back to body 14px | `PlaylistCard:194` | `title` (23px) | 5 min |
| 14 | **Color-only status dots without a11y** — pinned, view options, library-ready | `PlaylistCard:213`, `LibraryHeader:101`, `Sidebar:173` | `Accessible.checked`/name | 15 min |
| 15 | **AlbumDetail duplicated info ≥960px** — chips AND stats column | `AlbumDetailView:147-162,210-248` | One treatment | 30 min |

## Phase 4 — 🟡 OPPORTUNITY (~8 h)

| # | Improvement | Detail | Effort |
|---|---|---|---|
| 16 | **Wayfinding: per-tab titles** | PageHeader per list tab (Songs/Favorites/History/RecentlyAdded/Genres/Folders/Albums/Artists currently titleless) | 1-2 h |
| 17 | **Action feedback** | Instantiate `ToastHost` (currently dead code) for add-to-playlist, remove, unfavorite, pin | 1-2 h |
| 18 | **Full qsTr** | 99 translated strings live in playlists/shell/empty-states only; cover toolbar, media, Sidebar + intra-file mixes (MagazineView, PlaylistCard) | 2-3 h |
| 19 | **`MichiFormat` singleton** | Replace 9 hand-rolled `formatTime` copies (m:ss, h:mm:ss, "N hr N min", GB/MB) with QLocale-aware helper | 1-2 h |
| 20 | **Undo** | Snackbar undo for remove-from-queue and unfavorite | 1-2 h |
| 21 | **Real highContrast** | Boost textSecondary/textMuted in high-contrast mode (currently borders only) | 30 min |

## Phase 5 — 🟢 FINAL POLISH (~2.5 h)

| # | Detail | Evidence | Effort |
|---|---|---|---|
| 22 | Timeline 1px misalignments (21/27/48), floating section header `z:4`, missing `reuseItems` | `TimelineView:56,132,149,48-52` | 1 h |
| 23 | Queue affordance levels (up/down always-lit vs hover trash); glass `elevated` → `subtle` | `QueuePanel:101-112,30-33` | 30 min |
| 24 | `Accessible.selected` on timeline/vinyl/path delegates; `Accessible.dialog` on QueueView | `TimelineView:109`, `VinylWallView:63`, `QueueView` | 45 min |
| 25 | Dead `Behavior on y`; hardcoded 36px buttons; `MichiDivider` magic width; unused `AsyncStateView`/`ui/*` | `AlbumPathView:279-285,240-254` | 30 min |

## Editorial playlist page redesign (M9-R2.4, done)

Spec-driven redesign of the playlist route content (mockup reference;
Sidebar / global top bar / NowPlayingBar untouched):

- **PlaylistHero** (`playlists/PlaylistHero.qml`, new): atmospheric
  low-saturation blue gradient (`playlistHeroTop/Mid/Bottom` tokens
  #152A45/#13243D/#0A0D14), dominant 136px square cover (custom /
  2x2 mosaic / quiet placeholder) with a faint diffuse shadow, eyebrow
  "PLAYLIST" (10-11px, tracking), display title (30px DemiBold), compact
  metadata + 2-line description cap, discrete actions (Play 36px accent,
  Shuffle/Pin/More 28px)
- **PlaylistTrackList** (redesigned): dense 50px editorial table —
  hover +0.035 / selected +0.06 / hairline divider tokens
  (`rowHover`/`rowSelected`/`rowDivider`), distinct selected vs playing
  (accent title + MichiPlayingIndicator), click selects, double-click /
  Enter plays from that track, context actions hover-revealed,
  `reuseItems`, full keyboard nav
- **PlaylistDetailView** (redesigned page): hero scrolls away, sticky
  quiet column header fades in by scroll progress, responsive columns
  (>1200 all, 900-1200 +album, 700-900 artist only, <700 grouped),
  integrated empty state ("This playlist is empty" + Add Music →
  navigates to Library), glass card hero removed
- **No queue coupling**: `play_track(index)` bridge →
  `play_playlist_from(id, index)` service (queue rebuilt as a
  consequence of playback); `selectedPlaylistDescription` property
  exposed for the future description field
- Canon tests updated (cover a11y now in PlaylistHero, empty-detail
  layout); new `test_m9_r2_4_playlist_editorial.py` (9 tests) +
  2 bridge tests for play-from-index

## Out of scope (do not touch)

- Now Playing surface: `views/NowPlayingView.qml`, `media/ArtworkFocusMode.qml`,
  `player/NowPlayingBar.qml`, `components/NowPlayingPanel.qml`,
  `components/PlaybackControls.qml`, `components/VolumeControl.qml`,
  `media/PlaybackProgress.qml` — reserved for a future redesign.
- Font-scaling hardening of fixed-height rows (PlaylistCard 220, cards 240/286,
  mini-player 94, chips 24): revisit after the Now Playing redesign.

## Material composition overhaul (M9-R2.3, done)

Audit finding: the grain was mathematically invisible (18 sub-pixel SVG dots,
0.28% coverage, 1.3–4.5% effective opacity) and the glass had no volume
(sheen 2.8%, no blur). Overhauled in one commit:

- **R1/R7** `MichiMaterialTexture`: procedural deterministic 128px grain
  (mulberry32 + seed, ~260 gaussian dots, ~5% coverage, smooth AA) replaces
  the 64px SVG asset; tile opacity 0.22 / 0.36 (was 0.09/0.16);
  `tileSeed` per surface (14 surfaces decorrelated) via `MichiGlassSurface`
- **R2** sheen 0.028 → 0.06, height 0.42→0.5, cap 36→56
- **R3** specular glint — the brand cat-head silhouette (Canvas path:
  two pointed ears over a rounded face, x=50-symmetric) as the light catch,
  filled with a radial glow (0.07/0.09) — `glassGlint` tokens
- **R4** rim highlight 0.045 → 0.075; bottom shadow 0.22 → 0.26
- **R5** real backdrop blur: `MultiEffect` (QtQuick.Effects) over a
  `ShaderEffectSource` of the window, gated to `glassQuality === "high"` and
  non-subtle elevations, using the orphaned `MichiElevation` blur tokens;
  tinted gradient layered above the blur (opacity 0.88)
- Canon: `michi-grain.svg` removed; color tokens stay theme-owned;
  `test_m9_r2_3_material_texture.py` (8 structural tests)
- **Now Playing Bar polish (positions frozen)**: backplane shares the film
  grain (seed 17); play/pause icons crossfade (opacity+scale, no layout
  shift); the playback aura breathes on a 2.4s cycle; play button gains a
  gradient material with a pressed/hover overlay; timeline and volume
  handles react to hover (scale + aurora border); bar time formatting
  delegates to `MichiFormat`

## Management notes

- **Branch debt**: `antigravity/m9-r2-ui-ux-refinement` is 20 commits behind
  `main` — integrate before closing PR #207.
- **Risk**: all changes are presentation-layer QML; gates are the 1575-test
  suite + qmllint + ruff. Preserve: determinate scan progress bar, DPR-aware
  artwork, reducedMotion gates, `activeFocusControl` shortcut gating.
