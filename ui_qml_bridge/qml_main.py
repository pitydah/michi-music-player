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
        pass

    # Device Sync
    try:
        from core.device_sync_service import DeviceSyncService
        bundle.device_sync_service = DeviceSyncService()
    except Exception as e:
        logger.debug("QML: DeviceSyncService init failed: %s", e)

    # Job Service
    try:
        from core.job_service import JobService
        bundle.job_service = JobService()
    except Exception as e:
        logger.debug("QML: JobService init failed: %s", e)

    # Confirmation Service
    try:
        from core.confirmation_service import ConfirmationService
        bundle.confirmation_service = ConfirmationService()
    except Exception as e:
        logger.debug("QML: ConfirmationService init failed: %s", e)

    # Audio Lab Service
    try:
        from core.audio_lab.audio_lab_service import AudioLabService
        als = AudioLabService(db=bundle.db, worker_manager=bundle.worker_manager)
        als.setup()
        bundle.audio_lab_service = als
    except Exception as e:
        logger.debug("QML: AudioLabService init failed: %s", e)

    logger.info("QML: Services available: %s", bundle.available_services)
    return bundle


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
