#!/usr/bin/python3
"""Michi Music Player — Plasma-native music player with KWin blur, Apple Music layout.

Self-contained. Python 3 + PySide6 + Qt Multimedia (GStreamer).
"""

import os
import sys


def _resolve_ui_mode() -> str:
    mode = os.environ.get("MICHI_UI", "auto").strip().lower()
    if mode not in ("widgets", "qml", "auto"):
        mode = "auto"
    return mode


def _try_qml() -> bool:
    from PySide6.QtCore import QTimer
    from PySide6.QtGui import QGuiApplication
    from PySide6.QtQml import QQmlApplicationEngine
    from PySide6.QtCore import QUrl
    from pathlib import Path

    app = QGuiApplication(sys.argv)
    engine = QQmlApplicationEngine()
    qml_dir = Path(__file__).resolve().parent / "ui_qml"
    main_qml = qml_dir / "Main.qml"
    if not main_qml.exists():
        print("[QML] ERROR: Main.qml not found", file=sys.stderr)
        return False

    engine.load(QUrl.fromLocalFile(str(main_qml)))
    app.processEvents()
    if not engine.rootObjects():
        print("[QML] ERROR: engine.load() returned no root objects", file=sys.stderr)
        engine.deleteLater()
        return False
    engine.deleteLater()
    QTimer.singleShot(0, app.quit)
    app.exec()
    return True


def _run_qml():
    from ui_qml_bridge.qml_main import main as qml_main
    qml_main()


def main():
    ui_mode = _resolve_ui_mode()

    if ui_mode == "qml":
        _run_qml()
        return

    if ui_mode == "auto":
        import logging
        logging.basicConfig(level=logging.INFO, format="[MICHI_UI] %(levelname)s: %(message)s")
        _log_auto = logging.getLogger("michi.ui_selector")
        _log_auto.info("MICHI_UI=auto — attempting QML...")
        try:
            _run_qml()
            return
        except Exception as e:
            _log_auto.error("QML failed: %s — falling back to QtWidgets", e)
            print(f"[MICHI_UI] QML error: {e}", file=sys.stderr)
            import gc
            for obj in gc.get_objects():
                if hasattr(obj, 'deleteLater'):
                    obj.deleteLater()

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
                lambda tid, err, code="": reporter.log_worker_error(tid, err, code))
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
