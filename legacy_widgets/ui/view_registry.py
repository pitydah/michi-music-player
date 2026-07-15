"""View Registry — centralized lazy view creation with safe-mode gating.

Replaces direct widget instantiation in window.py's _setup_ui().
Optional views load only when first accessed. Errors produce placeholders.
"""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger("michi.view_registry")


def _placeholder_widget(title: str, message: str) -> QWidget:
    """Safe placeholder when an optional view cannot be loaded."""
    w = QWidget()
    w.setStyleSheet("background: #090B11;")
    vl = QVBoxLayout(w)
    vl.setAlignment(Qt.AlignCenter)
    t = QLabel(title)
    t.setAlignment(Qt.AlignCenter)
    t.setStyleSheet(
        "QLabel { color: rgba(255,255,255,0.62); font-size: 16px; font-weight: 600; }")
    vl.addWidget(t)
    m = QLabel(message)
    m.setAlignment(Qt.AlignCenter)
    m.setWordWrap(True)
    m.setStyleSheet(
        "QLabel { color: rgba(255,255,255,0.48); font-size: 12px; }")
    vl.addWidget(m)
    return w


class ViewRegistry:
    """Lazy view factory with safe-mode gating and placeholder fallback."""

    def __init__(self, safe_mode: bool = False):
        self._factories: dict[str, tuple[Callable, dict]] = {}
        self._views: dict[str, QWidget] = {}
        self._safe_mode = safe_mode

    def register(self, key: str, factory: Callable[[], QWidget],
                 *, experimental: bool = False,
                 title: str = "", description: str = ""):
        """Register a view factory. Experimental views are blocked in safe mode."""
        self._factories[key] = (factory, {
            "experimental": experimental,
            "title": title or key,
            "description": description or "",
        })

    def get(self, key: str) -> QWidget:
        """Get or create a view. Returns placeholder on error or safe-mode block."""
        if key in self._views:
            return self._views[key]

        entry = self._factories.get(key)
        if not entry:
            return _placeholder_widget(key, "Vista no registrada")

        factory, meta = entry
        if meta["experimental"] and self._safe_mode:
            return _placeholder_widget(
                meta["title"],
                "Desactivada en modo seguro.")

        try:
            view = factory()
            self._views[key] = view
            return view
        except Exception as e:
            logger.warning("Failed to create view '%s': %s", key, e)
            return _placeholder_widget(
                meta["title"],
                f"Error al cargar: {e}")

    def has(self, key: str) -> bool:
        return key in self._views

    def preload(self, *keys: str):
        """Eager-load core views (call after main window is shown)."""
        for k in keys:
            self.get(k)
