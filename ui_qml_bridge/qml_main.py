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

from ui_qml_bridge.app_bridge import AppBridge
from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.command_bus import CommandBus
from ui_qml_bridge.theme_bridge import ThemeBridge
from ui_qml_bridge.library_bridge import LibraryBridge
from ui_qml_bridge.michi_ai_bridge import MichiAIBridge
from ui_qml_bridge.cover_bridge import CoverBridge
from ui_qml_bridge.metadata_bridge import MetadataBridge
from ui_qml_bridge.mix_bridge import MixBridge
from ui_qml_bridge.playback_bridge import PlaybackBridge
from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge
from ui_qml_bridge.devices_bridge import DevicesBridge
from ui_qml_bridge.playlists_bridge import PlaylistsBridge
from ui_qml_bridge.audio_lab_bridge import AudioLabBridge
from ui_qml_bridge.settings_bridge import SettingsBridge
from ui_qml_bridge.radio_bridge import RadioBridge
from ui_qml_bridge.connections_bridge import ConnectionsBridge
from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
from ui_qml_bridge.eq_bridge import EqBridge
from ui_qml_bridge.library_doctor_bridge import LibraryDoctorBridge
from ui_qml_bridge.disc_lab_bridge import DiscLabBridge
from ui_qml_bridge.selection_context_bridge import SelectionContextBridge
from ui_qml_bridge.notification_bridge import NotificationBridge
from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge
from ui_qml_bridge.app_state_bridge import AppStateBridge
from ui_qml_bridge.diagnostics_bridge import DiagnosticsBridge
from ui_qml_bridge.command_palette_bridge import CommandPaletteBridge

logger = logging.getLogger("michi.qml")


def _get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


