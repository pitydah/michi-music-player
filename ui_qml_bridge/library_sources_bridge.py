from __future__ import annotations

import logging
from pathlib import Path

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.library_sources_service import LibrarySourcesService

logger = logging.getLogger("michi.library_sources_bridge")


class LibrarySourcesBridge(QObject):
    dataChanged = Signal()

    def __init__(self, service: LibrarySourcesService,
                 job_bridge=None, folder_service=None, parent=None):
        super().__init__(parent)
        self._svc = service
        self._jb = job_bridge
        self._folder_svc = folder_service
        self._status = "ready"
        self._exclusions: list[str] = []

    @Property("QVariantList", notify=dataChanged)
    def sources(self):
        return self._svc.list()

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}

    @Slot(str, result=dict)
    def addSource(self, path: str):
        result = self._svc.add(path)
        self.dataChanged.emit()
        return result

    @Slot(str, str, result=dict)
    def editSource(self, path: str, new_path: str):
        return self.relinkSource(path, new_path)

    @Slot(str, result=dict)
    def removeSource(self, path: str):
        result = self._svc.remove(path)
        self.dataChanged.emit()
        return result

    @Slot(str, bool, result=dict)
    def setSourceEnabled(self, path: str, enabled: bool):
        result = self._svc.enable(path, enabled)
        self.dataChanged.emit()
        return result

    @Slot(str, result=dict)
    def scanSource(self, path: str):
        if not self._jb:
            return {"ok": False, "error": "NO_JOB_SERVICE"}
        self.dataChanged.emit()
        return self._jb.runJob("library_scan", path)

    @Slot(str, result=dict)
    def cancelSourceScan(self, path: str):
        if not self._jb:
            return {"ok": False, "error": "NO_JOB_SERVICE"}
        self._status = "idle"
        self.dataChanged.emit()
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}

    @Slot(result=dict)
    def scanAllSources(self):
        if not self._jb:
            return {"ok": False, "error": "NO_JOB_SERVICE"}
        return self._jb.runJob("library_scan_all")

    @Slot(str, str, result=dict)
    def relinkSource(self, old_path: str, new_path: str):
        if not Path(new_path).is_dir():
            return {"ok": False, "error": "DIR_NOT_FOUND"}
        remove = self._svc.remove(old_path)
        if not remove.get("ok"):
            return {"ok": False, "error": "SOURCE_NOT_FOUND"}
        add = self._svc.add(new_path)
        self.dataChanged.emit()
        return add

    @Slot(str, result=dict)
    def setExclusion(self, path: str):
        if path not in self._exclusions:
            self._exclusions.append(path)
        return {"ok": True, "exclusions": list(self._exclusions)}

    @Slot(str, result=dict)
    def removeExclusion(self, path: str):
        self._exclusions = [e for e in self._exclusions if e != path]
        return {"ok": True, "exclusions": list(self._exclusions)}

    @Slot(result=dict)
    def watchState(self):
        import time
        return {
            "ok": True,
            "sources": self._svc.list(),
            "status": self._status,
            "exclusions": list(self._exclusions),
            "timestamp": time.time(),
        }

    @Slot(result=dict)
    def refreshAvailability(self):
        self.dataChanged.emit()
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}

    @Slot(str, result=dict)
    def openSource(self, path: str):
        import subprocess
        import os
        if os.name == "nt":
            subprocess.Popen(["explorer", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return {"ok": False, "error": "METHOD_UNAVAILABLE"}

    @Slot(str, result=dict)
    def scanFolder(self, path: str):
        if self._folder_svc and hasattr(self._folder_svc, 'scan'):
            return self._folder_svc.scan(path)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    @Slot(str, result=dict)
    def checkIntegrity(self, path: str):
        if self._folder_svc and hasattr(self._folder_svc, 'integrity_check'):
            return self._folder_svc.integrity_check(path)
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def root_paths(self) -> list[str]:
        return self._svc.root_paths()
