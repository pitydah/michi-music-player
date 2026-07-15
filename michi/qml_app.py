"""QML application entry point. Does NOT import QtWidgets or ui.* modules."""
from __future__ import annotations

import logging
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("michi.qml_app")


def run_qml() -> int:
    """Start the QML application. Returns exit code."""
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as e:
        logger.error("Failed to import QML modules: %s", e)
        return 1

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setOrganizationName("Michi")

    engine = QQmlApplicationEngine()
    from core.application_bootstrap import ApplicationBootstrap

    bootstrap = ApplicationBootstrap()
    try:
        bootstrap.run(engine)
    except Exception:
        logger.exception("QML bootstrap failed")
        bootstrap.shutdown()
        return 1

    if not engine.rootObjects():
        bootstrap.shutdown()
        return 1

    app.aboutToQuit.connect(bootstrap.shutdown)
    return app.exec()
