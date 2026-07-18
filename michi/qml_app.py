"""QML application entry point — uses ApplicationBootstrap for productive composition."""
from __future__ import annotations

import logging
import os
import sys

from PySide6.QtCore import QTranslator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [QML] %(levelname)s: %(message)s")
logger = logging.getLogger("michi.qml_app")


def run_qml() -> int:
    os.environ.setdefault("QT_QPA_PLATFORM", "wayland;xcb")
    os.environ.setdefault("QT_WAYLAND_DISABLE_WINDOWDECORATION", "1")
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as e:
        logger.error("Failed to import QML modules: %s", e)
        return 1

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setOrganizationName("Michi")

    from core.application_bootstrap import ApplicationBootstrap

    # Load translation
    translator = QTranslator()
    from core.settings_manager import SETTINGS
    locale = SETTINGS.value("appearance/language", "es")
    qm_path = os.path.join(os.path.dirname(__file__), "..", "translations", f"michi_{locale}.qm")
    if os.path.exists(qm_path):
        if translator.load(qm_path):
            app.installTranslator(translator)
            logger.info("Loaded translation: %s", qm_path)
        else:
            logger.warning("Failed to load translation: %s", qm_path)

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(os.path.dirname(__file__), "..", "ui_qml"))

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.build()
        bootstrap.start()
        bootstrap.create_bridges()
        bootstrap.register_context(engine)
        bootstrap.load_qml(engine)

        if not engine.rootObjects():
            logger.error("Failed to load QML root objects")
            return 1

        logger.info("Michi Music Player QML — READY")
        return app.exec()
    finally:
        try:
            bootstrap.shutdown()
        except Exception as shutdown_err:
            logger.warning("Shutdown error: %s", shutdown_err)
