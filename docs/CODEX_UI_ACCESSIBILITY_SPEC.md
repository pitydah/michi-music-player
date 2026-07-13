# Codex UI Accessibility Specification

## Component contract

| Component type | Role | Name | Keyboard |
|---|---|---|---|
| Text button | Button | Visible label or explicit name | Enter, Space |
| Icon button | Button | Mandatory semantic action | Enter, Space; tooltip mirrors name |
| Search field | EditableText | Search scope | Enter submits, Escape clears |
| Slider | Slider | Controlled value purpose | Arrows adjust by step |
| Track/list row | ListItem | Title plus artist/context | Enter/Space primary action; context key later |
| Tile/card | ListItem or Button | Entity title | Enter/Space activate |
| State panel | StaticText/Indicator | State title | Actions enter normal tab order |

## Focus

- Focus is visible only when an item has active keyboard focus.
- Ring uses theme focus color, width and HiDPI-safe offset.
- Disabled controls remain legible and expose why they are unavailable through description/tooltip.
- Focus order follows visual order; no hidden item receives focus.

## Motion and feedback

- Reduced motion removes optional travel and shortens essential feedback.
- Loading remains perceivable when animation is disabled.
- Error and unavailable states use text, not color alone.
- Skeletons expose an accessible loading name.

## Adoption acceptance

- Every icon-only control has configurable `Accessible.name`.
- Custom interactive content handles Enter and Space.
- Escape closes/clears modal or search contexts where applicable.
- No action depends only on hover or right click.
- Long translated text wraps or elides without hiding the primary action.
