# Codex UI Token Gaps

The existing singleton architecture is retained. Separate token files were not added because the same categories already belong to `MichiTheme`, `MichiColors`, `MichiTypography` and `MichiMotion`.

| Category | Existing reused | Added |
|---|---|---|
| Breakpoints | None | compact 800, regular 1280, wide 1920 |
| Page margins | `spacing.lg/xl/page` | compact/regular/wide aliases |
| Controls | header/now-playing sizes | toolbar, compact/comfortable row, minimum interactive size |
| Covers | Ad hoc sizes | small 48, medium 128, large 224, shared radius |
| Focus | `borderWidthFocus`, `borderFocus` | focus width and offset |
| Opacity | disabled/hover/active | compatibility aliases using existing values |
| Motion | fast/normal/slow | public motion aliases and reduced duration |
| Typography | body/meta/badge | caption size |
| Semantic colors | card/accent/borders | hover, pressed, disabled, track, thumb, focus halo, skeleton |

## Remaining gaps

- A validated high-contrast palette mode.
- Platform-derived reduced-motion preference.
- Density preference persistence.
- Dedicated semantic assets for search, close, more, warning and error.
- Automated contrast measurement for glass over artwork.
