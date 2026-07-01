#!/usr/bin/python3
"""Michi Music Player — Plasma-native music player with KWin blur, Apple Music layout.

Self-contained. Python 3 + PySide6 + Qt Multimedia (GStreamer).
"""

import os
import sys


def main():
    if "--qml" in sys.argv:
        from ui_qml_bridge.qml_main import main as qml_main
        qml_main()
        return

    os.environ.setdefault("QT_MEDIA_BACKEND", "gstreamer")

    # Setup persistent logging before any other imports
    from core.logger import setup_logging, LOG_FILE
    setup_logging()
    import logging
    _log = logging.getLogger("michi.main")

    from PySide6.QtWidgets import QApplication
    from PySide6.QtGui import QFont
    from ui.theme import build_plasma_palette, PLASMA_QSS

    app = QApplication(sys.argv)
    app.setApplicationName("MichiMusicPlayer")
    app.setStyle("Fusion")
    app.setPalette(build_plasma_palette())
    app.setStyleSheet(PLASMA_QSS)

    # CrashReporter — captura integral de errores
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
        pass  # dialogo no disponible, reporte silencioso

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
        # Conectar errores de workers al reporter
        if hasattr(window, '_workers'):
            window._workers.task_error.connect(
                lambda tid, err: reporter.log_worker_error(tid, err))
        if hasattr(window, '_crash_reporter'):
            pass  # ya se instalo arriba
    except Exception as e:
        _log.exception("Fatal error creating MainWindow: %s", e)
        from PySide6.QtWidgets import QMessageBox
        QMessageBox.critical(
            None, "Michi Music Player — Error",
            f"Error fatal al iniciar:\n\n{e}\n\n"
            f"Revisa el log en {LOG_FILE}")
        sys.exit(1)

    # Initialize theme manager
    from ui.theme_manager import create_theme_manager
    theme_mgr = create_theme_manager(window)
    window._theme_mgr = theme_mgr

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
