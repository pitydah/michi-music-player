# Codex UI Responsive Specification

## Breakpoints

| Mode | Width | Margin | Columns | Density |
|---|---:|---:|---:|---|
| Compact | 800-1279 | 16 | 1 | compact |
| Regular | 1280-1919 | 24 | 2 | comfortable |
| Wide | 1920+ | 40 | 4 | comfortable |

## Required behavior

- 800x600: sidebar may collapse; primary actions remain visible; secondary actions use overflow; split panels stack.
- 1280x720: heroes shorten or scroll; toolbars avoid single-line crowding; tables may hide secondary metadata.
- 1920x1080: two-panel layouts and two-to-four-column grids are preferred.
- 2560x1440 and 3840x2160: constrain reading/form widths and increase columns, not font size by viewport.
- HiDPI 125/150/200%: rely on Qt scaling and preserve minimum interactive size and SVG assets.

## Overflow requirements

| Page/area | Required overflow |
|---|---|
| Library toolbar | Search stays visible; refresh/filter extras move to overflow. |
| Playlist detail | Destructive and secondary actions wrap or overflow. |
| Metadata workflows | Forms scroll vertically; labels do not use fixed 60 px widths. |
| Audio Lab/Connections | Cards change 1/2/4 columns. |
| Now Playing | Compact mode retains play/pause, identity and route access. |

## Responsive panel requirements

- Playback queue/history: side-by-side only when regular/wide.
- Album/artist detail: artwork header stacks in compact mode.
- Home ecosystem cards: one column below regular.
- Devices/connections: details move below summary rather than disappearing.

Adoption must be screenshot-tested at 800x600, 1280x720, 1920x1080 and 3840x2160 after each functional wave.
