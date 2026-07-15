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

    if not bootstrap.load_qml(engine):
        sys.exit(1)

    logger.info("Michi Music Player %s — experimental QML UI", _get_app_version())

    try:
        exit_code = app.exec()
        logger.info("QML app exited with code %d", exit_code)
        sys.exit(exit_code)
    except Exception as e:
        logger.critical("QML app crashed: %s", e, exc_info=True)
        print(f"[QML] CRASH: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
