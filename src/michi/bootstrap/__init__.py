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
        self._settings_repo: SQLiteSettingsRepository | None = None
        self._playback: PlaybackService | None = None
        self._queue: QueueService | None = None
        self._library: LibraryService | None = None
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

        # Application
        playback = PlaybackService(backend)
        queue = QueueService(playback)
        scanner = FilesystemLibraryScanner()
        library = LibraryService(scanner, queue)

        # Restore persisted settings
        s = settings_repo.load()
        playback.restore_volume(s.volume, s.muted)

        # Coordinator: audio events → application logic
        coordinator = PlaybackCoordinator(backend, queue, playback)
        coordinator.start()

        # Presentation bridges — subscribe to services automatically
        pb = PlaybackBridge(playback)
        qb = QueueBridge(queue)
        lb = LibraryBridge(library)

        # QML engine
        engine = QQmlApplicationEngine()
        engine.quit.connect(self._app.quit)
        ctx = engine.rootContext()
        ctx.setContextProperty("playback", pb)
        ctx.setContextProperty("queue", qb)
        ctx.setContextProperty("library", lb)

        # Explicit ownership for shutdown
        self._backend = backend
        self._settings_repo = settings_repo
        self._playback = playback
        self._queue = queue
        self._library = library
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

        # Persist settings before destroying services
        if self._playback and self._settings_repo:
            from michi.domain.settings import SettingsState

            vol, muted = self._playback.snapshot_volume()
            self._settings_repo.save(SettingsState(volume=vol, muted=muted))

        if self._backend:
            self._backend.stop()
        if self._engine:
            self._engine.deleteLater()

        self._engine = None
        self._coordinator = None
        self._library = None
        self._queue = None
        self._playback = None
        self._settings_repo = None
        self._backend = None
        self._app = None
