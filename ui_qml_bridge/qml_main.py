import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

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


def _try_get_db():
    """Try to open library DB for bridges that need it."""
    db_path = Path.home() / ".local" / "share" / "michi-music-player" / "library.db"
    if db_path.exists():
        try:
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            conn.row_factory = sqlite3.Row
            return conn
        except Exception:
            pass
    return None


def _try_get_sync_manager():
    """Try to get SyncManager instance if available."""
    try:
        from library.library_db import LibraryDB
        from sync.sync_manager import SyncManager
        db_path = Path.home() / ".local" / "share" / "michi-music-player" / "library.db"
        if db_path.exists():
            ldb = LibraryDB(str(db_path))
            mgr = SyncManager(ldb)
            return mgr
    except Exception:
        pass
    return None


def main():
    app = QGuiApplication(sys.argv)
    app.setApplicationName("Michi Music Player")
    app.setApplicationVersion("0.1.0-qml")

    engine = QQmlApplicationEngine()

    db_conn = _try_get_db()
    sync_mgr = _try_get_sync_manager()

    app_bridge = AppBridge()
    nav_bridge = NavigationBridge()
    cmd_bus = CommandBus()
    theme_bridge = ThemeBridge()
    library_bridge = LibraryBridge()
    michi_ai_bridge = MichiAIBridge()
    metadata_bridge = MetadataBridge()
    mix_bridge = MixBridge()
    playback_bridge = PlaybackBridge()
    nowplaying_bridge = NowPlayingBridge()
    devices_bridge = DevicesBridge(sync_manager=sync_mgr)
    playlists_bridge = PlaylistsBridge(db_conn=db_conn)
    audio_lab_bridge = AudioLabBridge(db_conn=db_conn)
    settings_bridge = SettingsBridge()
    radio_bridge = RadioBridge()

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

    print("[QML] Michi Music Player QML experimental running")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
