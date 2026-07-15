"""QML entry point — delegates to ApplicationBootstrap.
Does not duplicate bootstrap logic.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtGui import QGuiApplication

from core.application_bootstrap import ApplicationBootstrap

logging.basicConfig(level=logging.INFO, format="[QML] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("michi.qml")


def _get_app_version() -> str:
    try:
        from importlib.metadata import version
        return version("michi-music-player")
    except Exception:
        return "0.2.0-alpha.1"


def _qt_message_handler(mode, context, message):
    if "ERROR" in str(mode) or "FATAL" in str(mode):
        logger.error("Qt: %s — %s (%s:%d)", message, context.file or "", context.function or "", context.line or 0)


def main():
    import faulthandler
    faulthandler.enable()

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setApplicationVersion(_get_app_version())

    from PySide6.QtQml import QQmlApplicationEngine
    engine = QQmlApplicationEngine()

    bootstrap = ApplicationBootstrap()
    bootstrap.build().start()
    bootstrap.create_bridges()
    bootstrap.register_context(engine)
    bootstrap.load_qml(engine)

    if not engine.rootObjects():
        logger.error("Failed to load QML root objects")
        return 1

    logger.info("QML: READY")
    code = app.exec()

    logger.info("QML: SHUTTING_DOWN")
    bootstrap.shutdown()
    logger.info("QML: STOPPED")
    return code


if __name__ == "__main__":
    sys.exit(main())
