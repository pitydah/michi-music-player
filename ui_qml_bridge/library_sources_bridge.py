"""LibrarySourcesBridge — QML bridge for LibrarySourcesService."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

from core.library_sources_service import LibrarySourcesService

logger = logging.getLogger("michi.library_sources_bridge")


class LibrarySourcesBridge(QObject):
    dataChanged = Signal()

    def __init__(self, service: LibrarySourcesService | None = None, parent=None):
        super().__init__(parent)
        self._svc = service or LibrarySourcesService()
        self._status = "ready"

    @Property("QVariantList", notify=dataChanged)
    def sources(self):
        return self._svc.list()

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def addSource(self, path: str):
        result = self._svc.add(path)
        self.dataChanged.emit()
        return result

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
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge(db=self._svc._db if hasattr(self._svc, '_db') else None)
        result = jb.runJob("library_scan", path)
        return result

    @Slot(result=dict)
    def scanAllSources(self):
        from ui_qml_bridge.job_bridge import JobBridge
        jb = JobBridge(db=self._svc._db if hasattr(self._svc, '_db') else None)
        result = jb.runJob("library_scan_all")
        return result

    def root_paths(self) -> list[str]:
        return self._svc.root_paths()
