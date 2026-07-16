"""KDE blur backend — safe no-op placeholder.

Actual KDE blur integration (KWindowSystem) is planned for a future iteration.
This module exists to centralize all window-composition calls in one place.
"""

from __future__ import annotations


def is_available() -> bool:
    return False


def enable_window_blur(window_id: int = 0) -> bool:
    return False


def enable_background_contrast(window_id: int = 0) -> bool:
    return False
