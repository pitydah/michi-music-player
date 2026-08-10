"""Composition root — wires dependencies, owns lifecycle. No business logic."""

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_service import LibraryService
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
        self._coordinator: PlaybackCoordinator | None = None

    def initialize(self) -> None:
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self._app = QGuiApplication(sys.argv)
        self._app.setApplicationName("Michi Music Player")
        self._app.setApplicationVersion("0.1.0")
        self._app.setOrganizationName("Michi")

        # Infrastructure
        backend = QtMultimediaBackend()
        settings_repo = SQLiteSettingsRepository(_data_dir() / "michi.db")
        scanner = FilesystemLibraryScanner()

        # Application
        playback = PlaybackService(backend)
        queue = QueueService(playback)
        library = LibraryService(scanner, queue)

        # Restore settings
        settings = settings_repo.load()
        playback.restore_volume(settings.volume, settings.muted)

        # Coordinator: audio events → application logic
        coordinator = PlaybackCoordinator(backend, queue, playback)

        # Presentation bridges
        pb = PlaybackBridge(playback)
        qb = QueueBridge(queue)
        lb = LibraryBridge(library)

        # Wire bridge notifications through coordinator
        def _notify() -> None:
            qb.notify()
            pb.notify_state()
            lb.notify()

        coordinator.on_state_change(_notify)
        coordinator.start()

        # QML engine
        engine = QQmlApplicationEngine()
        engine.quit.connect(self._app.quit)
        ctx = engine.rootContext()
        ctx.setContextProperty("playback", pb)
        ctx.setContextProperty("queue", qb)
        ctx.setContextProperty("library", lb)

        # Keep references for shutdown
        self._backend = backend
        self._coordinator = coordinator
        self._engine = engine

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
        if self._backend:
            self._backend.stop()
        if self._engine:
            self._engine.deleteLater()
        self._engine = None
        self._coordinator = None
        self._backend = None
        self._app = None
