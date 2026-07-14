"""QML application entry point. Does NOT import PySide6.QtWidgets or ui.* modules."""
from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("michi.qml_app")


def run_qml() -> int:
    """Start the QML application. Returns exit code."""
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")
    try:
        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine
    except ImportError as e:
        logger.error("Failed to import QML modules: %s", e)
        return 1

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setOrganizationName("Michi")

    engine = QQmlApplicationEngine()
    engine.addImportPath(os.path.join(os.path.dirname(__file__), "..", "ui_qml"))

    qml_path = os.path.join(os.path.dirname(__file__), "..", "ui_qml", "Main.qml")
    if not os.path.exists(qml_path):
        logger.error("Main.qml not found at %s", qml_path)
        return 1

    engine.load(qml_path)
    if not engine.rootObjects():
        logger.error("Failed to load QML root objects")
        return 1

    return app.exec()
