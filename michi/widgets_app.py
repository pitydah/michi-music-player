"""Widgets application entry point (legacy). Does NOT create QQmlEngine."""
from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("michi.widgets_app")


def run_widgets() -> int:
    """Start the Widgets application. Returns exit code."""
    os.environ.setdefault("QT_MEDIA_BACKEND", "gstreamer")
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as e:
        logger.error("Failed to import QtWidgets: %s", e)
        return 1

    from core.logger import setup_logging, LOG_FILE
    setup_logging()
    _log = logging.getLogger("michi.widgets_app")

    app = QApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setStyle("Fusion")

    from PySide6.QtGui import QFont
    from ui.theme import build_plasma_palette, PLASMA_QSS
    app.setPalette(build_plasma_palette())
    app.setStyleSheet(PLASMA_QSS)

    font = QFont("Inter", 11)
    if not font.exactMatch():
        font = QFont("SF Pro Display", 11)
    if not font.exactMatch():
        font = QFont("sans-serif", 11)
    app.setFont(font)

    from core.crash_reporter import CrashReporter
    reporter = CrashReporter()

    try:
        from ui.window import MainWindow
        window = MainWindow()
        window.show()
        if hasattr(window, "_workers"):
            window._workers.task_error.connect(
                lambda tid, err, code="": reporter.log_worker_error(tid, err, code))
    except Exception as e:
        _log.exception("Fatal error creating MainWindow: %s", e)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Michi Music Player — Error",
            f"Error fatal al iniciar:\n\n{e}\n\n"
            f"Revisa el log en {LOG_FILE}")
        return 1

    from ui.theme_manager import create_theme_manager
    theme_mgr = create_theme_manager(window)
    window._theme_mgr = theme_mgr

    return app.exec()
