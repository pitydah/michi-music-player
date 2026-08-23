"""Domain layer — application settings. No Qt/infrastructure."""

import json
from dataclasses import dataclass, field

from michi.domain.audio_engine import AudioEngineId


@dataclass(frozen=True)
class WindowGeometry:
    """Restorable window placement. Pure — no Qt/QRect.

    Negative x/y are legitimate (multi-monitor layouts); width/height are
    always positive in a valid geometry.
    """

    x: int | None = None
    y: int | None = None
    width: int = 1100
    height: int = 700
    maximized: bool = False


@dataclass
class SettingsState:
    volume: int = 80  # 0-100
    muted: bool = False
    last_directory: str = ""
    recent_files: list[str] = field(default_factory=list)
    theme: str = "dark"
    window_geometry: WindowGeometry = WindowGeometry()
    online_enrichment: bool = False  # M6.9 privacy: network DEFAULT OFF
    # M11.3F: persisted user engine preference (SELECTED intent — never the
    # ACTIVE engine). Missing/malformed preference falls back to Qt.
    audio_engine_id: AudioEngineId = AudioEngineId.QT_MULTIMEDIA


def window_geometry_to_json(geometry: WindowGeometry) -> str:
    """Strict JSON serialization of a WindowGeometry (canonical key order)."""
    return json.dumps(
        {
            "x": geometry.x,
            "y": geometry.y,
            "width": geometry.width,
            "height": geometry.height,
            "maximized": geometry.maximized,
        }
    )


def window_geometry_from_json(raw: object) -> tuple[WindowGeometry, bool]:
    """Decode a persisted window_geometry value into (geometry, malformed).

    M11.2C field fallback rules: a missing row is not this function's
    concern (callers default silently); a present row must be strict JSON
    whose width/height keys exist and are positive integers. x/y may be
    null or any integer (negative is legitimate), and default to None when
    missing; maximized defaults to False and must be a boolean when
    present. Any violation falls back to the default WindowGeometry with
    malformed=True.
    """
    if not isinstance(raw, str):
        return WindowGeometry(), True
    try:
        parsed = json.loads(raw)
    except (TypeError, ValueError):
        return WindowGeometry(), True
    if not isinstance(parsed, dict):
        return WindowGeometry(), True

    def _is_int(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool)

    width = parsed.get("width")
    height = parsed.get("height")
    if not _is_int(width) or not _is_int(height) or width <= 0 or height <= 0:
        return WindowGeometry(), True

    x = parsed.get("x")
    y = parsed.get("y")
    if x is not None and not _is_int(x):
        return WindowGeometry(), True
    if y is not None and not _is_int(y):
        return WindowGeometry(), True

    maximized = parsed.get("maximized", False)
    if not isinstance(maximized, bool):
        return WindowGeometry(), True

    return (
        WindowGeometry(x=x, y=y, width=width, height=height, maximized=maximized),
        False,
    )
