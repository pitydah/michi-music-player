"""Composition root — wires dependencies, owns lifecycle. No business logic."""

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QTimer, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from michi.application.coordinator import PlaybackCoordinator
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner
from michi.infrastructure.qt_backend import QtMultimediaBackend
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.queue_bridge import QueueBridge


def _data_dir() -> Path:
    base = QStandardPaths.writableLocation(QStandardPaths.AppLocalDataLocation)
    path = Path(base)
    path.mkdir(parents=True, exist_ok=True)
    return path


class ApplicationContainer:
    """Creates and owns all long-lived components. Explicit wiring only."""

    def __init__(self) -> None:
        self._app: QGuiApplication | None = None
        self._engine: QQmlApplicationEngine | None = None
        self._backend: QtMultimediaBackend | None = None
        self._settings_repo: SQLiteSettingsRepository | None = None
        self._scanner: FilesystemLibraryScanner | None = None
        self._playback_service: PlaybackService | None = None
        self._queue_service: QueueService | None = None
        self._coordinator: PlaybackCoordinator | None = None
        self._playback_bridge: PlaybackBridge | None = None
        self._queue_bridge: QueueBridge | None = None
        self._library_bridge: LibraryBridge | None = None
        self._position_timer: QTimer | None = None

    def initialize(self) -> None:
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self._app = QGuiApplication(sys.argv)
        self._app.setApplicationName("Michi Music Player")
        self._app.setApplicationVersion("0.1.0")
        self._app.setOrganizationName("Michi")

        # ── Infrastructure ──────────────────────────────────────────
        self._backend = QtMultimediaBackend()
        self._settings_repo = SQLiteSettingsRepository(_data_dir() / "michi.db")
        self._scanner = FilesystemLibraryScanner()

        # ── Application ─────────────────────────────────────────────
        self._playback_service = PlaybackService(self._backend)
        self._queue_service = QueueService(self._playback_service)

        # Restore persisted settings via public API
        settings = self._settings_repo.load()
        self._playback_service.restore_volume(settings.volume, settings.muted)

        # Coordinator: track end → queue advance
        self._coordinator = PlaybackCoordinator(self._backend, self._queue_service)

        # ── Presentation bridges ────────────────────────────────────
        self._playback_bridge = PlaybackBridge(self._playback_service)
        self._queue_bridge = QueueBridge(self._queue_service)
        self._library_bridge = LibraryBridge(self._scanner, self._queue_service)

        # Wire bridge notifications through the coordinator callback
        def _notify_bridges() -> None:
            if self._queue_bridge:
                self._queue_bridge.notify()
            if self._playback_bridge:
                self._playback_bridge.notify_state()

        self._coordinator.on_state_change(_notify_bridges)
        self._coordinator.start()

        # Position sync — infrastructure concern, lives in bootstrap
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._sync_position)
        self._position_timer.start(250)

        # ── QML engine ─────────────────────────────────────────────
        self._engine = QQmlApplicationEngine()
        self._engine.quit.connect(self._app.quit)
        root_context = self._engine.rootContext()
        root_context.setContextProperty("playback", self._playback_bridge)
        root_context.setContextProperty("queue", self._queue_bridge)
        root_context.setContextProperty("library", self._library_bridge)

    def run(self) -> int:
        qml_dir = Path(__file__).parent.parent / "presentation"
        main_qml = qml_dir / "main.qml"
        if not main_qml.exists():
            print(f"FATAL: QML entry not found at {main_qml}", file=sys.stderr)
            return 1
        self._engine.load(QUrl.fromLocalFile(str(main_qml)))
        if not self._engine.rootObjects():
            print("FATAL: QML engine failed to load any root object", file=sys.stderr)
            return 1
        return self._app.exec()

    def shutdown(self) -> None:
        if self._coordinator:
            self._coordinator.stop()

        if self._position_timer is not None:
            self._position_timer.stop()

        # Persist settings via public API
        if self._playback_service is not None and self._settings_repo is not None:
            from michi.domain.settings import SettingsState
            s = self._playback_service.state
            self._settings_repo.save(SettingsState(volume=s.volume, muted=s.muted))

        if self._backend is not None:
            self._backend.stop()

        if self._engine is not None:
            self._engine.deleteLater()

        self._engine = None
        self._position_timer = None
        self._library_bridge = None
        self._queue_bridge = None
        self._playback_bridge = None
        self._coordinator = None
        self._queue_service = None
        self._playback_service = None
        self._settings_repo = None
        self._backend = None
        self._app = None

    def _sync_position(self) -> None:
        if self._backend is None or self._playback_service is None or self._playback_bridge is None:
            return
        self._playback_service.update_position(
            position_ms=self._backend.position(),
            duration_ms=self._backend.duration(),
        )
        self._playback_bridge.notify_state()
