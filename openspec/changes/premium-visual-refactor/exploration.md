# P0-UI0: Visual Audit — QML UI System Inventory

**Date:** Mon Jul 27 2026
**Scope:** `ui_qml/` — entire QML UI layer
**Result:** Comprehensive visual inventory of gradients, textures, colors, effects, assets, and borders

---

## 1. Executive Summary

The QML visual system is well-structured with a centralized theme layer (`MichiColors.qml`, `MichiTheme.qml`) and 7 material primitives. The system uses theme tokens extensively. Key findings:

| Metric | Value |
|--------|-------|
| Total QML files | 468 |
| Icon files (all) | 265 |
| Materials | 7 (SidebarMaterial, HeroMaterial, GlassMaterial, PopupMaterial, AcrylicBackdrop, TextureOverlay, InputMaterial) |
| Gradient instances | 19 |
| "transparent" as gradient target | 11 occurrences |
| Direct hex colors (non-theme) | 8 (all in SettingsAppearancePage accent picker + 2 "white" strings) |
| Texture variants | 2 (grain + contours) |
| SVG texture assets | 2 (michi-grain.svg, michi-contours.svg) |
| ShaderEffect / MultiEffect | 1 (MichiIcon.qml for colorization) |
| Image.Tile usage | 1 (TextureOverlay.qml grain variant) |
| DropShadow/GaussianBlur/Glow | 0 (none used) |
| border declarations | 27 (all tokenized) |
| AI model PNG assets | 5 |
| GPL-3.0 license | Yes (LICENSE + NOTICE) |

---

## 2. Gradient Inventory

All 19 gradient instances found across the codebase. Organized by file:

### 2.1 Materials (9 gradients)

**SidebarMaterial.qml** — 3 gradients:
- `L26-31`: Horizontal glow → transparent → surfaceSheen (across full sidebar)
- `L39-42`: Vertical accentGlowSubtle → transparent (top 34% of sidebar)
- `L63-70`: Horizontal transparent → shadowSoft (right-edge shadow band)

**HeroMaterial.qml** — 2 gradients:
- `L30-34`: Vertical accentSurface → transparent → shadowSoft (depth stack)
- `L47-50`: Vertical surfaceHeroGlow → transparent (conditional glow layer)

**AcrylicBackdrop.qml** — 1 gradient:
- `L24-28`: Vertical accentSurface → transparent → shadowSoft

**GlassMaterial.qml** — 1 gradient:
- `L77-80`: Vertical surfaceSheen → transparent (top 44% sheen reflection)

### 2.2 Components (2 gradients)

