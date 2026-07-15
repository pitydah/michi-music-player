"""Safe view factory — creates optional views with placeholder fallback on error."""

from __future__ import annotations

import logging
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger("michi.view_factory")


def make_placeholder(title: str, message: str, details: str = "") -> QWidget:
    """Create a safe placeholder widget shown when a view fails to load."""
    w = QWidget()
    w.setStyleSheet("background: #090B11;")
    vl = QVBoxLayout(w)
    vl.setAlignment(Qt.AlignCenter)
    vl.setSpacing(6)

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

    if details:
        d = QLabel(details)
        d.setAlignment(Qt.AlignCenter)
        d.setWordWrap(True)
        d.setStyleSheet(
            "QLabel { color: rgba(255,255,255,0.35); font-size: 11px; }")
        vl.addWidget(d)

    return w


def safe_create_view(
    key: str,
    factory: Callable[[], QWidget],
    title: str = "",
    *,
    _logger=None,
) -> QWidget:
    """Create a view via factory. On error, return a placeholder. Never returns None."""
    log = _logger or logger
    try:
        return factory()
    except Exception as e:
        log.warning("View '%s' failed to load — placeholder: %s", key, e)
        return make_placeholder(
            title or key,
            f"Esta sección no pudo cargarse.\n{type(e).__name__}: {e}",
            details="",
        )
