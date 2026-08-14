"""Composition root — wires dependencies, owns lifecycle. No business logic."""

import sys
from pathlib import Path

from PySide6.QtCore import QStandardPaths, Qt, QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine

from michi.application.coordinator import PlaybackCoordinator
from michi.application.library_preferences_coordinator import (
    LibraryPreferencesCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.navigation_service import NavigationService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner
from michi.infrastructure.qt_backend import QtMultimediaBackend
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.playback_bridge import PlaybackBridge
from michi.presentation.queue_bridge import QueueBridge
from michi.presentation.settings_bridge import SettingsBridge


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
        self._settings: SettingsService | None = None
        self._playback: PlaybackService | None = None
        self._queue: QueueService | None = None
        self._library: LibraryService | None = None
        self._library_prefs: LibraryPreferencesCoordinator | None = None
        self._navigation: NavigationService | None = None
        self._coordinator: PlaybackCoordinator | None = None
        self._pb: PlaybackBridge | None = None
        self._qb: QueueBridge | None = None
        self._lb: LibraryBridge | None = None
        self._nb: NavigationBridge | None = None
        self._sb: SettingsBridge | None = None

    def initialize(self) -> None:
        QGuiApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QGuiApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

        self._app = QGuiApplication(sys.argv)
        self._app.setApplicationName("Michi Music Player")
        self._app.setApplicationVersion("0.1.0")
        self._app.setOrganizationName("Michi")

        db_path = _data_dir() / "michi.db"
        repo = SQLiteSettingsRepository.open_for_startup(db_path)
        backend = QtMultimediaBackend()
        settings = SettingsService(repo)

        playback = PlaybackService(backend)
        queue = QueueService(playback)
        scanner = FilesystemLibraryScanner()
        library = LibraryService(scanner, queue)
        navigation = NavigationService()

        # Load persisted preferences once
        s = settings.load()
        playback.restore_volume(s.volume, s.muted)

        # Library/settings coordination: restore last_directory, sync on scan
        lib_prefs = LibraryPreferencesCoordinator(library, settings)
        lib_prefs.start()

        coordinator = PlaybackCoordinator(backend, queue, playback)
        coordinator.start()

        pb = PlaybackBridge(playback)
        qb = QueueBridge(queue)
        lb = LibraryBridge(library)
        nb = NavigationBridge(navigation)
        sb = SettingsBridge(settings)

        engine = QQmlApplicationEngine()
        engine.quit.connect(self._app.quit)
        ctx = engine.rootContext()
        ctx.setContextProperty("playback", pb)
        ctx.setContextProperty("queue", qb)
        ctx.setContextProperty("library", lb)
        ctx.setContextProperty("navigation", nb)
        ctx.setContextProperty("settingsBridge", sb)

        self._backend = backend
        self._settings = settings
        self._playback = playback
        self._queue = queue
        self._library = library
        self._library_prefs = lib_prefs
        self._navigation = navigation
        self._coordinator = coordinator
        self._pb = pb
        self._qb = qb
        self._lb = lb
        self._nb = nb
        self._sb = sb
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
        error: Exception | None = None

        try:
            if self._coordinator:
                self._coordinator.stop()
        except Exception as exc:
            error = error or exc

        try:
            if self._library_prefs:
                self._library_prefs.stop()
        except Exception as exc:
            error = error or exc

        try:
            if self._playback and self._settings:
                vol, muted = self._playback.snapshot_volume()
                self._settings.set_playback_preferences(vol, muted)
                self._settings.save()
        except Exception as exc:
            error = error or exc

        for bridge in (self._pb, self._qb, self._lb, self._nb):
            try:
                if bridge:
                    bridge.dispose()
            except Exception as exc:
                error = error or exc

        try:
            if self._backend:
                self._backend.stop()
        except Exception as exc:
            error = error or exc

        try:
            if self._engine:
                self._engine.deleteLater()
        except Exception as exc:
            error = error or exc

        self._engine = None
        self._lb = None
        self._qb = None
        self._pb = None
        self._nb = None
        self._sb = None
        self._coordinator = None
        self._library_prefs = None
        self._navigation = None
        self._library = None
        self._queue = None
        self._playback = None
        self._settings = None
        self._backend = None
        self._app = None

        if error is not None:
            raise error
