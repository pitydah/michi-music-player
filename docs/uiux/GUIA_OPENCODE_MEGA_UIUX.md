# Guía estricta para OpenCode — Mega UI/UX

## Objetivo

Aplicar el parche literalmente sobre el estado que ya contiene los parches de
fundamentos premium, sidebar, Biblioteca contextual, Now Playing premium y la
corrección del selector de vistas.

## Reglas

1. No restaures `radioSearch`, `playlistSearch` ni una búsqueda local en
   `LibraryPage`.
2. No restaures los overlays internos eliminados de `PageStack`.
3. No cambies el hover de `MichiIconButton` a `radius.pill`; `circular` es una
   excepción explícita.
4. No sustituyas los SVG por Unicode, emoji o abreviaturas de dos letras.
5. No copies texturas externas al repositorio.
6. No muevas el acento cálido de Now Playing/EQ al resto de la aplicación.
7. No deshabilites, marques como `skip` ni borres pruebas.
8. No reviertas `ZoneDetailPage.qml`: el archivo anterior estaba truncado.
9. No edites lógica de reproducción para resolver un problema visual.
10. No cambies archivos de Michi AI que no estén incluidos en el parche.

## Aplicación

```bash
git apply --check michi-uiux-mega-refactor.patch
git apply michi-uiux-mega-refactor.patch
```

## Validación mínima

```bash
python scripts/audit_qml_ui.py --strict
git diff --check
python -m py_compile \
  scripts/audit_qml_ui.py \
  tests/qml/test_uiux_system_contract.py \
  tests/qml/keyboard/test_playlists_keyboard.py
```

Con PySide6 y pytest:

```bash
pytest -q tests/qml/test_uiux_system_contract.py
pytest -q tests/qml/test_qml_components.py
pytest -q tests/qml/test_qml_compile_all.py
pytest -q tests/qml/test_qml_instance_all.py
python main.py --qml
```

## Revisión visual

Verifica como mínimo:

- Inicio, Biblioteca, Radio, Playlists, Mix, Conexiones, Audio Lab y Home Audio.
- Temas oscuro y claro.
- Anchos de 800, 1024, 1200, 1600 y 2560 px.
- Navegación completa con Tab, Shift+Tab, Enter, Espacio y Escape.
- Foco de 2 px visible.
- Textura sin interferir con texto ni carátulas.
- Carga/error únicos.
- `zone_detail` con volumen, mute, fuente, latencia, renombrado y eliminación.

Si una prueba antigua exige un buscador local o un overlay duplicado, actualiza
la prueba para validar el contrato contextual; no restaures la UI anterior.
