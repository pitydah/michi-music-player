"""QML safe mode verification entry point.
Loads services and QML engine; runs headless for CI validation."""
from __future__ import annotations

import logging
import os
import sys

logging.basicConfig(level=logging.INFO, format="%(levelname)s:%(name)s:%(message)s")
logger = logging.getLogger("michi.verify_app")


def run_verify() -> int:
    """Start QML in safe/verify mode. Returns exit code."""
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ["MICHI_SAFE_MODE"] = "1"

    try:
        from core.application_bootstrap import ApplicationBootstrap

        bootstrap = ApplicationBootstrap()
        bootstrap.build()
        bootstrap.start()

        from PySide6.QtGui import QGuiApplication
        from PySide6.QtQml import QQmlApplicationEngine

        app = QGuiApplication(sys.argv)
        app.setApplicationName("Michi Music Player")
        app.setOrganizationName("Michi")
        app.setOrganizationDomain("michi.app")
        engine = QQmlApplicationEngine()

        bootstrap.create_bridges()
        bootstrap.register_context(engine)

        engine.addImportPath(os.path.join(os.path.dirname(__file__), "..", "ui_qml"))
        qml_path = os.path.join(os.path.dirname(__file__), "..", "ui_qml", "Main.qml")
        if not os.path.exists(qml_path):
            logger.error("Main.qml not found at %s", qml_path)
            return 1

        engine.load(qml_path)
        if not engine.rootObjects():
            logger.error("Failed to load QML root objects")
            return 1

        bootstrap.shutdown()
        logger.info("QML verify mode OK")
        return 0

    except Exception as e:
        logger.error("QML verify failed: %s", e)
        return 1
