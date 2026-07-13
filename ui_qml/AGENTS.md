# Michi QML UI Rules

Scope: everything below `ui_qml/`.

## Visual identity

Michi is a sober, premium Linux/KDE music player. Use restrained smoked glass, medium density, strong contrast, monochrome icons and controlled accents. Do not imitate Apple Music, Spotify or Roon.

## Required practices

- Use `MichiTheme` for color, spacing, type, radius, motion and control sizes.
- Extend existing components before adding another variant.
- Keep foundation, state, layout and content components presentational.
- Support Qt 6 and PySide6 6.7 or newer.
- Preserve usable layouts from 800x600 through 3840x2160.
- Use compact, regular and wide behavior from `MichiResponsive`.
- Keep interactive targets at least `MichiTheme.minimumInteractiveSize`.
- Provide visible keyboard focus and Enter/Space activation.
- Add configurable `Accessible.name`; add descriptions for unavailable or destructive actions.
- Respect reduced motion for optional animation while preserving feedback.

## Prohibited practices

- No hardcoded colors outside the theme.
- No `ActionButton`.
- No Unicode or abbreviated text as a primary icon.
- No direct bridge, service, model, SQLite or context-property access from foundations.
- No production routes for files under `ui_qml/dev/`.
- No backend simulation outside the development gallery.

## Validation

```bash
ruff check .
python -m compileall -q -x '.venv/|\.tmpl\.' .
QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/test_qml_components.py -q
QT_QPA_PLATFORM=offscreen python -m pytest tests/qml/ -q
```

The consolidated UI foundation tests cover loading, states, controls, accessibility, responsive behavior and the gallery while keeping the branch within its 30-new-file limit.
