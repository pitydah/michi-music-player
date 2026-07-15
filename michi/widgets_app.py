"""Widgets application entry point (fallback legacy). Does NOT create QQmlApplicationEngine."""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("michi.widgets_app")


def run_widgets() -> int:
    """Start the Widgets application. Returns exit code."""
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        logger.error("Failed to import QtWidgets: %s", e)
        return 1

    app = QApplication(sys.argv)
    app.setApplicationName("Michi Music Player (Widgets)")
    app.setOrganizationName("Michi")

    from main import MainWindow
    window = MainWindow()
    window.show()

    return app.exec()
