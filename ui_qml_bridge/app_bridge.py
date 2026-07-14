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

    BOOTSTRAP = "bootstrap"
    DATABASE_READY = "database_ready"
    SERVICES_READY = "services_ready"
    BRIDGES_READY = "bridges_ready"
    QML_LOADING = "qml_loading"
    READY = "ready"
    DEGRADED = "degraded"
    FAILED = "failed"
    SHUTTING_DOWN = "shutting_down"
    STOPPED = "stopped"
    PHASE_LOADING_SERVICES = "services_ready"
    PHASE_INITIALIZING = "bootstrap"
    PHASE_LOADING_QML = "qml_loading"
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
        self._services: list = [s for s in [worker_manager, query_executor,
                               player_service, queue_bridge, sync_manager,
                               home_audio_controller, radio_manager, discovery, db]
                               if s is not None]
        self._ui_mode = "qml"
        self._phase = self.BOOTSTRAP
        self._accepting_new = True

    def receive_services(self, *services):
        self._services = list(services)

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

    def setPhase(self, phase: str):
        self._phase = phase
        self.statusChanged.emit(phase)

    @Slot()
    def setReady(self):
        self._ready = True
        self._phase = self.READY
        self.statusChanged.emit("ready")

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
        self._phase = self.SHUTTING_DOWN
        self._accepting_new = False
        self.statusChanged.emit("shutting_down")
        self._ordered_shutdown()

    def _ordered_shutdown(self):
        steps = []
        for svc in self._services:
            steps.append(svc)

        import contextlib
        for step in steps:
            if hasattr(step, 'shutdown'):
                with contextlib.suppress(Exception):
                    step.shutdown()

        self._phase = self.STOPPED
        self.statusChanged.emit("stopped")

        from PySide6.QtCore import QCoreApplication
        QCoreApplication.quit()

    @Slot()
    def cancelAllTasks(self):
        import contextlib
        for svc in self._services:
            if hasattr(svc, 'cancel_all'):
                with contextlib.suppress(Exception):
                    svc.cancel_all()

    def notifyRestartRequired(self):
        self._restart_required = True
        self.statusChanged.emit("restart_required")

    @Slot(result=dict)
    def appScore(self) -> dict:
        score = 0
        if self._services:
            score += 25
        if self._ready:
            score += 15
        if not self._safe_mode and self._ready:
            score += 15
        if len(self._services) > 2:
            score += 15
        if self._phase in (self.READY, self.DEGRADED):
            score += 15
        return {
            "score": min(100, score),
            "service_count": len(self._services),
            "ready": self._ready,
            "safe_mode": self._safe_mode,
            "shutting_down": self._shutting_down,
            "restart_required": self._restart_required,
            "phase": self._phase,
        }