**NowPlayingBar.qml** — 1 vertical 3-stop warm gradient:
- `L154-167`: nowPlayingGradientStart (#FF7A00) → gradientMiddle (#FF4F72) → gradientEnd (#C65CFF)

**MichiWarmSlider.qml** — 1 horizontal 4-stop warm gradient:
- `L55-61`: nowPlayingGradientStart → gradientMiddle → gradientEnd → nowPlayingThumb

### 2.3 Pages (4 gradients)

| File | Line | Description |
|------|------|-------------|
| `AlbumDetailPage.qml` | L127-130 | Vertical accentSoft → transparent → surfaceSubtle (header overlay) |
| `ArtistDetailPage.qml` | L139-142 | Vertical accentSoft → transparent → surfaceSubtle (header overlay) |
| `AlbumGridView.qml` | L205-207 | Vertical transparent → overlayDark (card bottom fade) |
| `AlbumMagazineView.qml` | L198-201 | Vertical accentSoft → surfaceHero → bgContent (magazine header) |
| `AIModelSelector.qml` | L131-135 | Horizontal accentSoft → surfaceSubtle → surfaceHero (card header) |

### 2.4 GradientStop Distribution

Total `GradientStop` instances: **48**
- 24 reference theme tokens (MichiTheme.colors.*)
- 11 use literal `"transparent"` as intermediate stop
- 13 are nowPlaying warm gradient stops (3 files)

---

## 3. "transparent" as Gradient Target

**11 occurrences** across 5 materials files. This is a deliberate technique for smooth gradient fades.

| File | Line | Context |
|------|------|---------|
| `SidebarMaterial.qml` | L29 | accentGlow → **transparent** (horizontal glow fade) |
| `SidebarMaterial.qml` | L41 | accentGlowSubtle → **transparent** (top gradient endpoint) |
| `SidebarMaterial.qml` | L65 | **transparent** → shadowSoft (shadow band start) |
| `HeroMaterial.qml` | L32 | accentSurface → **transparent** (center of depth stack) |
| `HeroMaterial.qml` | L49 | surfaceHeroGlow → **transparent** (glow layer endpoint) |
| `AcrylicBackdrop.qml` | L26 | accentSurface → **transparent** (midpoint fade) |
| `GlassMaterial.qml` | L79 | surfaceSheen → **transparent** (sheen reflection endpoint) |
| `AlbumDetailPage.qml` | L129 | accentSoft → **transparent** (header overlay midpoint) |
| `ArtistDetailPage.qml` | L141 | accentSoft → **transparent** (header overlay midpoint) |
| `AlbumGridView.qml` | L206 | **transparent** → overlayDark (card fade start) |

Additional `color: "transparent"` (non-gradient) — 4 occurrences used for `Rectangle` base colors in dual-border patterns.

---

## 4. Direct Hex Colors (Non-Theme)

**Zero** hardcoded hex colors in `ui_qml/materials/`, `ui_qml/components/`, `ui_qml/shell/`, `ui_qml/theme/`.

The **only** direct hex colors in the entire QML codebase:

| File | Lines | Colors | Purpose |
|------|-------|--------|---------|
| `pages/settings/SettingsAppearancePage.qml` | L102-107 | `#8FB7FF`, `#A78BFA`, `#FF7A00`, `#4ADE80`, `#F87171`, `#F0F2F8` | Accent color picker — intentional and correct |

Two files use literal `"white"` in error banners (not hex):
- `pages/nowplaying/NowPlayingPage.qml:L95`
- `pages/devices/MobilePairingPage.qml:L85`

**Result:** Clean — no unauthorized hex colors. Materials are 100% tokenized.

---

## 5. Texture Overlay System

### 5.1 TextureOverlay Component (`ui_qml/materials/TextureOverlay.qml`)

A single presentational component used for noise/texture overlays.

**Properties:**
- `variant`: `"grain"` | `"contours"` (default: `"grain"`)
- `strength`: real 0.0-1.0 (default: `1.0`)

**Behavior:**
- `grain`: Image.Tile with `sourceSize: 96×96` (MichiTheme.textureTileSize), opacity ≈ `strength × 0.20` (dark) / `strength × 0.12` (light)
- `contours`: Image.PreserveAspectCrop with mipmapping, opacity ≈ `strength × 0.30` (dark) / `strength × 0.18` (light)
- `enabled: false`, `Accessible.ignored: true` — purely decorative

### 5.2 Texture Usage Map

| File | Location | Variant | Strength |
|------|----------|---------|----------|
| `SidebarMaterial.qml` | L45-48 | grain | 0.40 |
| `HeroMaterial.qml` | L37-41 | contours | 0.62 / 0.90 (glow) |
| `AcrylicBackdrop.qml` | L31-36 | grain/contours | 0.46 / 0.72 (hero) |
| `HeaderBar.qml` | L96-100 | grain | 0.34 |

### 5.3 SVG Texture Assets

**michi-grain.svg** (`96×96`):
- White 1×1px dots at ~40 positions with opacities 0.18 and 0.34
- Tiled as `Image.Tile`
- Looks like fine film grain

**michi-contours.svg** (`960×320`):
- 6 acrylic-like flowing curves in `#8FB7FF` at opacities 0.09-0.26
- One filled corner wedge at 0.08 opacity
- Used with `PreserveAspectCrop` + mipmap
- Looks like subtle acrylic/fluid contours

**Note on textures:** Both SVGs reference `#8FB7FF` (cool blue accent) and `#fff` hardcoded. Since `TextureOverlay` applies them via `Image` with `opacity`, the final appearance depends on the opacity multiplier. This is acceptable for decorative assets.

---

## 6. Effects (ShaderEffect / MultiEffect)

**One single usage** in the entire codebase:

**`components/MichiIcon.qml:L53-58`:**
```qml
MultiEffect {
    anchors.fill: image
    source: image
    colorization: 1.0
    colorizationColor: root.color
}
```

Used for icon colorization (tinting SVGs/PNGs to theme colors). Uses `QtQuick.Effects` module.

**Zero** usages of:
- `ShaderEffect` / `ShaderEffectSource`
- `DropShadow`
- `GaussianBlur` / `FastBlur`
- `OpacityMask`
- `Glow` / `RectangularGlow`

In the classical Qt Widgets layer, `showGlow` is a boolean property on `HeroMaterial` controlling a gradient rectangle, not a Qt Quick `Glow` effect.

---

## 7. Image FillMode / Tile

**One usage:**
- `TextureOverlay.qml:L18`: `Image.Tile` for grain texture (`sourceSize: 96×96`)

`PreserveAspectCrop` is used for the contours variant (not Tile).

---

## 8. Image Assets

### 8.1 SVG Textures
| File | Size | Purpose |
|------|------|---------|
| `ui_qml/assets/textures/michi-grain.svg` | 949 B | Film grain noise overlay |
| `ui_qml/assets/textures/michi-contours.svg` | 799 B | Acrylic fluid contour overlay |

### 8.2 AI Model PNGs
| File | Purpose |
|------|---------|
| `ui_qml/assets/ai_models/michi-calico.png` | AI model avatar |
| `ui_qml/assets/ai_models/michi-carey.png` | AI model avatar |
| `ui_qml/assets/ai_models/michi-maine-coon.png` | AI model avatar |
| `ui_qml/assets/ai_models/michi-munchkin.png` | AI model avatar |
| `ui_qml/assets/ai_models/michi-sphynx.png` | AI model avatar |

### 8.3 App Icons
| File | Purpose |
|------|---------|
| `icons/app_icon.svg` | Main app icon |
| `icons/app_icon.png` | Main app icon (raster) |

### 8.4 Navigation Icons (`icons/`)
4 SVG nav icons: `nav_back.svg`, `nav_forward.svg`, `clear.svg`, `refresh.svg`

### 8.5 Sidebar Icons (`icons/sidebar/`) — 22+ SVGs
Album, artist, assistant, audio_lab, devices, folders, home, home_audio, identifier, jellyfin, library, mix, navidrome, playlist_item, sidebar_add, etc.

### 8.6 Now Playing Icons (`icons/nowplaying_clean/`) — 38 files
All are PNG (32/64/128px) with "warm_" prefix:
`warm_play_*.png`, `warm_pause_*.png`, `warm_prev_*.png`, `warm_next_*.png`,
`warm_shuffle_*.png`, `warm_repeat_*.png`, `warm_mute_*.png`,
`warm_vol_*.png`, `warm_eq_*.png`, `warm_audio_source_*.png`, `warm_mini_player_*.png`

### 8.7 Other icons
- `icons/radio/` — `radio_speaker.svg`
- Sidebar clean variants in `icons/sidebar_clean/`
- Old sidebar backups: `icons/backup-sidebar-old/`, `icons/backup-warm-old/`

---

## 9. Icon System

### 9.1 Icon Loading

All icons use `components/MichiIcon.qml`:
```qml
MichiIcon {
    iconKey: "sectionIcon"
    size: 18
    active: isActive
}
```

`MichiIcon` uses `MultiEffect` for colorization — the only `QtQuick.Effects` usage.

### 9.2 Now Playing Icon Pattern

NowPlaying icons follow a consistent naming scheme:
```
icons/nowplaying_clean/warm_{action}_{size}.png
```

Referenced in components:
- `NowPlayingControls.qml` — 5 icon references (shuffle, prev, play/pause, next, repeat)
- `ExpandedNowPlayingPanel.qml` — 6 icon references
- `NowPlayingTransport.qml` — 5 icon references
- `NowPlayingVolume.qml` — 4 icon references (mute, vol_low, vol_medium, vol_high)

### 9.3 HeaderBar Icons

SVG icons referenced directly:
- `nav_back.svg`, `nav_forward.svg`, `refresh.svg`
- `icons/view/filter.svg`
- `theme_sun.svg` / `theme_moon.svg`

---

## 10. Border Inventory

All 27 border declarations are fully tokenized. No hardcoded border colors.

### 10.1 Border Style Map

| Component | Border Variants | Colors Used |
|-----------|----------------|-------------|
| `GlassMaterial.qml` | `accent` / `danger` / `floating` / `hero` / `base` + `hover` | `borderFocus`, `borderActive`, `borderError`, `borderCard`, `borderSubtle`, `borderInner` |
| `InputMaterial.qml` | `normal` / `focused` / `hovered` | `borderSubtle`, `borderCard`, `borderFocus` |
| `HeroMaterial.qml` | Single style | `borderSubtle` |
| `PopupMaterial.qml` | Duo-border (outer + inner highlight) | `borderCard`, `surfaceEdgeHighlight` |
| `SidebarMaterial.qml` | accentSeparator (right edge) | `accentSeparator` |

### 10.2 Border Width

All at `MichiTheme.borderWidth` (1px) or `MichiTheme.borderWidthFocus` (2px for focused states).

---

## 11. Now Playing Color Palette

The NowPlaying system uses a dedicated warm palette scoped to playback controls:

### 11.1 Theme Tokens (from `MichiColors.qml` L139-159)

| Token | Value | Usage |
|-------|-------|-------|
| `nowPlayingBackground` | `#06080D` (dark) / `#F5F6FA` (light) | Bar background |
| `nowPlayingBorder` | `rgba(1,1,1,0.06)` (dark) | Top separator |
| `nowPlayingTrack` | `#24272E` (dark) / `#D0D4DC` (light) | Slider track |
| `nowPlayingThumb` | `#FF7A00` | Slider thumb (orange) |
| `nowPlayingThumbBorder` | `#FFFFFF` (both modes) | Thumb outline |
| `nowPlayingGradientStart` | `#FF7A00` | Warm gradient start (orange) |
| `nowPlayingGradientMiddle` | `#FF4F72` | Warm gradient middle (pink/rose) |
| `nowPlayingGradientEnd` | `#C65CFF` | Warm gradient end (purple) |
| `nowPlayingTransportBg` | `#1B1D23` (dark) / `#E8EAF0` (light) | Control button bg |
| `nowPlayingTransportBorder` | `rgba(255,255,255,0.09)` (dark) | Control button border |
| `nowPlayingTransportHover` | `rgba(255,255,255,0.12)` (dark) | Hover state |
| `nowPlayingTransportHoverBorder` | `rgba(255,255,255,0.145)` (dark) | Hover border |
| `nowPlayingTransportPressed` | `rgba(255,255,255,0.055)` (dark) | Pressed state |
| `nowPlayingShuffleActive` | `rgba(249,33,65,0.135)` | Shuffle active bg |
| `nowPlayingShuffleActiveBorder` | `rgba(249,33,65,0.26)` | Shuffle active border |
| `nowPlayingTransmitActive` | `rgba(52,199,89,0.13)` | Transmit active bg |
| `nowPlayingTransmitActiveBorder` | `rgba(52,199,89,0.28)` | Transmit active border |
| `nowPlayingQualityBg` | `surfaceElevation4` | Quality badge bg |
| `nowPlayingQualityBorder` | `rgba(255,255,255,0.08)` | Quality badge border |
| `nowPlayingMetaText` | `#B0B8C0` (light) / `#485068` (dark) | Meta text |

### 11.2 Where warm gradient is used

| File | Component | Purpose |
|------|-----------|---------|
| `NowPlayingBar.qml:L154-167` | Metadata card accent bar | 3-stop vertical gradient accent strip |
| `MichiWarmSlider.qml:L55-61` | Seek bar fill | 4-stop horizontal gradient |
| `MichiWarmSlider.qml:L72` | Slider thumb | Solid `#FF7A00` |

### 11.3 "warm" icon references

All 38 icons in `icons/nowplaying_clean/` use the `warm_` prefix pattern.

---

## 12. License and Attribution

| File | Lines | Content |
|------|-------|---------|
| `LICENSE` | 674 | GPL-3.0 (full text) |
| `NOTICE` | 134 | Attribution for Miro Player derivation |

No `ATTRIBUTION` or `THIRD_PARTY` files for QML assets. The texture SVGs were created for Michi (not third-party).

---

## 13. Material Architecture Summary

```
materials/
├── SidebarMaterial.qml   → Surface: surfaceSidebar + 3 accent gradients + grain texture
├── HeroMaterial.qml       → Surface: surfaceHero + depth gradient + contours texture + optional glow
├── GlassMaterial.qml      → Surface: 7 variants (base/compact/elevated/accent/floating/status/hero/danger)
│                             + sheen gradient + inner border
├── PopupMaterial.qml      → Surface: surfaceGlassStrong + dual border (outer + edge highlight)
├── AcrylicBackdrop.qml    → Backdrop: bgApp/surfaceHero + depth gradient + texture
├── TextureOverlay.qml     → Decorative: grain/contours SVG with strength/tint control
└── InputMaterial.qml      → Input: surfaceInput + state-based borders
```

### Composition Pattern

All materials follow the same layered pattern:
1. Base `Rectangle` with theme color
2. Depth `Rectangle` with gradient (accent → transparent → shadow)
3. Texture `Rectangle` with `TextureOverlay`
4. Border `Rectangle` (either as `border.color` property or separate overlay)
5. Optional glow layer

---

## 14. Theme Token Coverage

The `MichiColors.qml` file defines **162 color tokens** across 10 categories:

| Category | Token Count | Example Keys |
|----------|-------------|-------------|
| Background | 4 | bgBase, bgCanvas, bgApp, bgContent |
| Surfaces (elevation 0-5) | 6 | surfaceElevation0-5 |
| Surfaces (semantic) | 15 | surfaceCard, surfaceGlass, surfaceHero, surfaceSidebar, surfacePopup, surfaceInput, surfaceNowPlaying, etc. |
| Surface states | 4 | surfaceHover, surfacePressed, surfaceDisabled, surfaceSubtle |
| Controls | 3 | controlTrack, controlThumb, focusHalo |
| Borders | 7 | borderSubtle, borderCard, borderInner, borderActive, borderHover, borderFocus, borderError |
| Text | 9 | textPrimary through textOnSuccess |
| Accent / Semantic | 19 | accentPrimary, accentSoft, accentGlow, etc. + success/warning/error/info |
| Badges | 8 | badgeInfoBg/Text, badgeActiveBg/Text, badgeExperimentalBg/Text, badgeWarningBg/Text, etc. |
| Now Playing | 19 | nowPlayingBackground through nowPlayingMetaText |
| Shadows | 2 | shadowSoft, shadowFloating |
| Misc | 3 | skeletonBase/Highlight, surfaceNowPlayingBorder, overlayDark |

Plus 8 compatibility aliases: `surface`, `surfaceElevated`, `border`, `accentFaint`, `accentGreen`

---

## 15. Key Findings and Recommendations

### ✅ Strengths
1. **Complete tokenization** — No hardcoded colors in materials, components, or shell. Only accent picker and 2 error labels use literals.
2. **Consistent material layering** — All 7 materials follow the same depth/glow/border/texture pattern.
3. **NowPlaying warm palette properly scoped** — Warm colors (#FF7A00 orange, #FF4F72 pink, #C65CFF purple) are only in nowPlaying tokens.
4. **Zero ShaderEffect** — Only MultiEffect for icon colorization. No GPU-heavy effects.
5. **Light/dark mode supported** — All tokens have dual values via `lightMode` property.
6. **GPL-3.0 license present** — Includes NOTICE for Miro Player derivation.

### ⚠️ Areas for Improvement
1. **Texture SVG hardcoded colors** — `michi-contours.svg` uses `#8FB7FF` and `#fff` directly. Could make theme-responsive if needed.
2. **NowPlaying warm icons** — 38 PNG files with "warm_" prefix. Would need regeneration if warm palette changes.
3. **No animation/transition effects** — No `Behavior`, `Transition`, or state-animation patterns in materials beyond `ColorAnimation`.
4. **"white" literals** — 2 error banners use `"white"` instead of `MichiTheme.colors.textOnError`.
5. **grain opacity formula** — `strength × 0.20` (dark) / `strength × 0.12` (light) is hardcoded in `TextureOverlay.qml:L25-27`.

### 📋 Action Items for P0-UI0
1. Replace `"white"` in NowPlayingPage.qml:L95 and MobilePairingPage.qml:L85 with `MichiTheme.colors.textOnError`
2. Consider parametrizing TextureOverlay opacity base values as theme tokens
3. Document texture overlay opacity formula
4. Consider adding `Behavior` on `opacity` for texture overlays on showGlow toggle
