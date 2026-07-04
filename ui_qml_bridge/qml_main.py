"""QML entry point — creates real services and bridges for the experimental QML UI.

Safe to import from main.py via --qml flag.
Does not depend on MainWindow or QtWidgets.
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

from ui_qml_bridge.service_bundle import ServiceBundle
from ui_qml_bridge.bridge_factory import BridgeFactory
from ui_qml_bridge.context_registrar import ContextRegistrar
from ui_qml_bridge.cover_bridge import CoverBridge
from ui_qml_bridge.mix_bridge import MixBridge  # noqa: F401 — imported for test visibility

logging.basicConfig(level=logging.INFO, format="[QML] %(levelname)s: %(message)s", stream=sys.stderr)
logger = logging.getLogger("michi.qml")


def _get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


def _create_services() -> ServiceBundle:
    """Create all real backend services, return ServiceBundle.

    Each service creation is independent — failure of one does not block others.
    """
    bundle = ServiceBundle()

    # Database
    try:
        from library.library_db import LibraryDB
        from core.paths import database_path
        db_path = Path(database_path())
        db_path.parent.mkdir(parents=True, exist_ok=True)
        bundle.db = LibraryDB(str(db_path))
        bundle.db_connection = getattr(bundle.db, 'conn', None)
        logger.info("QML: LibraryDB opened at %s", db_path)
    except Exception as e:
        logger.debug("QML: LibraryDB init failed: %s", e)

    # Player
    try:
        from audio.player import GStreamerEngine
        from audio.player_service import PlayerService
        logger.info("QML: Creating GStreamerEngine...")
        engine = GStreamerEngine()
        logger.info("QML: GStreamerEngine created OK, creating PlayerService...")
        bundle.player_service = PlayerService(engine)
        logger.info("QML: PlayerService created OK")
    except ImportError as e:
        logger.warning("QML: PlayerService ImportError — %s", e)
    except Exception as e:
        logger.warning("QML: PlayerService init failed: %s — %s", type(e).__name__, e)

    # Search
    if bundle.db:
        try:
            from library.search_engine import SearchEngine
            bundle.search_engine = SearchEngine(bundle.db)
        except Exception as e:
            logger.debug("QML: SearchEngine init failed: %s", e)

    # Radio
    try:
        from streaming.radio_manager import RadioManager
        bundle.radio_manager = RadioManager()
        logger.info("QML: RadioManager created")
    except Exception as e:
        logger.debug("QML: RadioManager init failed: %s", e)

    # Sync
    if bundle.db:
        try:
            from sync.sync_manager import SyncManager
            bundle.sync_manager = SyncManager(bundle.db)
            logger.info("QML: SyncManager created")
        except Exception as e:
            logger.debug("QML: SyncManager init failed: %s", e)

    # Home Audio & Snapcast adapters (no MainWindow needed)
    try:
        from integrations.home_assistant.client import HomeAssistantClient
        from ui_qml_bridge.adapters.home_audio_adapter import HomeAudioAdapter
        bundle.home_audio_controller = HomeAudioAdapter(ha_client=HomeAssistantClient())
        logger.info("QML: HomeAudioAdapter created")
    except Exception as e:
        logger.debug("QML: HomeAudioAdapter init failed: %s", e)

    try:
        from integrations.snapcast.group_manager import GroupManager
        from ui_qml_bridge.adapters.snapcast_adapter import SnapcastAdapter
        gm = GroupManager()
        bundle.snapcast_controller = SnapcastAdapter(group_manager=gm)
        logger.info("QML: SnapcastAdapter created")
    except Exception as e:
        logger.debug("QML: SnapcastAdapter init failed: %s", e)

    # Michi Link
    try:
        from integrations.michi_link.services.service_manager import ServiceManager
        bundle.michi_link_controller = ServiceManager()
        logger.info("QML: MichiLink ServiceManager created")
    except Exception as e:
        logger.debug("QML: MichiLink init failed: %s", e)

    # Disc Detection Service
    try:
        from ui.audio_lab.services.disc_detection_service import DiscDetectionService
        bundle.disc_service = DiscDetectionService()
        logger.info("QML: DiscDetectionService created")
    except Exception as e:
        logger.debug("QML: DiscDetectionService init failed: %s", e)

    # Metadata Service
    try:
        from ui.audio_lab.services.smart_tagging_service import SmartTaggingService
        bundle.smart_tagging_service = SmartTaggingService()
        bundle.metadata_service = bundle.smart_tagging_service
    except Exception as e:
        logger.debug("QML: SmartTagging init failed: %s", e)

    logger.info("QML: Services available: %s", bundle.available_services)
    return bundle


def _qt_message_handler(mode, context, message):
    if "ERROR" in str(mode) or "FATAL" in str(mode):
        logger.error("Qt: %s — %s (%s:%d)", message, context.file or "", context.function or "", context.line or 0)


def main():
    import faulthandler
    faulthandler.enable()
    from PySide6.QtCore import qInstallMessageHandler
    qInstallMessageHandler(_qt_message_handler)

    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setApplicationVersion(_get_app_version())

    engine = QQmlApplicationEngine()

    services = _create_services()
    registrar = ContextRegistrar(engine)

    # Create navigation bridge first (needed by others)
    factory = BridgeFactory(services)
    factory.create_navigation_bridge()

    # Create all bridges
    all_bridges = factory.create_all()

    # Register context properties
    bridge_names = {
        "appBridge": "app",
        "navigationBridge": "navigation",
        "commandBus": None,
        "themeBridge": "theme",
        "libraryBridge": "library",
        "michiAiBridge": "michi_ai",
        "metadataBridge": "metadata",
        "mixBridge": "mix",
        "playbackBridge": "playback",
        "nowplayingBridge": "nowplaying",
        "devicesBridge": "devices",
        "playlistsBridge": "playlists",
        "audioLabBridge": "audio_lab",
        "settingsBridge": "settings",
        "radioBridge": "radio",
        "connectionsBridge": "connections",
        "smartTaggingBridge": "smart_tagging",
        "libraryDoctorBridge": "library_doctor",
        "discLabBridge": "disc_lab",
        "selectionContextBridge": "selection_context",
        "homeAudioBridge": "home_audio",
        "lyricsBridge": "lyrics",
        "notificationBridge": "notification",
        "routeRegistryBridge": "route_registry",
        "appStateBridge": "app_state",
        "diagnosticsBridge": "diagnostics",
        "commandPaletteBridge": "command_palette",
    }

    for qml_name, bridge_key in bridge_names.items():
        bridge = all_bridges.get(bridge_key) if bridge_key else None
        if bridge_key == "eq":
            bridge = factory.get("eq")
        if bridge is not None:
            registrar.register(qml_name, bridge)
        else:
            logger.debug("QML: Skipping context property '%s' (bridge not created)", qml_name)

    # eqBridge is optional
    eq_bridge = factory.get("eq")
    if eq_bridge:
        registrar.register("eqBridge", eq_bridge)

    # Set service availability on app state bridge
    app_state = factory.get("app_state")
    if app_state:
        app_state.setServiceAvailability(
            services.player_service is not None,
            services.db is not None,
            "available" if services.player_service else "unavailable",
        )

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

    # Audit
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
    main()
