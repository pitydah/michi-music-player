"""Icon Loader — centralized icon resolution with tinting, caching, validation."""
import os
import logging
from pathlib import Path
from functools import lru_cache

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QIcon

from ui.icon_registry import ICON_REGISTRY
from ui.icon_renderer import render_svg_icon

HERE = Path(__file__).parent.parent
BREEZE = "/usr/share/icons/breeze"

_log = logging.getLogger("michi.icons")

# ── Color tokens for tinting ──

SIDEBAR_NORMAL = QColor(255, 255, 255, 217)   # rgba(255,255,255,0.85)
SIDEBAR_HOVER = QColor(255, 255, 255, 245)    # rgba(255,255,255,0.96)
SIDEBAR_ACTIVE = QColor(255, 255, 255, 255)   # #FFFFFF
SIDEBAR_MUTED = QColor(255, 255, 255, 92)     # rgba(255,255,255,0.36)


@lru_cache(maxsize=128)
def _cache_key_func(key, color_str, size):
    return (key, color_str or "", size)


def icon_path(key: str) -> str:
    """Return absolute path for an icon key, or '' if not found."""
    spec = ICON_REGISTRY.get(key)
    if not spec:
        return ""
    p = Path(spec.path)
    full = p if p.is_absolute() else HERE / spec.path
    if full.exists():
        return str(full)
    # Theme fallback
    if spec.theme_fallback:
        fb = os.path.join(BREEZE, spec.theme_fallback)
        if not fb.endswith(".svg"):
            fb += ".svg"
        if os.path.exists(fb):
            return fb
    return ""


def get_icon(key: str) -> str:
    """Compatibility wrapper — returns path string."""
    return icon_path(key)


def _svg_padding_for_spec(spec, default: int = 1) -> int:
    """Return safe padding for SVG icons by UI family."""
    if spec and spec.family in ("action", "view"):
        return 0   # no padding — these SVGs have tight viewBox
    if spec and spec.family == "tray":
        return 4   # tray icons render larger
    return default  # sidebar: 1-2px padding


def get_qicon(key: str, color: QColor | None = None, size: int = 24) -> QIcon:
    """Return a QIcon with optional tinting, always alpha-safe for SVGs."""
    from ui.icon_registry import ICON_REGISTRY
    path = icon_path(key)
    if not path:
        return _missing_icon(color, size)

    spec = ICON_REGISTRY.get(key)
    is_svg = path.lower().endswith(".svg")
    is_native = spec and spec.render_mode == "native_color"

    if is_svg:
        if color and not is_native:
            return QIcon(_tinted_pixmap(path, color, size))
        padding = _svg_padding_for_spec(spec, default=1)
        return QIcon(render_svg_icon(path, size, padding=padding))

    # PNG
    if color:
        pix = _tinted_pixmap(path, color, size)
        return QIcon(pix)
    return QIcon(path)


def get_pixmap(key: str, color: QColor | None = None, size: int = 24) -> QPixmap:
    """Return a QPixmap with optional tinting (only for symbolic_tint).
    All SVGs pass through the alpha-safe renderer."""
    spec = ICON_REGISTRY.get(key)
    path = icon_path(key)
    if not path:
        return _missing_pixmap(color, size)

    is_svg = path.lower().endswith(".svg")
    is_native = spec and spec.render_mode == "native_color"

    if is_svg:
        if is_native:
            padding = _svg_padding_for_spec(spec, default=1)
            return render_svg_icon(path, size, padding=padding)
        if color:
            return _tinted_pixmap(path, color, size)
        padding = _svg_padding_for_spec(spec, default=1)
        return render_svg_icon(path, size, padding=padding)

    # PNG — native_color never gets tinted, symbolic may
    if is_native:
        pix = QPixmap(path)
        if pix.isNull():
            return _missing_pixmap(color, size)
        return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    if color:
        return _tinted_pixmap(path, color, size)
    pix = QPixmap(path)
    if pix.isNull():
        return _missing_pixmap(color, size)
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def get_sidebar_icon(key: str, active: bool = False, hover: bool = False,
                     size: int = 22) -> QPixmap:
    """Get sidebar icon with correct tinting for SVGs, direct load for PNGs."""
    spec = ICON_REGISTRY.get(key)
    path = icon_path(key)
    if not path:
        return _missing_pixmap(SIDEBAR_NORMAL, size)
    # PNGs already have correct color — load directly
    if path.lower().endswith(".png"):
        pix = QPixmap(path)
        if not pix.isNull():
            return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return _missing_pixmap(SIDEBAR_NORMAL, size)
    # native_color SVGs: render preserving original colors (no tinting)
    if spec and spec.render_mode == "native_color":
        return render_svg_icon(path, size, padding=1)
    # symbolic_tint SVGs get tinted to match text opacity
    if active:
        return get_pixmap(key, SIDEBAR_ACTIVE, size)
    if hover:
        return get_pixmap(key, SIDEBAR_HOVER, size)
    return get_pixmap(key, SIDEBAR_NORMAL, size)


