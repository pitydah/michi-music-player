# Michi Icon System

## Rules

- SVG monochrome line art
- Consistent stroke width (~1.5-2px)
- viewBox: 24x24 preferred, 20x20 or 32x32 acceptable
- No emoji, no letters as icons ("IN", "BL", "MX")
- Color controlled by UI layer (fill: currentColor or theme token)
- Fallback: accessible text, never glyph

## Sizes

| Context | Size |
|---------|------|
| Sidebar | 20-22px |
| Toolbar | 18-20px |
| Inline | 16px |
| Action | 24px |
| Hero | 32px |

## Locations

| Path | Purpose |
|------|---------|
| `icons/sidebar_*.svg` | Sidebar navigation icons |
| `icons/nav_*.svg` | Navigation (back, forward) |
| `icons/view/*.svg` | View mode icons |
| `icons/warm_*.svg` | NowPlaying / playback controls |
| `icons/actions/*.svg` | Context actions |
| `icons/app_icon.svg` | Application icon |

## Current Inventory

### Sidebar (10 icons)
`sidebar_home.svg`, `sidebar_library.svg`, `sidebar_mix.svg`, `sidebar_songs.svg`,
`sidebar_servers.svg`, `sidebar_radio.svg`, `sidebar_playlists.svg`,
`sidebar_home_audio.svg`, `sidebar_assistant.svg`, `sidebar_audio_lab.svg`

### Navigation (2 icons)
`nav_back.svg`, `nav_forward.svg`

### Playback (8 icons)
`warm_play.svg`, `warm_pause.svg`, `warm_next.svg`, `warm_prev.svg`,
`warm_shuffle.svg`, `warm_repeat.svg`, `warm_vol_high.svg`, `warm_vol_low.svg`

### View Modes (6 icons in `icons/view/`)
coverflow, grid, list, timeline, magazine, vinyl

## Prohibited

- Unicode characters as primary icon
- Abbreviated text ("IN", "MX", "PL")
- Emoji
- Mixed outline + filled icons without explicit rule
- Icons without Accessible.name
