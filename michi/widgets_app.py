"""QtWidgets application entry point.

Contains all legacy QtWidgets logic from main.py.
"""
from __future__ import annotations

import os
import sys

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont


def run_widgets():
    os.environ.setdefault("QT_MEDIA_BACKEND", "gstreamer")

    from core.logger import setup_logging, LOG_FILE
    setup_logging()
    import logging
    _log = logging.getLogger("michi.widgets_app")

    from ui.theme import build_plasma_palette, PLASMA_QSS

    app = QApplication(sys.argv)
    app.setApplicationName("MichiMusicPlayer")
    app.setStyle("Fusion")
    app.setPalette(build_plasma_palette())
    app.setStyleSheet(PLASMA_QSS)

    from core.crash_reporter import CrashReporter
    reporter = CrashReporter()
    try:
        from ui.dialogs.crash_dialog import CrashDialog

        def _show_crash_dialog(report_path):
            try:
                dialog = CrashDialog(report_path)
                dialog.exec()
            except Exception:
                pass
        reporter.crash_occurred.connect(_show_crash_dialog)
    except Exception:
        pass

    font = QFont("Inter", 11)
    if not font.exactMatch():
        font = QFont("SF Pro Display", 11)
    if not font.exactMatch():
        font = QFont("sans-serif", 11)
    app.setFont(font)

    try:
        from ui.window import MainWindow
        window = MainWindow()
        window.show()
        if hasattr(window, '_workers'):
            window._workers.task_error.connect(
                lambda tid, err, code="": reporter.log_worker_error(tid, err, code))
    except Exception as e:
        _log.exception("Fatal error creating MainWindow: %s", e)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Michi Music Player — Error",
            f"Error fatal al iniciar:\n\n{e}\n\n"
            f"Revisa el log en {LOG_FILE}")
        sys.exit(1)

    from ui.theme_manager import create_theme_manager
    theme_mgr = create_theme_manager(window)
    window._theme_mgr = theme_mgr

    sys.exit(app.exec())
