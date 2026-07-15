"""AudioLabBridge -- connects Audio Lab QML to AudioLabService."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot


class AudioLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, audio_lab_service=None, job_service=None, parent=None):
        super().__init__(parent)
        self._svc = audio_lab_service
        self._jobs = job_service
        self._active = False

    @Property(bool, notify=dataChanged)
    def serviceAvailable(self):
        return self._svc is not None

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def startAnalysis(self, filepath: str):
        if not self._svc:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        return {"ok": True}

    @Slot(str, result=dict)
    def cancelJob(self, job_id: str):
        if self._jobs and hasattr(self._jobs, 'cancel'):
            return self._jobs.cancel(job_id)
        return {"ok": False, "error_code": "UNSUPPORTED"}
