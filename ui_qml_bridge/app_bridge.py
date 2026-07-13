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

    def __init__(self, worker_manager=None, query_executor=None, parent=None):
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
        self._ui_mode = "qml"

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
        self.statusChanged.emit("shutting_down")
        if self._qe and hasattr(self._qe, 'shutdown'):
            self._qe.shutdown(1000)
        if self._wm and hasattr(self._wm, 'shutdown'):
            self._wm.shutdown(2000)
        from PySide6.QtCore import QCoreApplication
        QCoreApplication.quit()
