"""Composition root — wires dependencies, owns lifecycle. No business logic."""

import sys
from pathlib import Path

from PySide6.QtCore import Qt, QUrl, QTimer
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtMultimedia import QMediaPlayer

from michi.infrastructure.qt_backend import QtMultimediaBackend
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.queue_bridge import QueueBridge


class ApplicationContainer:
    """Creates and owns all long-lived components. Explicit wiring only."""

    def __init__(self) -> None:
        self._app: QGuiApplication | None = None
        self._engine: QQmlApplicationEngine | None = None
        self._backend: QtMultimediaBackend | None = None
        self._playback_service: PlaybackService | None = None
        self._queue_service: QueueService | None = None
        self._playback_bridge: PlaybackBridge | None = None
        self._queue_bridge: QueueBridge | None = None
        self._position_timer: QTimer | None = None

    def initialize(self) -> None:
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self._app = QGuiApplication(sys.argv)
        self._app.setApplicationName("Michi Music Player")
        self._app.setApplicationVersion("0.1.0")
        self._app.setOrganizationName("Michi")

        # Infrastructure
        self._backend = QtMultimediaBackend()

        # Application — explicit injection
        self._playback_service = PlaybackService(self._backend)
        self._queue_service = QueueService(self._playback_service)

        # Auto-advance: when track ends, play next in queue
        self._backend.player.mediaStatusChanged.connect(self._on_media_status)

        # Presentation bridges
        self._playback_bridge = PlaybackBridge(self._playback_service)
        self._queue_bridge = QueueBridge(self._queue_service)

        # Position sync timer
        self._position_timer = QTimer()
        self._position_timer.timeout.connect(self._sync_position)
        self._position_timer.start(250)

        # QML engine
        self._engine = QQmlApplicationEngine()
        self._engine.quit.connect(self._app.quit)
        root_context = self._engine.rootContext()
        root_context.setContextProperty("playback", self._playback_bridge)
        root_context.setContextProperty("queue", self._queue_bridge)

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
        if self._position_timer is not None:
            self._position_timer.stop()
        if self._backend is not None:
            self._backend.player.stop()
        if self._engine is not None:
            self._engine.deleteLater()
        self._engine = None
        self._position_timer = None
        self._queue_bridge = None
        self._playback_bridge = None
        self._queue_service = None
        self._playback_service = None
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

    def _on_media_status(self, status: QMediaPlayer.MediaStatus) -> None:
        if status == QMediaPlayer.EndOfMedia:
            if self._queue_service is not None and self._queue_service.state.has_next:
                self._queue_service.next()
                self._queue_bridge.notify()
                self._playback_bridge.notify_state()
