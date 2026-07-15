"""Icon resolution — custom SVGs first, then Breeze system, then generic fallback.
This is a compatibility wrapper over ui.icon_loader."""
from pathlib import Path

from ui.icon_loader import (
    icon_path, get_qicon, get_pixmap, get_sidebar_icon,
    get_tray_icon, app_icon, validate_icon_key,
)

HERE = Path(__file__).parent.parent
BREEZE = "/usr/share/icons/breeze"


def get_icon(name: str) -> str:
    """Returns absolute path to icon file. Legacy compatibility API."""
    return icon_path(name)


def get_icon_qicon(name: str):
    """Returns QIcon with generic fallback. Legacy compatibility API."""
    return get_qicon(name)


# Re-export for existing importers
__all__ = [
    "get_icon", "get_icon_qicon", "app_icon",
    "get_qicon", "get_pixmap", "get_sidebar_icon",
    "get_tray_icon", "validate_icon_key",
]
