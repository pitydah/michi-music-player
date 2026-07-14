"""AudioLabState — QObject state container for Audio Lab orchestration.

Maintains state across subroutines: input descriptors, source context,
selected profile, output, preview, active jobs, results, errors.
"""
from __future__ import annotations

import time
from typing import Any

from PySide6.QtCore import QObject, Signal, Property, Slot


class AudioLabState(QObject):
    stateChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._inputs: list[dict[str, Any]] = []
        self._source_context: str = ""
        self._selected_profile: str = ""
        self._output_dir: str = ""
        self._preview: dict[str, Any] | None = None
        self._active_jobs: dict[str, dict[str, Any]] = {}
        self._results: list[dict[str, Any]] = []
        self._errors: list[str] = []

    @Property("QVariantList", notify=stateChanged)
    def inputs(self):
        return self._inputs

    @inputs.setter
    def inputs(self, val: list[dict[str, Any]]):
        self._inputs = val
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def sourceContext(self):
        return self._source_context

    @sourceContext.setter
    def sourceContext(self, val: str):
        self._source_context = val
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def selectedProfile(self):
        return self._selected_profile

    @selectedProfile.setter
    def selectedProfile(self, val: str):
        self._selected_profile = val
        self.stateChanged.emit()

    @Property(str, notify=stateChanged)
    def outputDir(self):
        return self._output_dir

    @outputDir.setter
    def outputDir(self, val: str):
        self._output_dir = val
        self.stateChanged.emit()

    @Property("QVariantMap", notify=stateChanged)
    def previewData(self):
        return self._preview or {}

    @previewData.setter
    def previewData(self, val: dict[str, Any] | None):
        self._preview = val
        self.stateChanged.emit()

    @Property("QVariantList", notify=stateChanged)
    def results(self):
        return self._results

    @results.setter
    def results(self, val: list[dict[str, Any]]):
        self._results = val
        self.stateChanged.emit()

    @Property("QVariantList", notify=stateChanged)
    def errors(self):
        return self._errors

    @errors.setter
    def errors(self, val: list[str]):
        self._errors = val
        self.stateChanged.emit()

    @Slot(str, result=dict)
    def getJob(self, job_id: str) -> dict[str, Any]:
        return self._active_jobs.get(job_id, {})

    @Slot(result="QVariantList")
    def activeJobs(self) -> list[dict[str, Any]]:
        return list(self._active_jobs.values())

    @Slot(str)
    def addInput(self, filepath: str):
        self._inputs.append({"filepath": filepath, "added_at": time.time()})
        self.stateChanged.emit()

    @Slot(str)
    def removeInput(self, filepath: str):
        self._inputs = [i for i in self._inputs if i["filepath"] != filepath]
        self.stateChanged.emit()

    @Slot()
    def clearInputs(self):
        self._inputs.clear()
        self._preview = None
        self._results.clear()
        self._errors.clear()
        self.stateChanged.emit()

    def track_job(self, job_id: str, job_type: str, source: str):
        self._active_jobs[job_id] = {
            "id": job_id, "type": job_type, "source": source,
            "status": "queued", "progress": 0.0,
            "created_at": time.time(),
        }
        self.stateChanged.emit()

    def update_job(self, job_id: str, **kwargs):
        job = self._active_jobs.get(job_id)
        if job:
            job.update(kwargs)
            self.stateChanged.emit()

    def remove_job(self, job_id: str):
        self._active_jobs.pop(job_id, None)
        self.stateChanged.emit()

    def add_result(self, result: dict[str, Any]):
        self._results.append(result)
        self.stateChanged.emit()

    def add_error(self, error: str):
        self._errors.append(error)
        self.stateChanged.emit()

    def reset(self):
        self._inputs.clear()
        self._source_context = ""
        self._selected_profile = ""
        self._output_dir = ""
        self._preview = None
        self._active_jobs.clear()
        self._results.clear()
        self._errors.clear()
        self.stateChanged.emit()
