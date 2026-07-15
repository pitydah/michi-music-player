from __future__ import annotations

import logging
import uuid

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.audio_lab.bridge")


class AudioLabBridge(QObject):
    dataChanged = Signal()
    jobProgress = Signal(str, str, float)
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)
    serviceAvailableChanged = Signal()

    def __init__(self, audio_lab_service=None, job_service=None,
                 process_controller=None, confirmation_service=None,
                 navigation_bridge=None, capability_bridge=None,
                 db_conn=None, player_service=None, parent=None):
        super().__init__(parent)
        self._svc = audio_lab_service
        self._jobs = job_service
        self._pc = process_controller
        self._confirm = confirmation_service
        self._nav = navigation_bridge
        self._cap = capability_bridge
        self._active_jobs: dict[str, dict] = {}
        self._db_conn = db_conn
        self._player_service = player_service

    @Property(bool, notify=dataChanged)
    def serviceAvailable(self):
        return self._svc is not None

    @Property(bool, notify=dataChanged)
    def jobServiceAvailable(self):
        return self._jobs is not None

    @Slot(result=dict)
    def capabilityMap(self):
        if not self._svc:
            return {}
        return self._svc.capability_map()

    @Slot(str, result=dict)
    def previewAnalysis(self, filepath: str):
        if not self._svc or not self._svc.analysis:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.analysis.analyze_file(filepath)
            preview = {
                "filepath": result.get("filepath", filepath),
                "format": result.get("format", ""),
                "sample_rate": result.get("sample_rate", 0),
                "bit_depth": result.get("bit_depth", 0),
                "channels": result.get("channels", 0),
                "bitrate": result.get("bitrate", 0),
                "duration": result.get("duration", 0.0),
                "codec": result.get("codec", ""),
                "status": result.get("status", "unknown"),
                "ok": result.get("status") not in ("error",),
            }
            return preview
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def validateAnalysis(self, filepath: str):
        if not self._svc or not self._svc.analysis:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.analysis.analyze_file(filepath)
            valid = result.get("status") not in ("error", "unsupported", "disabled")
            return {"ok": valid, "filepath": filepath, "status": result.get("status")}
        except Exception as e:
            return {"ok": False, "error_code": "VALIDATE_FAILED", "detail": str(e)}

    @Slot(str, result=str)
    def startAnalysis(self, filepath: str):
        if not self._svc or not self._svc.analysis:
            return ""
        job_id = f"analysis_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": "analysis", "filepath": filepath, "status": "running"}

        def _run():
            return self._svc.analysis.analyze_file(filepath)

        def _done(result):
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = result
            self.jobCompleted.emit(job_id, "analysis", result)
            self.dataChanged.emit()

        if self._pc and hasattr(self._pc, 'run_in_thread'):
            self._pc.run_in_thread(job_id, _run, on_done=_done)
        elif self._svc._wm:
            self._svc._wm.run_task(job_id, _run, on_done=_done, cancellable=True, owner="audio_lab")
        else:
            result = _run()
            _done(result)
        self.dataChanged.emit()
        return job_id

    @Slot(str, result=dict)
    def previewConversion(self, filepath: str, target_format: str = "flac"):
        if not self._svc or not self._svc.conversion:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            from core.audio_lab.audio_conversion_service import ConversionProfile
            profile = ConversionProfile(format=target_format.upper())
            result = self._svc.conversion.preview(filepath, profile)
            return result
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=str)
    def startConversion(self, filepath: str, target_format: str = "flac"):
        if not self._svc or not self._svc.conversion:
            return ""
        from core.audio_lab.audio_conversion_service import ConversionProfile
        profile = ConversionProfile(format=target_format.upper())
        job_id = self._svc.conversion.convert(filepath, profile)
        self._active_jobs[job_id] = {"type": "conversion", "filepath": filepath, "status": "running"}
        self._svc.conversion.conversionCompleted.connect(
            lambda jid, target: self._on_job_done(jid, "conversion", {"target": target})
        )
        self._svc.conversion.conversionFailed.connect(
            lambda jid, err: self._on_job_failed(jid, "conversion", err)
        )
        self.dataChanged.emit()
        return job_id

    def _on_job_done(self, job_id, job_type, result):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = result
            self.jobCompleted.emit(job_id, job_type, result)
            self.dataChanged.emit()

    def _on_job_failed(self, job_id, job_type, error):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "failed"
            self._active_jobs[job_id]["error"] = error
            self.jobFailed.emit(job_id, error)
            self.dataChanged.emit()

    @Slot(str, result=dict)
    def previewNormalization(self, filepath: str):
        if not self._svc or not self._svc.normalization:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.normalization.measure_loudness(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "integrated_loudness": result.integrated_loudness,
                "true_peak": result.true_peak,
                "loudness_range": result.loudness_range,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=dict)
    def startNormalization(self, filepath: str, confirmation_token: str = ""):
        if not self._svc or not self._svc.normalization:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            needs_confirm = self._svc.normalization.normalize_file(
                filepath, destructive=True, confirmation_token=confirmation_token or None
            )
            if isinstance(needs_confirm, dict) and needs_confirm.get("requires_confirmation"):
                return needs_confirm
            return {"ok": True, "status": "metadata_only", "message": "Usar ReplayGain para normalizacion no destructiva"}
        except Exception as e:
            return {"ok": False, "error_code": "NORMALIZE_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def previewReplayGain(self, filepath: str):
        if not self._svc or not self._svc.replaygain:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.replaygain.analyze_track(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "track_gain": result.track_gain,
                "track_peak": result.track_peak,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def validateReplayGain(self, filepath: str):
        if not self._svc or not self._svc.replaygain:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.replaygain.analyze_track(filepath)
            return {
                "ok": result.status == "completed",
                "filepath": result.filepath,
                "status": result.status,
            }
        except Exception as e:
            return {"ok": False, "error_code": "VALIDATE_FAILED", "detail": str(e)}

    @Slot(str, result=str)
    def startReplayGain(self, filepath: str):
        if not self._svc or not self._svc.replaygain:
            return ""
        job_id = f"rg_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": "replaygain", "filepath": filepath, "status": "running"}

        def _run():
            result = self._svc.replaygain.analyze_track(filepath)
            if result.status == "completed":
                self._svc.replaygain.write_tags(
                    filepath, result.track_gain, result.track_peak,
                    album_gain=result.album_gain, album_peak=result.album_peak
                )
            return result

        def _done(result):
            d = {"track_gain": result.track_gain, "track_peak": result.track_peak, "status": result.status}
            self._active_jobs[job_id]["status"] = "completed" if result.status == "completed" else "failed"
            if result.status == "completed":
                self.jobCompleted.emit(job_id, "replaygain", d)
            else:
                self.jobFailed.emit(job_id, result.error)
            self.dataChanged.emit()

        if self._pc and hasattr(self._pc, 'run_in_thread'):
            self._pc.run_in_thread(job_id, _run, on_done=_done)
        elif self._svc._wm:
            self._svc._wm.run_task(job_id, _run, on_done=_done, cancellable=True, owner="audio_lab")
        else:
            result = _run()
            _done(result)
        self.dataChanged.emit()
        return job_id

    @Slot(str, result=dict)
    def previewIntegrity(self, filepath: str):
        if not self._svc or not self._svc.integrity:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.integrity.check(filepath, quick=True)
            return {
                "ok": result.is_valid,
                "filepath": result.filepath,
                "status": result.status,
                "issues": result.issues,
                "duration": result.duration,
                "size": result.file_size,
                "is_valid": result.is_valid,
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, result=dict)
    def validateIntegrity(self, filepath: str):
        return self.previewIntegrity(filepath)

    @Slot(str, result=str)
    def startIntegrity(self, filepath: str):
        if not self._svc or not self._svc.integrity:
            return ""
        job_id = f"integrity_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": "integrity", "filepath": filepath, "status": "running"}

        def _run():
            return self._svc.integrity.check(filepath, quick=False)

        def _done(result):
            d = {"is_valid": result.is_valid, "issues": result.issues, "checksum": result.checksum}
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = d
            self.jobCompleted.emit(job_id, "integrity", d)
            self.dataChanged.emit()

        if self._pc and hasattr(self._pc, 'run_in_thread'):
            self._pc.run_in_thread(job_id, _run, on_done=_done)
        elif self._svc._wm:
            self._svc._wm.run_task(job_id, _run, on_done=_done, cancellable=True, owner="audio_lab")
        else:
            result = _run()
            _done(result)
        self.dataChanged.emit()
        return job_id

    @Slot(str, str, result=dict)
    def previewComparison(self, file_a: str, file_b: str):
        if not self._svc or not self._svc.comparison:
            return {"ok": False, "error_code": "SERVICE_UNAVAILABLE"}
        try:
            result = self._svc.comparison.compare(file_a, file_b)
            return {
                "ok": not result.error,
                "identical": result.identical,
                "dimensions": [{
                    "key": d.key, "label": d.label,
                    "value_a": d.value_a, "value_b": d.value_b,
                    "identical": d.identical,
                } for d in result.dimensions],
            }
        except Exception as e:
            return {"ok": False, "error_code": "PREVIEW_FAILED", "detail": str(e)}

    @Slot(str, str, result=str)
    def startComparison(self, file_a: str, file_b: str):
        if not self._svc or not self._svc.comparison:
            return ""
        job_id = f"compare_{uuid.uuid4().hex[:8]}"
        self._active_jobs[job_id] = {"type": "comparison", "status": "running"}

        def _run():
            return self._svc.comparison.compare(file_a, file_b)

        def _done(result):
            d = {"identical": result.identical, "dimensions": len(result.dimensions)}
            self._active_jobs[job_id]["status"] = "completed"
            self._active_jobs[job_id]["result"] = d
            self.jobCompleted.emit(job_id, "comparison", d)
            self.dataChanged.emit()

        if self._pc and hasattr(self._pc, 'run_in_thread'):
            self._pc.run_in_thread(job_id, _run, on_done=_done)
        elif self._svc._wm:
            self._svc._wm.run_task(job_id, _run, on_done=_done, cancellable=True, owner="audio_lab")
        else:
            result = _run()
            _done(result)
        self.dataChanged.emit()
        return job_id

    @Slot(str, result=dict)
    def cancelJob(self, job_id: str):
        if job_id in self._active_jobs:
            self._active_jobs[job_id]["status"] = "cancelled"
            if self._pc and hasattr(self._pc, 'cancel'):
                self._pc.cancel(job_id)
            elif self._svc and self._svc._wm and hasattr(self._svc._wm, 'cancel'):
                self._svc._wm.cancel(job_id)
            self.dataChanged.emit()
            return {"ok": True, "job_id": job_id}
        if self._jobs and hasattr(self._jobs, 'cancel'):
            result = self._jobs.cancel(job_id)
            if result and result.get("ok"):
                self.dataChanged.emit()
                return result
        return {"ok": False, "error_code": "JOB_NOT_FOUND"}

    @Slot(str, result=dict)
    def retryJob(self, job_id: str):
        info = self._active_jobs.get(job_id)
        if not info:
            return {"ok": False, "error_code": "JOB_NOT_FOUND"}
        job_type = info.get("type")
        filepath = info.get("filepath", "")
        if job_type == "analysis" and filepath:
            new_id = self.startAnalysis(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        if job_type == "replaygain" and filepath:
            new_id = self.startReplayGain(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        if job_type == "integrity" and filepath:
            new_id = self.startIntegrity(filepath)
            return {"ok": True, "new_job_id": new_id, "type": job_type}
        return {"ok": False, "error_code": "RETRY_UNSUPPORTED"}

    @Slot(result=dict)
    def cleanupCompleted(self):
        count = 0
        finished = [jid for jid, info in self._active_jobs.items()
                    if info.get("status") in ("completed", "failed", "cancelled")]
        for jid in finished:
            del self._active_jobs[jid]
            count += 1
        self.dataChanged.emit()
        return {"ok": True, "cleaned": count}

    @Slot(str, result=dict)
    def jobStatus(self, job_id: str):
        info = self._active_jobs.get(job_id)
        if info:
            return {"ok": True, "job_id": job_id, "status": info.get("status"),
                    "type": info.get("type"), "filepath": info.get("filepath", "")}
        if self._jobs and hasattr(self._jobs, 'status'):
            result = self._jobs.status(job_id)
            if result and result.get("ok"):
                return result
        return {"ok": False, "error_code": "JOB_NOT_FOUND"}

    @Slot(result=dict)
    def activeJobs(self):
        return {jid: info.get("status") for jid, info in self._active_jobs.items()}

    @Slot(result=dict)
    def refresh(self):
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def navigateTo(self, route: str):
        if self._nav:
            return self._nav.navigate(route)
        return {"ok": False, "error_code": "NAVIGATION_UNAVAILABLE"}

    @Slot(str, result=dict)
    def requireConfirmation(self, action: str):
        if self._confirm:
            return self._confirm.request(action)
        return {"ok": False, "error_code": "CONFIRMATION_UNAVAILABLE"}

    @Slot(result=dict)
    def partialFailureReport(self):
        failed = [{"job_id": jid, "type": info.get("type"), "error": info.get("error", "")}
                  for jid, info in self._active_jobs.items()
                  if info.get("status") == "failed"]
        return {"ok": True, "has_failures": bool(failed), "failures": failed}
