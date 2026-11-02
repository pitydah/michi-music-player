# F11 Visual Recovery — UI Specification

## Identity

Feline Hi-Fi Atelier: obsidian/graphite, smoked glass, fine strokes, one
dominant accent per surface, Inter, existing Michi tokens only. No second theme,
neon, full-screen blur or decorative signal animation.

## Geometry

- NowPlayingBar: 154 px, no scroll, centred transport, existing track card.
- Signal Truth popup: target 480 px, viewport-safe minimum, internal stage
  scroll, fixed header/footer.
- Quick EQ: target 480 px, 10 rails with visible zero line, preamp -24..+24 dB.
- Advanced EQ: target 880x680, viewport-safe fallback, fixed footer, tabs wrap
  without clipping.
- Engine 360 px, Output 380 px, all within Wayland overlay safe margins.

## Signal states

| State | Token | Glyph | Accessible text |
|---|---|---|---|
| unknown | textMuted/borderSubtle | info | Unknown |
| pending | auroraBlue | history/clock | Pending |
| observed | success | check | Observed |
| transformed | auroraCyan | equalizer | Transformed |
| historical | textSecondary | history/clock | Historical |
| error | error | info/alert | Error |

Color is never the only carrier.

## Quick EQ states

`Unavailable`, `Ready`, `Draft`, `Applying`, `Effective · rev N`, `Bypassed`,
`Error`. Draft edits are local; commit is one transaction at release/apply.
Busy controls are non-editable. Calculated response is labelled
"Calculated response · not measured" and is absent without a decoded PCM rate.

## Sidebar

The sidebar keeps smoked material, grain and shadow, but disables recursive
backdrop blur (`allowBackdropBlur: false`) because the backdrop source includes
the sidebar itself. This is the KX11-08 containment; it is not a new theme.