def get_tray_icon() -> QIcon:
    """Return the system tray icon."""
    from ui.icon_registry import ICON_REGISTRY
    path = icon_path("tray_icon")
    if path:
        spec = ICON_REGISTRY.get("tray_icon")
        padding = _svg_padding_for_spec(spec, default=4)
        pix = render_svg_icon(path, 64, padding=padding)
        return QIcon(pix)
    # Fallback to app icon
    app_path = HERE / "icons" / "app_icon.png"
    if app_path.exists():
        return QIcon(str(app_path))
    return _missing_icon(None, 24)


def app_icon() -> str:
    """Return path to the main app icon."""
    path = HERE / "icons" / "app_icon.png"
    return str(path) if path.exists() else ""


def validate_icon_key(key: str) -> bool:
    """Check if an icon key is registered and the file exists."""
    return bool(icon_path(key))


# ── Internal helpers ──

def _tinted_pixmap(path: str, color: QColor, size: int) -> QPixmap:
    """Load an image and apply a tint color using composition."""
    pix = QPixmap(path)
    if pix.isNull():
        return _missing_pixmap(color, size)
    overlay = QPixmap(pix.size())
    overlay.fill(color)
    painter = QPainter(pix)
    painter.setCompositionMode(QPainter.CompositionMode_SourceIn)
    painter.drawPixmap(0, 0, overlay)
    painter.end()
    return pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)


def _missing_icon(color: QColor | None, size: int) -> QIcon:
    """Return a fallback QIcon."""
    pix = _missing_pixmap(color, size)
    return QIcon(pix)


def _missing_pixmap(color: QColor | None, size: int) -> QPixmap:
    """Draw a generic transparent fallback pixmap."""
    pix = QPixmap(size, size)
    pix.fill(Qt.transparent)
    painter = QPainter(pix)
    painter.setRenderHint(QPainter.Antialiasing)
    c = color or QColor("#c7c7cc")
    painter.setPen(QPen(c, 1.5))
    painter.setBrush(QColor(c.red(), c.green(), c.blue(), 40))
    painter.drawRoundedRect(2, 2, size - 4, size - 4, 4, 4)
    # Question mark
    painter.setPen(QPen(c, 1.5))
    painter.drawText(pix.rect(), Qt.AlignCenter, "?")
    painter.end()
    return pix


# ── Debug runtime validator ──

if os.environ.get("ASTRA_DEBUG_ICONS"):
    import xml.etree.ElementTree as ET

    def _check_black_bg(path: str):
        if not path.endswith(".svg"):
            return
        try:
            tree = ET.parse(path)
            root = tree.getroot()
            for rect in root.iter("{http://www.w3.org/2000/svg}rect"):
                fill = rect.get("fill", "").lower()
                if fill in ("#000", "#000000", "black", "rgb(0,0,0)", "rgb(0, 0, 0)"):
                    _log.warning("Icon %s contains black rect background", path)
                    return
            for elem in root.iter():
                style = elem.get("style", "")
                if "background" in style.lower():
                    _log.warning("Icon %s contains background style: %s", path, style)
        except Exception:
            pass
