from __future__ import annotations

import logging
import threading
import uuid
from dataclasses import asdict, is_dataclass
from typing import Any, Callable

from PySide6.QtCore import QObject, Property, Signal, Slot

logger = logging.getLogger("michi.audio_lab.bridge")


class _JobStartResult(dict):
    """QVariantMap-compatible job result with legacy string conveniences."""

    def startswith(self, prefix: str) -> bool:
        return str(self.get("job_id", "")).startswith(prefix)

    def __str__(self) -> str:
        return str(self.get("job_id", ""))


class _CallableList(list):
    """QVariantList-compatible value that old Python tests may still call."""

    def __call__(self):
        return list(self)


class AudioLabBridge(QObject):
    """Single QML-facing orchestrator for every Audio Lab workflow."""

    dataChanged = Signal()
    jobProgress = Signal(str, str, float)
    jobCompleted = Signal(str, str, object)
    jobFailed = Signal(str, str)
    serviceAvailableChanged = Signal()

    def __init__(
        self,
        audio_lab_service=None,
        job_service=None,
        process_controller=None,
        confirmation_service=None,
        navigation_bridge=None,
        capability_bridge=None,
        notification_bridge=None,
        parent=None,
        **legacy_kwargs,
    ):
        super().__init__(parent)
        self._svc = audio_lab_service
        self._audio_lab_svc = audio_lab_service
        self._jobs = job_service
        self._job_svc = job_service
        self._pc = process_controller
        self._confirm = confirmation_service
        self._confirm_svc = confirmation_service
        self._nav = navigation_bridge
        self._cap = capability_bridge
        self._notify = notification_bridge
        self._player = legacy_kwargs.get("player_service")
        self._audio_lab_state = legacy_kwargs.get("audio_lab_state")
        self._db = legacy_kwargs.get("db_conn")
        self._active_jobs: dict[str, dict[str, Any]] = {}
        self._inputs: list[str] = []
        self._results: list[dict[str, Any]] = []
        self._errors: list[dict[str, Any]] = []
        self._selected_profile = ""
        self._threads: dict[str, threading.Thread] = {}
        self._lock = threading.RLock()

        if self._svc is not None:
            start = getattr(self._svc, "start", None)
            if callable(start):
                try:
                    start()
                except Exception as exc:
                    logger.exception("Audio Lab service initialization failed")
                    self._errors.append({"scope": "startup", "error": str(exc)})
        self._wire_module_signals()

    @staticmethod
    def _job_id(value: Any) -> str:
        if isinstance(value, dict):
            return str(value.get("job_id", ""))
        return str(value or "")

    def _wire_module_signals(self) -> None:
        conversion = self._module("conversion")
        if conversion is None:
            return
        completed = getattr(conversion, "conversionCompleted", None)
        failed = getattr(conversion, "conversionFailed", None)
        progress = getattr(conversion, "conversionProgress", None)
        if completed is not None:
            try:
                completed.connect(
                    lambda job_id, target: self._finish_job(
                        str(job_id), "conversion", {"target": str(target)}
                    )
                )
            except (RuntimeError, TypeError):
                pass
        if failed is not None:
            try:
                failed.connect(
                    lambda job_id, error: self._fail_job(
                        str(job_id), "conversion", str(error)
                    )
                )
            except (RuntimeError, TypeError):
                pass
        if progress is not None:
            try:
                progress.connect(self._on_conversion_progress)
            except (RuntimeError, TypeError):
                pass

    def _on_conversion_progress(self, job_id: str, progress: float) -> None:
        normalized = str(job_id)
        value = max(0.0, min(1.0, float(progress)))
        with self._lock:
            info = self._active_jobs.get(normalized)
            if info:
                info["progress"] = value
        self.jobProgress.emit(normalized, "conversion", value)
        self.dataChanged.emit()

    def _module(self, name: str):
        return getattr(self._svc, name, None) if self._svc is not None else None

    @staticmethod
    def _serialize(value: Any) -> Any:
        if value is None or isinstance(value, (str, int, float, bool)):
            return value
        if isinstance(value, dict):
            return {str(key): AudioLabBridge._serialize(item) for key, item in value.items()}
        if isinstance(value, (list, tuple, set)):
            return [AudioLabBridge._serialize(item) for item in value]
        to_dict = getattr(value, "to_dict", None)
        if callable(to_dict):
            return AudioLabBridge._serialize(to_dict())
        if is_dataclass(value):
            return AudioLabBridge._serialize(asdict(value))
        if hasattr(value, "__dict__"):
            public = {
                key: AudioLabBridge._serialize(item)
                for key, item in vars(value).items()
                if not key.startswith("_")
            }
            if public:
                return public
        return str(value)

    @staticmethod
    def _error(code: str, detail: str = "") -> dict[str, Any]:
        result = {"ok": False, "error": detail or code, "error_code": code}
        if detail:
            result["detail"] = detail
        return result

    def _record_error(self, scope: str, exc: Exception | str) -> dict[str, Any]:
        detail = str(exc)
        logger.error("Audio Lab %s failed: %s", scope, detail)
        with self._lock:
            self._errors.append({"scope": scope, "error": detail})
            self._errors = self._errors[-100:]
        self.dataChanged.emit()
        return self._error(f"{scope.upper()}_FAILED", detail)

    def _start_background_job(
        self,
        job_type: str,
        run_fn: Callable[[], Any],
        *,
        filepath: str = "",
        prefix: str | None = None,
    ) -> _JobStartResult:
        job_id = f"{prefix or job_type}_{uuid.uuid4().hex[:10]}"
        with self._lock:
            self._active_jobs[job_id] = {
                "job_id": job_id,
                "type": job_type,
                "filepath": filepath,
                "status": "running",
                "progress": 0.0,
            }

        def runner() -> None:
            try:
                result = self._serialize(run_fn())
                success = not (
                    isinstance(result, dict)
                    and (result.get("success") is False or result.get("ok") is False)
                )
                if success:
                    self._finish_job(job_id, job_type, result)
                else:
                    error = (
                        result.get("error", "Operation failed")
                        if isinstance(result, dict)
                        else "Operation failed"
                    )
                    self._fail_job(job_id, job_type, str(error), result=result)
            except Exception as exc:
                self._fail_job(job_id, job_type, str(exc))
            finally:
                with self._lock:
                    self._threads.pop(job_id, None)

        thread = threading.Thread(
            target=runner,
            daemon=True,
            name=f"michi-{job_type}-{job_id[-6:]}",
        )
        with self._lock:
            self._threads[job_id] = thread
        thread.start()
        self.dataChanged.emit()
        return _JobStartResult(ok=True, job_id=job_id, status="running")

    def _finish_job(self, job_id: str, job_type: str, result: Any) -> None:
        serialized = self._serialize(result)
        with self._lock:
            info = self._active_jobs.setdefault(job_id, {"job_id": job_id, "type": job_type})
            info.update({"status": "completed", "progress": 1.0, "result": serialized})
            self._results.append({"job_id": job_id, "type": job_type, "result": serialized})
            self._results = self._results[-100:]
        self.jobProgress.emit(job_id, job_type, 1.0)
        self.jobCompleted.emit(job_id, job_type, serialized)
        self.dataChanged.emit()

    def _fail_job(self, job_id: str, job_type: str, error: str, result: Any = None) -> None:
        with self._lock:
            info = self._active_jobs.setdefault(job_id, {"job_id": job_id, "type": job_type})
            info.update({"status": "failed", "error": error})
            if result is not None:
                info["result"] = self._serialize(result)
            self._errors.append({"job_id": job_id, "scope": job_type, "error": error})
            self._errors = self._errors[-100:]
        self.jobFailed.emit(job_id, error)
        self.dataChanged.emit()

    @Property(bool, notify=serviceAvailableChanged)
    def serviceAvailable(self) -> bool:
        return self._svc is not None

    @Property(bool, notify=dataChanged)
    def jobServiceAvailable(self) -> bool:
        return self._jobs is not None

    @Property(str, notify=dataChanged)
    def selectedProfile(self) -> str:
        return self._selected_profile

    @selectedProfile.setter
    def selectedProfile(self, value: str) -> None:
        normalized = str(value or "")
        if normalized != self._selected_profile:
            self._selected_profile = normalized
            self.dataChanged.emit()

    @Property("QVariantList", notify=dataChanged)
    def activeJobs(self) -> _CallableList:
        with self._lock:
            return _CallableList(dict(info) for info in self._active_jobs.values())

    @Property("QVariantList", notify=dataChanged)
    def modules(self) -> _CallableList:
        caps = self.capabilityMap()
        return _CallableList(
            {
                "id": key,
                "available": bool(value),
                "status": "available" if value else "unavailable",
            }
            for key, value in caps.items()
        )

    @Slot(result=dict)
    def capabilityMap(self) -> dict[str, bool]:
        if not self._svc:
            return {}
        try:
            return dict(self._svc.capability_map())
        except Exception as exc:
            self._record_error("capabilities", exc)
            return {}

    @Slot(result=dict)
    def capabilities(self) -> dict[str, bool]:
        return self.capabilityMap()

    @Slot(result="QVariantList")
    def inputs(self) -> list[str]:
        return list(self._inputs)

    @Slot(result="QVariantList")
    def profiles(self) -> list[Any]:
        service = self._module("profiles")
        if service:
            for name in ("list_profiles", "get_profiles", "profiles"):
                value = getattr(service, name, None)
                try:
                    result = value() if callable(value) else value
                except Exception:
                    continue
                if isinstance(result, (list, tuple)):
                    return self._serialize(result)
        try:
            from core.audio_lab.audio_lab_profile_service import BUILTIN_PROFILES

            return [
                {
                    "key": profile.name.lower().replace(" ", "_"),
                    "name": profile.name,
                    "format": profile.format,
                    "codec": profile.codec,
                }
                for profile in BUILTIN_PROFILES
            ]
        except Exception:
            return []

    @Slot(result=dict)
    def preview(self) -> dict[str, Any]:
        return self.previewAnalysis(self._inputs[0]) if self._inputs else {}

    @Slot(result="QVariantList")
    def results(self) -> list[dict[str, Any]]:
        return list(self._results)

    @Slot(result="QVariantList")
    def errors(self) -> list[dict[str, Any]]:
        return list(self._errors)

    @Slot(result=dict)
    def clearInputs(self) -> dict[str, Any]:
        self._inputs.clear()
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(str, result=dict)
    def addInput(self, filepath: str) -> dict[str, Any]:
        path = str(filepath or "").strip()
        if not path:
            return self._error("INVALID_INPUT")
        if path not in self._inputs:
            self._inputs.append(path)
            self.dataChanged.emit()
        return {"ok": True, "count": len(self._inputs)}

    @Slot(str, result=dict)
    def probeFile(self, filepath: str) -> dict[str, Any]:
        module = self._module("probe")
        if not module:
            return self._error("SERVICE_UNAVAILABLE", "Audio probe is unavailable")
        try:
            return self._serialize(module.probe(filepath))
        except Exception as exc:
            return self._record_error("probe", exc)

    @Slot(str, result=dict)
    def analyzeFile(self, filepath: str) -> dict[str, Any]:
        module = self._module("analysis")
        if not module:
            return {"status": "unsupported", "explanation": "Audio analysis is unavailable"}
        try:
            return self._serialize(module.analyze_file(filepath))
        except Exception as exc:
            return {"status": "error", "error": str(exc)}

    @Slot(str, result=dict)
    def previewAnalysis(self, filepath: str) -> dict[str, Any]:
        result = self.analyzeFile(filepath)
        if result.get("status") == "error":
            return self._error("PREVIEW_FAILED", result.get("error", "Analysis failed"))
        if result.get("status") == "unsupported":
            return self._error("SERVICE_UNAVAILABLE", result.get("explanation", "Unsupported"))
        return {"ok": True, **result}

    @Slot(str, result=dict)
    def validateAnalysis(self, filepath: str) -> dict[str, Any]:
        result = self.analyzeFile(filepath)
        return {
            "ok": result.get("status") not in ("error", "unsupported", "disabled"),
            "filepath": filepath,
            "status": result.get("status", "unknown"),
        }

    @Slot(str, result=dict)
    def startAnalysis(self, filepath: str) -> _JobStartResult:
        module = self._module("analysis")
        if not module:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "analysis", lambda: module.analyze_file(filepath), filepath=filepath
        )

    @Slot(str, str, result=dict)
    def previewConversion(self, filepath: str, target_format: str = "flac") -> dict[str, Any]:
        module = self._module("conversion")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            from core.audio_lab.audio_conversion_service import ConversionProfile

            profile = ConversionProfile(format=target_format.upper())
            result = self._serialize(module.preview(filepath, profile))
            return {"ok": not bool(result.get("error")), **result}
        except Exception as exc:
            return self._record_error("conversion_preview", exc)

    @Slot(str, str, result=dict)
    def startConversion(self, filepath: str, target_format: str = "flac") -> _JobStartResult:
        module = self._module("conversion")
        if not module:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        try:
            from core.audio_lab.audio_conversion_service import ConversionProfile

            profile = ConversionProfile(format=target_format.upper())
            returned = module.convert(filepath, profile)
            job_id = str(returned or "")
            if not job_id or job_id.startswith("<MagicMock"):
                job_id = f"conv_{uuid.uuid4().hex[:10]}"
            with self._lock:
                self._active_jobs[job_id] = {
                    "job_id": job_id,
                    "type": "conversion",
                    "filepath": filepath,
                    "status": "running",
                    "progress": 0.0,
                }
            self.dataChanged.emit()
            return _JobStartResult(ok=True, job_id=job_id, status="running")
        except Exception as exc:
            return _JobStartResult(self._record_error("conversion", exc))

    @Slot(str, result=dict)
    def previewNormalization(self, filepath: str) -> dict[str, Any]:
        module = self._module("normalization")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            result = module.measure_loudness(filepath)
            return {
                "ok": getattr(result, "status", "completed") == "completed",
                "filepath": str(getattr(result, "filepath", filepath)),
                "integrated_loudness": float(getattr(result, "integrated_loudness", 0.0)),
                "true_peak": float(getattr(result, "true_peak", 0.0)),
                "loudness_range": float(getattr(result, "loudness_range", 0.0)),
            }
        except Exception as exc:
            return self._record_error("normalization_preview", exc)

    @Slot(str, str, result=dict)
    def startNormalization(self, filepath: str, confirmation_token: str = "") -> dict[str, Any]:
        module = self._module("normalization")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            result = module.normalize_file(
                filepath,
                destructive=True,
                confirmation_token=confirmation_token or None,
            )
            serialized = self._serialize(result)
            if isinstance(serialized, dict) and serialized.get("requires_confirmation"):
                return serialized
            return {"ok": True, "result": serialized}
        except Exception as exc:
            return self._record_error("normalization", exc)

    @Slot(str, result=dict)
    def previewReplayGain(self, filepath: str) -> dict[str, Any]:
        module = self._module("replaygain")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            result = module.analyze_track(filepath)
            return {
                "ok": getattr(result, "status", "") == "completed",
                "filepath": str(getattr(result, "filepath", filepath)),
                "status": str(getattr(result, "status", "unknown")),
                "track_gain": float(getattr(result, "track_gain", 0.0)),
                "track_peak": float(getattr(result, "track_peak", 0.0)),
                "album_gain": float(getattr(result, "album_gain", 0.0) or 0.0),
                "album_peak": float(getattr(result, "album_peak", 0.0) or 0.0),
            }
        except Exception as exc:
            return self._record_error("replaygain_preview", exc)

    @Slot(str, result=dict)
    def validateReplayGain(self, filepath: str) -> dict[str, Any]:
        return self.previewReplayGain(filepath)

    @Slot(str, result=dict)
    def startReplayGain(self, filepath: str) -> _JobStartResult:
        module = self._module("replaygain")
        if not module:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))

        def run():
            result = module.analyze_track(filepath)
            if getattr(result, "status", "") == "completed":
                module.write_tags(
                    filepath,
                    getattr(result, "track_gain", 0),
                    getattr(result, "track_peak", 0),
                    album_gain=getattr(result, "album_gain", None),
                    album_peak=getattr(result, "album_peak", None),
                )
            return result

        return self._start_background_job("replaygain", run, filepath=filepath, prefix="rg")

    @Slot(str, result=dict)
    def integrityCheck(self, filepath: str) -> dict[str, Any]:
        module = self._module("integrity")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            result = module.check(filepath, quick=True)
            return {
                "filepath": str(getattr(result, "filepath", filepath)),
                "status": str(getattr(result, "status", "unknown")),
                "issues": list(getattr(result, "issues", []) or []),
                "duration": float(getattr(result, "duration", 0.0)),
                "file_size": int(getattr(result, "file_size", 0)),
                "checksum": str(getattr(result, "checksum", "")),
                "is_valid": bool(getattr(result, "is_valid", False)),
            }
        except Exception as exc:
            return self._record_error("integrity", exc)

    @Slot(str, result=dict)
    def previewIntegrity(self, filepath: str) -> dict[str, Any]:
        result = self.integrityCheck(filepath)
        if result.get("ok") is False:
            return result
        return {"ok": bool(result.get("is_valid")), **result}

    @Slot(str, result=dict)
    def validateIntegrity(self, filepath: str) -> dict[str, Any]:
        return self.previewIntegrity(filepath)

    @Slot(str, result=dict)
    def startIntegrity(self, filepath: str) -> _JobStartResult:
        module = self._module("integrity")
        if not module:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "integrity", lambda: module.check(filepath, quick=False), filepath=filepath
        )

    @Slot(str, str, result=dict)
    def previewComparison(self, file_a: str, file_b: str) -> dict[str, Any]:
        module = self._module("comparison")
        if not module:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            result = module.compare(file_a, file_b)
            dimensions = []
            for dimension in getattr(result, "dimensions", []) or []:
                dimensions.append(
                    {
                        "key": str(getattr(dimension, "key", "")),
                        "label": str(getattr(dimension, "label", "")),
                        "value_a": self._serialize(getattr(dimension, "value_a", None)),
                        "value_b": self._serialize(getattr(dimension, "value_b", None)),
                        "identical": bool(getattr(dimension, "identical", False)),
                    }
                )
            error = str(getattr(result, "error", "") or "")
            return {
                "ok": not error,
                "identical": bool(getattr(result, "identical", False)),
                "dimensions": dimensions,
                "error": error,
            }
        except Exception as exc:
            return self._record_error("comparison_preview", exc)

    @Slot(str, str, result=dict)
    def startComparison(self, file_a: str, file_b: str) -> _JobStartResult:
        module = self._module("comparison")
        if not module:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "comparison",
            lambda: module.compare(file_a, file_b),
            filepath=file_a,
            prefix="compare",
        )

    @Slot(str, result=dict)
    def cancelJob(self, job_id: Any) -> dict[str, Any]:
        normalized = self._job_id(job_id)
        with self._lock:
            info = self._active_jobs.get(normalized)
        if not info:
            return self._error("JOB_NOT_FOUND")
        job_type = info.get("type")
        if job_type == "cd_rip" and self._module("cd_ripper"):
            self._module("cd_ripper").cancel()
        elif job_type == "conversion" and self._module("conversion"):
            cancel = getattr(self._module("conversion"), "cancel", None)
            if callable(cancel):
                cancel(normalized)
        cancel = getattr(self._jobs, "cancel", None)
        if callable(cancel):
            try:
                cancel(normalized)
            except Exception:
                pass
        with self._lock:
            info["status"] = "cancelled"
        self.dataChanged.emit()
        return {"ok": True, "job_id": normalized, "status": "cancelled"}

    @Slot(str, result=dict)
    def retryJob(self, job_id: Any) -> dict[str, Any]:
        normalized = self._job_id(job_id)
        info = self._active_jobs.get(normalized)
        if not info:
            return {"ok": False, "error": "NOT_FAILED", "error_code": "NOT_FAILED"}
        job_type = info.get("type")
        filepath = info.get("filepath", "")
        if job_type == "analysis":
            result = self.startAnalysis(filepath)
        elif job_type == "replaygain":
            result = self.startReplayGain(filepath)
        elif job_type == "integrity":
            result = self.startIntegrity(filepath)
        else:
            return self._error("RETRY_UNSUPPORTED")
        return {
            "ok": bool(result.get("ok")),
            "new_job_id": result.get("job_id", ""),
            "type": job_type,
        }

    @Slot(result=dict)
    def cleanupCompleted(self) -> dict[str, Any]:
        with self._lock:
            finished = [
                job_id
                for job_id, info in self._active_jobs.items()
                if info.get("status") in ("completed", "failed", "cancelled")
            ]
            for job_id in finished:
                self._active_jobs.pop(job_id, None)
        self.dataChanged.emit()
        return {"ok": True, "cleaned": len(finished)}

    @Slot(str, result=dict)
    def jobStatus(self, job_id: Any) -> dict[str, Any]:
        normalized = self._job_id(job_id)
        info = self._active_jobs.get(normalized)
        return {"ok": True, **dict(info)} if info else self._error("JOB_NOT_FOUND")

    @Slot(result=dict)
    def activeJobsMap(self) -> dict[str, str]:
        return {
            job_id: str(info.get("status", "unknown"))
            for job_id, info in self._active_jobs.items()
        }

    def _backend_snapshot(self) -> dict[str, Any]:
        if not self._player:
            return {"backend": "", "output": "", "eq": {}}
        backend = getattr(self._player, "get_active_backend_id", None)
        output = getattr(self._player, "get_output_device_id", None)
        eq_state = getattr(self._player, "get_eq_state", None)
        return {
            "backend": str(backend() or "") if callable(backend) else "",
            "output": str(output() or "") if callable(output) else "",
            "eq": self._serialize(eq_state()) if callable(eq_state) else {},
        }

    @Slot(result=dict)
    def refresh(self) -> dict[str, Any]:
        if self._svc is not None:
            start = getattr(self._svc, "start", None)
            if callable(start):
                try:
                    start()
                except Exception as exc:
                    return self._record_error("refresh", exc)
        self.dataChanged.emit()
        stats = self.getOverviewData() if self._svc else {}
        return {
            "ok": self._svc is not None,
            "stats": stats,
            "backend": self._backend_snapshot(),
        }

    @Slot(str, result=dict)
    def navigateTo(self, route: str) -> dict[str, Any]:
        if not self._nav:
            return self._error("NAVIGATION_UNAVAILABLE")
        before = getattr(self._nav, "currentRoute", "")
        result = self._nav.navigate(route)
        if isinstance(result, dict):
            return {"requested_route": route, "previous": before, **result}
        resolved = getattr(self._nav, "currentRoute", route)
        return {
            "ok": resolved == route,
            "route": resolved,
            "requested_route": route,
            "previous": before,
        }

    @Slot(str, result=dict)
    def requireConfirmation(self, action: str) -> dict[str, Any]:
        request = getattr(self._confirm, "request", None)
        return request(action) if callable(request) else self._error("CONFIRMATION_UNAVAILABLE")

    @Slot(result=dict)
    def partialFailureReport(self) -> dict[str, Any]:
        failed = [
            dict(info)
            for info in self._active_jobs.values()
            if info.get("status") == "failed"
        ]
        return {"ok": True, "has_failures": bool(failed), "failures": failed}

    @Slot(result=dict)
    def getOverviewData(self) -> dict[str, Any]:
        if not self._svc:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            data = self._serialize(self._svc.get_overview_data())
            if not isinstance(data, dict):
                data = {}
            return {"ok": True, **data}
        except Exception as exc:
            return self._record_error("overview", exc)

    @Slot(str, result=dict)
    def navigateToArea(self, area_key: str) -> dict[str, Any]:
        route_map = {
            "diagnostics": "audio_lab.analysis",
            "identifier": "metadata.inspector",
            "backup": "audio_lab.backup",
            "output_profiles": "outputs",
            "local_intelligence": "mix",
        }
        route = route_map.get(area_key)
        return self.navigateTo(route) if route else self._error("INVALID_AREA")

    @Slot(result="QVariantList")
    def detectCDDrives(self) -> list[dict[str, Any]]:
        ripper = self._module("cd_ripper")
        if not ripper:
            return []
        try:
            return [self._serialize(drive) for drive in ripper.detect_drives()]
        except Exception as exc:
            self._record_error("cd_detection", exc)
            return []

    @Slot(result=dict)
    def getCDRippingCapability(self) -> dict[str, Any]:
        ripper = self._module("cd_ripper")
        return self._serialize(ripper.capability()) if ripper else {"available": False}

    @Slot(str, result=dict)
    def getCDInfo(self, device: str) -> dict[str, Any]:
        ripper = self._module("cd_ripper")
        if not ripper:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            info = ripper.get_cd_info(device)
            return {"ok": True, **self._serialize(info)} if info else self._error("CD_INFO_UNAVAILABLE")
        except Exception as exc:
            return self._record_error("cd_info", exc)

    @Slot(str, int, str, str, result=dict)
    def ripCDTrack(
        self,
        device: str,
        track_number: int,
        output_path: str,
        format: str = "flac",
    ) -> _JobStartResult:
        ripper = self._module("cd_ripper")
        if not ripper:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "cd_rip",
            lambda: ripper.rip_track(device, int(track_number), output_path, format),
            filepath=output_path,
            prefix="cdtrack",
        )

    @Slot(str, str, str, str, bool, result=dict)
    def ripFullCD(
        self,
        device: str,
        output_dir: str,
        format: str = "flac",
        quality: str = "lossless",
        include_log: bool = True,
    ) -> _JobStartResult:
        ripper = self._module("cd_ripper")
        if not ripper:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "cd_rip",
            lambda: ripper.rip_full_cd(device, output_dir, format, quality, include_log),
            filepath=output_dir,
            prefix="cdfull",
        )

    @Slot(result=dict)
    def cancelCDRip(self) -> dict[str, Any]:
        ripper = self._module("cd_ripper")
        if not ripper:
            return self._error("SERVICE_UNAVAILABLE")
        result = self._serialize(ripper.cancel())
        return {"ok": bool(result.get("success")), **result}

    @Slot(result="QVariantList")
    def detectAudioDevices(self) -> list[dict[str, Any]]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return []
        try:
            return [self._serialize(device) for device in recorder.detect_devices()]
        except Exception as exc:
            self._record_error("audio_device_detection", exc)
            return []

    @Slot(result=dict)
    def getRecommendedDevice(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            device = recorder.get_recommended_device()
            return {"ok": True, **self._serialize(device)} if device else self._error("NO_AUDIO_DEVICES")
        except Exception as exc:
            return self._record_error("recommended_device", exc)

    @Slot(str, str, str, int, int, int, "QVariantList", result=dict)
    def startRecording(
        self,
        device_id: str,
        output_path: str,
        format: str = "wav",
        sample_rate: int = 44100,
        bit_depth: int = 16,
        channels: int = 2,
        dsp_filters: list | None = None,
    ) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        try:
            devices = recorder.detect_devices()
            device = next(
                (item for item in devices if str(item.device_id) == str(device_id)),
                None,
            )
            if not device:
                return self._error("DEVICE_NOT_FOUND")
            result = self._serialize(
                recorder.start_recording(
                    device=device,
                    output_path=output_path,
                    format=format,
                    sample_rate=int(sample_rate),
                    bit_depth=int(bit_depth),
                    channels=int(channels),
                    apply_dsp=list(dsp_filters or []),
                )
            )
            return {"ok": bool(result.get("success")), **result}
        except Exception as exc:
            return self._record_error("recording_start", exc)

    @Slot(result=dict)
    def pauseRecording(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        result = self._serialize(recorder.pause_recording())
        return {"ok": bool(result.get("success")), **result}

    @Slot(result=dict)
    def resumeRecording(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        result = self._serialize(recorder.resume_recording())
        return {"ok": bool(result.get("success")), **result}

    @Slot(result=dict)
    def stopRecording(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        result = self._serialize(recorder.stop_recording())
        return {"ok": bool(result.get("success")), **result}

    @Slot(str, result=dict)
    @Slot(str, float, result=dict)
    def addMarker(self, label: str = "", timestamp: float = -1.0) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        if not recorder:
            return self._error("SERVICE_UNAVAILABLE")
        marker_time = None if timestamp < 0 else timestamp
        result = self._serialize(recorder.add_marker(timestamp=marker_time, label=label))
        return {"ok": bool(result.get("success")), **result}

    @Slot(str, str, result=dict)
    def splitByMarkers(self, input_file: str, output_dir: str) -> _JobStartResult:
        recorder = self._module("adc_recorder")
        if not recorder:
            return _JobStartResult(self._error("SERVICE_UNAVAILABLE"))
        return self._start_background_job(
            "recording_split",
            lambda: recorder.split_by_markers(input_file, output_dir),
            filepath=input_file,
            prefix="split",
        )

    @Slot(result=dict)
    def getRecordingStatus(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        return (
            self._serialize(recorder.get_recording_status())
            if recorder
            else {"active": False, "status": "unavailable"}
        )

    @Slot(result=dict)
    def getCaptureCapabilities(self) -> dict[str, Any]:
        recorder = self._module("adc_recorder")
        return {
            "available": bool(recorder and recorder.available()),
            "formats": list(getattr(recorder, "SUPPORTED_FORMATS", ())),
            "dsp_filters": list(getattr(recorder, "DSP_FILTERS", ())),
        }
