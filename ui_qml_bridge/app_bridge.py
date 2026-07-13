"""AppBridge — real application state and lifecycle."""
from __future__ import annotations

import os
import sys
from importlib.metadata import version, PackageNotFoundError

from PySide6.QtCore import QObject, Signal, Property, Slot


def get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


class AppBridge(QObject):
    statusChanged = Signal(str)

    PHASE_INITIALIZING = "initializing"
    PHASE_LOADING_SERVICES = "loading_services"
    PHASE_LOADING_QML = "loading_qml"
    PHASE_READY = "ready"
    PHASE_SHUTTING_DOWN = "shutting_down"
    PHASE_FAILED = "failed"

    def __init__(self, worker_manager=None, query_executor=None,
                 player_service=None, queue_bridge=None,
                 sync_manager=None, home_audio_controller=None,
                 radio_manager=None, discovery=None, db=None, parent=None):
        super().__init__(parent)
        self._app_name = "Michi Music Player"
        self._version = get_app_version()
        self._experimental_qml = True
        self._safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        self._ready = False
        self._shutting_down = False
        self._restart_required = False
        self._wm = worker_manager
        self._qe = query_executor
        self._player_service = player_service
        self._queue_bridge = queue_bridge
        self._sync_manager = sync_manager
        self._home_audio = home_audio_controller
        self._radio_manager = radio_manager
        self._discovery = discovery
        self._db = db
        self._ui_mode = "qml"
        self._phase = self.PHASE_INITIALIZING
        self._accepting_new = True

    @Property(str, constant=True)
    def appName(self):
        return self._app_name

    @Property(str, constant=True)
    def version(self):
        return self._version

    @Property(bool, constant=True)
    def experimentalQml(self):
        return self._experimental_qml

    @Property(bool, notify=statusChanged)
    def safeMode(self):
        return self._safe_mode

    @Property(bool, notify=statusChanged)
    def ready(self):
        return self._ready

    @Property(bool, notify=statusChanged)
    def shuttingDown(self):
        return self._shutting_down

    @Property(bool, notify=statusChanged)
    def restartRequired(self):
        return self._restart_required

    @Property(str, constant=True)
    def uiMode(self):
        return self._ui_mode

    @Property(str, notify=statusChanged)
    def phase(self):
        return self._phase

    @Property(str, constant=True)
    def dataPath(self):
        try:
            from core.paths import data_dir
            return str(data_dir())
        except Exception:
            return ""

    @Property(str, constant=True)
    def cachePath(self):
        try:
            from core.paths import cache_dir
            return str(cache_dir())
        except Exception:
            return ""

    @Property(str, constant=True)
    def configPath(self):
        try:
            from core.paths import config_dir
            return str(config_dir())
        except Exception:
            return ""

    @Property(str, constant=True)
    def logPath(self):
        try:
            from core.paths import log_dir
            return str(log_dir())
        except Exception:
            return ""

    @Slot()
    def setReady(self):
        self._ready = True
        self._phase = self.PHASE_READY
        self.statusChanged.emit("ready")

    def setPhase(self, phase: str):
        self._phase = phase
        self.statusChanged.emit(phase)

    @Slot(result=dict)
    def requestRestart(self):
        self._restart_required = True
        self.statusChanged.emit("restart_required")
        return {"ok": True, "restart_required": True}

    @Slot(result=dict)
    def copyVersionInfo(self):
        lines = [
            f"App: {self._app_name}",
            f"Version: {self._version}",
            f"Python: {sys.version}",
            f"Safe mode: {self._safe_mode}",
            f"UI mode: {self._ui_mode}",
            f"Data: {self.dataPath}",
            f"Cache: {self.cachePath}",
            f"Config: {self.configPath}",
            f"Logs: {self.logPath}",
        ]
        return {"ok": True, "text": "\n".join(lines)}

    @Slot()
    def quit(self):
        self._shutting_down = True
        self._phase = self.PHASE_SHUTTING_DOWN
        self._accepting_new = False
        self.statusChanged.emit("shutting_down")

        import contextlib

        # b. Cancel QueryExecutor
        with contextlib.suppress(Exception):
            if self._qe and hasattr(self._qe, 'shutdown'):
                self._qe.shutdown(2000)

        # c. Cancel WorkerManager
        with contextlib.suppress(Exception):
            if self._wm and hasattr(self._wm, 'cancel_all'):
                self._wm.cancel_all()
            if self._wm and hasattr(self._wm, 'shutdown'):
                self._wm.shutdown(3000)

        # d. Stop SyncManager
        with contextlib.suppress(Exception):
            if self._sync_manager and hasattr(self._sync_manager, 'stop'):
                self._sync_manager.stop()

        # e. Stop discovery
        with contextlib.suppress(Exception):
            if self._discovery and hasattr(self._discovery, 'stop'):
                self._discovery.stop()

        # f. Stop Home Audio polling
        with contextlib.suppress(Exception):
            if self._home_audio:
                if hasattr(self._home_audio, 'stop'):
                    self._home_audio.stop()
                elif hasattr(self._home_audio, 'shutdown'):
                    self._home_audio.shutdown()

        # g. Stop radio
        with contextlib.suppress(Exception):
            if self._radio_manager:
                if hasattr(self._radio_manager, 'stop'):
                    self._radio_manager.stop()
                elif hasattr(self._radio_manager, 'shutdown'):
                    self._radio_manager.shutdown()

        # h. Stop audio
        with contextlib.suppress(Exception):
            if self._player_service and hasattr(self._player_service, 'stop'):
                self._player_service.stop()

        # i. Persist queue and session
        with contextlib.suppress(Exception):
            if self._queue_bridge:
                self._queue_bridge.saveState()

        # j. Close DB
        with contextlib.suppress(Exception):
            if self._db and hasattr(self._db, 'close'):
                self._db.close()

        # k. Quit Qt
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.quit()

    @Slot()
    def cancelAllTasks(self):
        if self._wm and hasattr(self._wm, 'cancel_all'):
            self._wm.cancel_all()

    def notifyRestartRequired(self):
        self._restart_required = True
        self.statusChanged.emit("restart_required")

    def getWorkerManager(self):
        return self._wm

    def getQueryExecutor(self):
        return self._qe

    @Slot(result=dict)
    def appScore(self) -> dict:
        score = 0
        if self._wm:
            score += 25
        if self._qe:
            score += 20
        if self._ready:
            score += 15
        if not self._safe_mode and self._ready:
            score += 15
        if self._wm and hasattr(self._wm, 'cancel_all'):
            score += 15
        if self._wm and hasattr(self._wm, 'shutdown'):
            score += 10
        return {
            "score": min(100, score),
            "has_worker_manager": self._wm is not None,
            "has_query_executor": self._qe is not None,
            "ready": self._ready,
            "safe_mode": self._safe_mode,
            "shutting_down": self._shutting_down,
            "restart_required": self._restart_required,
        }