class QmlServiceFactory:
    """Creates and wires real backend services for QML bridges.

    Safe to call without MainWindow. Falls back to None for unavailable
    services — bridges handle None gracefully.
    """

    def __init__(self):
        self._db = None
        self._player_service = None
        self._sync_mgr = None
        self._radio_mgr = None

    def create_db(self):
        """Create LibraryDB using canonical path."""
        if self._db is not None:
            return self._db
        try:
            from library.library_db import LibraryDB
            from core.paths import database_path
            db_path = database_path()
            if db_path.exists():
                self._db = LibraryDB(str(db_path))
                logger.info("QML: LibraryDB opened at %s", db_path)
            else:
                logger.info("QML: No library DB at %s", db_path)
        except Exception as e:
            logger.debug("QML: LibraryDB init failed: %s", e)
        return self._db

    def create_player_service(self):
        """Create PlayerService with GStreamer engine."""
        if self._player_service is not None:
            return self._player_service
        try:
            from audio.player_engine import GStreamerEngine
            from audio.player_service import PlayerService
            engine = GStreamerEngine()
            self._player_service = PlayerService(engine)
            logger.info("QML: PlayerService created")
        except Exception as e:
            logger.debug("QML: PlayerService init failed: %s", e)
        return self._player_service

    def create_sync_manager(self):
        """Create SyncManager from LibraryDB."""
        if self._sync_mgr is not None:
            return self._sync_mgr
        db = self.create_db()
        if db is None:
            return None
        try:
            from sync.sync_manager import SyncManager
            self._sync_mgr = SyncManager(db)
            logger.info("QML: SyncManager created")
        except Exception as e:
            logger.debug("QML: SyncManager init failed: %s", e)
        return self._sync_mgr

    def create_radio_manager(self):
        """Create RadioManager for station management."""
        if self._radio_mgr is not None:
            return self._radio_mgr
        try:
            from streaming.radio_manager import RadioManager
            self._radio_mgr = RadioManager()
            logger.info("QML: RadioManager created")
        except Exception as e:
            logger.debug("QML: RadioManager init failed: %s", e)
        return self._radio_mgr

    def create_michi_link(self):
        """Create a lightweight MichiLink adapter (no MainWindow needed)."""
        try:
            from integrations.michi_link.services.service_manager import ServiceManager
            mgr = ServiceManager()
            return mgr
        except Exception as e:
            logger.debug("QML: MichiLink adapter init failed: %s", e)
            return None

    def create_search_engine(self):
        """Create SearchEngine from LibraryDB."""
        db = self.create_db()
        if db is None:
            return None
        try:
            from library.search_engine import SearchEngine
            return SearchEngine(db)
        except Exception as e:
            logger.debug("QML: SearchEngine init failed: %s", e)
            return None


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setApplicationVersion(_get_app_version())

    engine = QQmlApplicationEngine()

    # Initialize services
    factory = QmlServiceFactory()
    db = factory.create_db()
    player_service = factory.create_player_service()
    sync_mgr = factory.create_sync_manager()
    radio_mgr = factory.create_radio_manager()
    michi_link = factory.create_michi_link()
    search_engine = factory.create_search_engine()

    # Get db_conn for bridges that expect a raw connection
    db_conn = db.conn if db is not None and hasattr(db, 'conn') else None

    # Create bridges with real services
    app_bridge = AppBridge()
    nav_bridge = NavigationBridge()
    cmd_bus = CommandBus()
    theme_bridge = ThemeBridge()
    library_bridge = LibraryBridge(
        db=db,
        search_engine=search_engine,
        playback_ctrl=player_service,
    )
    michi_ai_bridge = MichiAIBridge()
    metadata_bridge = MetadataBridge()
    mix_bridge = MixBridge(db=db)
    nowplaying_bridge = NowPlayingBridge(player_service=player_service)
    playback_bridge = PlaybackBridge(
        player_service=player_service,
        nowplaying_bridge=nowplaying_bridge,
    )
    selection_context_bridge = SelectionContextBridge()
    devices_bridge = DevicesBridge(sync_manager=sync_mgr)
    playlists_bridge = PlaylistsBridge(db=db, selection_context=selection_context_bridge)
    audio_lab_bridge = AudioLabBridge(db_conn=db_conn)
    settings_bridge = SettingsBridge()
    radio_bridge = RadioBridge(radio_manager=radio_mgr, player_service=player_service)
    connections_bridge = ConnectionsBridge(michi_link_ctrl=michi_link)
    eq_bridge = EqBridge(player_service=player_service) if player_service else None
    smart_tagging_bridge = SmartTaggingBridge()
    library_doctor_bridge = LibraryDoctorBridge(db=db)
    disc_lab_bridge = DiscLabBridge()
    notification_bridge = NotificationBridge()
    route_registry_bridge = RouteRegistryBridge()
    app_state_bridge = AppStateBridge()
    diagnostics_bridge = DiagnosticsBridge()
    command_palette_bridge = CommandPaletteBridge(navigation_bridge=nav_bridge)
    try:
        from ui.audio_lab.services.smart_tagging_service import SmartTaggingService
        smart_tagging_bridge.set_service(SmartTaggingService())
    except Exception:
        pass

    # Register context properties
    engine.rootContext().setContextProperty("appBridge", app_bridge)
    engine.rootContext().setContextProperty("navigationBridge", nav_bridge)
    engine.rootContext().setContextProperty("commandBus", cmd_bus)
    engine.rootContext().setContextProperty("themeBridge", theme_bridge)
    engine.rootContext().setContextProperty("libraryBridge", library_bridge)
    engine.rootContext().setContextProperty("michiAiBridge", michi_ai_bridge)
    engine.rootContext().setContextProperty("metadataBridge", metadata_bridge)
    engine.rootContext().setContextProperty("mixBridge", mix_bridge)
    engine.rootContext().setContextProperty("playbackBridge", playback_bridge)
    engine.rootContext().setContextProperty("nowplayingBridge", nowplaying_bridge)
    engine.rootContext().setContextProperty("devicesBridge", devices_bridge)
    engine.rootContext().setContextProperty("playlistsBridge", playlists_bridge)
    engine.rootContext().setContextProperty("audioLabBridge", audio_lab_bridge)
    engine.rootContext().setContextProperty("settingsBridge", settings_bridge)
    engine.rootContext().setContextProperty("radioBridge", radio_bridge)
    engine.rootContext().setContextProperty("connectionsBridge", connections_bridge)
    engine.rootContext().setContextProperty("smartTaggingBridge", smart_tagging_bridge)
    engine.rootContext().setContextProperty("libraryDoctorBridge", library_doctor_bridge)
    engine.rootContext().setContextProperty("discLabBridge", disc_lab_bridge)
    engine.rootContext().setContextProperty("selectionContextBridge", selection_context_bridge)
    engine.rootContext().setContextProperty("notificationBridge", notification_bridge)
    engine.rootContext().setContextProperty("routeRegistryBridge", route_registry_bridge)
    engine.rootContext().setContextProperty("appStateBridge", app_state_bridge)
    engine.rootContext().setContextProperty("diagnosticsBridge", diagnostics_bridge)
    engine.rootContext().setContextProperty("commandPaletteBridge", command_palette_bridge)
    if eq_bridge:
        engine.rootContext().setContextProperty("eqBridge", eq_bridge)

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

    print(f"[QML] Michi Music Player {_get_app_version()} — experimental QML UI")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
