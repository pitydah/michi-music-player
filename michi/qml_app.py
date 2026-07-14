"""QML application entry point.

Only QML-related imports are allowed.
"""
from __future__ import annotations

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from importlib.metadata import version, PackageNotFoundError

from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine, qmlRegisterType
from PySide6.QtCore import QUrl

logger = logging.getLogger("michi.qml_app")


def _get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


def _qt_message_handler(mode, context, message):
    if "ERROR" in str(mode) or "FATAL" in str(mode):
        logger.error("Qt: %s — %s (%s:%d)", message, context.file or "", context.function or "", context.line or 0)


def run_qml():
    import faulthandler
    faulthandler.enable()
    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(_qt_message_handler)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setApplicationVersion(_get_app_version())

    from ui_qml_bridge.qml_main import _create_services
    from ui_qml_bridge.bridge_factory import BridgeFactory
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    from ui_qml_bridge.cover_bridge import CoverBridge

    engine = QQmlApplicationEngine()

    services = _create_services()
    registrar = ContextRegistrar(engine)

    factory = BridgeFactory(services)
    factory.create_navigation_bridge()
    all_bridges = factory.create_all()

    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = all_bridges.get(bridge_key)
        if bridge_key == "eq":
            bridge = factory.get("eq")
        if bridge is not None:
            registrar.register(qml_name, bridge)
        else:
            logger.debug("QML: Skipping '%s' (bridge not created)", qml_name)

    eq_bridge = factory.get("eq")
    if eq_bridge:
        registrar.register("eqBridge", eq_bridge)

    app_state = factory.get("app_state")
    if app_state:
        app_state.setServiceAvailability(
            services.player_service is not None,
            services.db is not None,
            "available" if services.player_service else "unavailable",
        )

    app_bridge = factory.get("app")
    if app_bridge:
        app_bridge.setPhase(app_bridge.__class__.PHASE_LOADING_QML)

    qmlRegisterType(CoverBridge, "MichiCover", 1, 0, "CoverBridge")

    qml_dir = Path(__file__).resolve().parent.parent / "ui_qml"
    engine.addImportPath(str(qml_dir))

    main_qml = qml_dir / "Main.qml"
    if not main_qml.exists():
        print(f"[QML] ERROR: Main.qml not found at {main_qml}", file=sys.stderr)
        sys.exit(1)

    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        print("[QML] ERROR: Failed to load QML root objects", file=sys.stderr)
        sys.exit(1)

    if app_bridge:
        app_bridge.setReady()

    audit = registrar.audit()
    logger.info("QML: Registered %d context properties", audit["total"])
    if audit["duplicates"]:
        logger.warning("QML: Duplicate context properties: %s", audit["duplicates"])

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
    run_qml()
