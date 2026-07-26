from __future__ import annotations

import logging
import os
import sys
from dataclasses import dataclass, field
from importlib.metadata import version, PackageNotFoundError
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.app_bridge")


@dataclass
class ShutdownResult:
    steps: list[dict[str, Any]] = field(default_factory=list)
    success: bool = True

    def record(self, step: str, ok: bool, detail: str = ""):
        self.steps.append({"step": step, "ok": ok, "detail": detail})
        if not ok:
            self.success = False

    def to_dict(self) -> dict:
        return {"success": self.success, "steps": list(self.steps)}


def get_app_version() -> str:
    try:
        return version("michi-music-player")
    except PackageNotFoundError:
        return "0.2.0-alpha.1"


def _try_shutdown(svc):
    if hasattr(svc, 'shutdown') and callable(svc.shutdown):
        svc.shutdown()
    elif hasattr(svc, 'stop') and callable(svc.stop):
        svc.stop()


def _try_cancel(svc):
    if hasattr(svc, 'cancel_all') and callable(svc.cancel_all):
        svc.cancel_all()


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
                 player_service=None, queue_service=None,
                 device_sync_service=None, connection_service=None,
                 home_audio_service=None, radio_service=None,
                 database=None, navigation_bridge=None,
                 queue_bridge=None, sync_manager=None,
                 home_audio_controller=None, radio_manager=None,
                 discovery=None, db=None, parent=None):
        super().__init__(parent)
        self._app_name = "Michi Music Player"
        self._version = get_app_version()
        self._experimental_qml = True
        self._safe_mode = os.environ.get("MICHI_SAFE_MODE") == "1"
        self._ready = False
        self._shutting_down = False
        self._restart_required = False
        self._phase = self.BOOTSTRAP
        self._accepting_new = True
        self._shutdown_executed = False
        self._external_processes: list = []
        self._navigation_bridge = navigation_bridge

        self._wm = worker_manager
        self._qe = query_executor
        self._player_service = player_service
        self._queue_service = queue_service or queue_bridge
        self._device_sync_service = device_sync_service or sync_manager
        self._connection_service = connection_service
        self._home_audio_service = home_audio_service or home_audio_controller
        self._radio_service = radio_service or radio_manager
        self._discovery = discovery
        self._database = database or db

        self._services: list = [s for s in [
            self._wm, self._qe, self._player_service,
            self._queue_service, self._device_sync_service,
            self._connection_service, self._home_audio_service,
            self._radio_service, self._navigation_bridge, self._database,
        ] if s is not None]

        self._ui_mode = "qml"

    @property
    def _accepting(self):
        return self._accepting_new

    @_accepting.setter
    def _accepting(self, value):
        self._accepting_new = value

    def receive_services(self, *services):
        self._services = list(services)

    def set_navigation_bridge(self, nav):
        self._navigation_bridge = nav
        if nav and nav not in self._services:
            self._services.append(nav)

    def track_external_process(self, proc):
        self._external_processes.append(proc)

    def _persist_page_state(self):
        pass

    def _close_repositories(self):
        pass

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

    @Slot(result=dict)
    def quit(self):
        self._shutting_down = True
        self._phase = self.SHUTTING_DOWN
        self._accepting_new = False
        self.statusChanged.emit("shutting_down")
        result = self._ordered_shutdown()
        return result.to_dict() if isinstance(result, ShutdownResult) else result

    SHUTDOWN_TIMEOUT_S = 5.0

    def _ordered_shutdown(self):
        if self._shutdown_executed:
            return {"success": True, "steps": []}
        self._shutdown_executed = True
        sr = ShutdownResult()

        steps = [
            ("block_actions", self._step_block_actions),
            ("cancel_navigation", self._step_cancel_navigation),
            ("cancel_queries", self._step_cancel_queries),
            ("cancel_jobs", self._step_cancel_jobs),
            ("terminate_subprocesses", self._step_terminate_subprocesses),
            ("persist_queue", self._step_persist_queue),
            ("persist_page_state", self._step_persist_page_state),
            ("stop_device_sync", self._step_stop_device_sync),
            ("stop_connections", self._step_stop_connections),
            ("stop_home_audio", self._step_stop_home_audio),
            ("stop_radio", self._step_stop_radio),
            ("stop_playback", self._step_stop_playback),
            ("close_repositories", self._step_close_repositories),
            ("close_db", self._step_close_db),
        ]
        for step_name, step_fn in steps:
            try:
                step_fn()
                sr.record(step_name, True)
            except Exception as e:
                logger.error("Shutdown step '%s' failed: %s", step_name, e)
                sr.record(step_name, False, str(e))

        if not sr.success:
            logger.warning("Shutdown completed with %d failed steps",
                          sum(1 for s in sr.steps if not s["ok"]))
        return sr

    def _step_block_actions(self):
        self._accepting_new = False

    def _step_cancel_navigation(self):
        if self._navigation_bridge and hasattr(self._navigation_bridge, 'clearHistory'):
            self._navigation_bridge.clearHistory()

    def _step_cancel_queries(self):
        if self._qe and hasattr(self._qe, 'shutdown'):
            self._qe.shutdown(2000)

    def _step_cancel_jobs(self):
        _try_cancel(self._wm)
        if self._wm and hasattr(self._wm, 'shutdown'):
            self._wm.shutdown(3000)

    def _step_terminate_subprocesses(self):
        for proc in self._external_processes:
            if hasattr(proc, 'terminate'):
                proc.terminate()
            if hasattr(proc, 'wait'):
                proc.wait(timeout=2)
        self._external_processes.clear()

    def _step_persist_queue(self):
        _try_shutdown(self._queue_service)

    def _step_persist_page_state(self):
        self._persist_page_state()

    def _step_stop_device_sync(self):
        _try_shutdown(self._device_sync_service)

    def _step_stop_connections(self):
        _try_shutdown(self._connection_service)

    def _step_stop_home_audio(self):
        _try_shutdown(self._home_audio_service)

    def _step_stop_radio(self):
        _try_shutdown(self._radio_service)

    def _step_stop_playback(self):
        if self._player_service and hasattr(self._player_service, 'stop'):
            self._player_service.stop()

    def _step_close_repositories(self):
        self._close_repositories()

    def _step_close_db(self):
        if self._database and hasattr(self._database, 'close'):
            self._database.close()

    def notifyRestartRequired(self):
        self._restart_required = True
        self.statusChanged.emit("restart_required")

    @Slot()
    def cancelAllTasks(self):
        _try_cancel(self._wm)

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
            "has_worker_manager": self._wm is not None,
        }
