# Guía de iconos — Michi Music Player

## Estructura de carpetas

```
icons/
├── app/              Icono principal (puede tener fondo)
├── sidebar/          Sidebar (SVG, currentColor, sin fondo)
├── sidebar_clean/    Sidebar PNG (alpha, 24px)
├── nowplaying_clean/ Acciones NowPlaying (PNG, 128px)
├── actions/          Acciones genéricas
├── tray/             System tray (symbolic + PNG)
├── view/             View switcher
├── folder.svg        Carpeta
└── ...
```

## Cómo añadir un icono nuevo

1. **Crear el SVG** con fondo transparente y `stroke="currentColor"`:
```svg
<svg xmlns="http://www.w3.org/2000/svg"
     width="24" height="24" viewBox="0 0 24 24" fill="none">
  <path d="..." stroke="currentColor" stroke-width="1.7"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
```

2. **Guardar** en la carpeta correcta según la familia:
   - `icons/sidebar/` — iconos del panel lateral
   - `icons/actions/` — botones de acción
   - `icons/view/` — modos de vista

3. **Registrar** en `ui/icon_registry.py`:
```python
"sidebar_mi_icono": IconSpec(
    key="sidebar_mi_icono",
    path="icons/sidebar/mi-icono.svg",
    family="sidebar",
    symbolic=True,
    description="Mi icono"),
```

4. **Auditar**:
```bash
python tools/audit_icons.py
```

5. **Probar** dark mode y light mode.

## Lo que NO debes hacer

- ❌ Usar `fill="#000"` en rect de fondo
- ❌ Usar PNG sin alpha en UI
- ❌ Usar rutas absolutas
- ❌ Duplicar iconos existentes
- ❌ Añadir iconos sin registrar

## Normalizar un SVG problemático

```bash
python tools/normalize_svg_icon.py icono.svg --family sidebar --out icons/sidebar/icono.svg
```

## Debug runtime

```bash
ASTRA_DEBUG_ICONS=1 python -m astra
```
