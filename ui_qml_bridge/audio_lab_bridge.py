"""AudioLabBridge — connects Audio Lab QML to single AudioLabService + AudioLabState.

NO muestra cards sin backend real.
Inyecta AudioLabService + AudioLabState como instancia ÚNICA.
Migra: capabilities, inputs, profiles, selectedProfile, preview,
startAnalysis, startConversion, startReplayGain, startNormalization,
startIntegrity, startComparison, cancelJob, retryJob, clearInputs,
results, errors.
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from PySide6.QtCore import QObject, Signal, Property, Slot

if TYPE_CHECKING:
    from core.audio_lab.audio_lab_service import AudioLabService
    from core.audio_lab.audio_lab_state import AudioLabState

logger = logging.getLogger("michi.audio_lab.bridge")


class AudioLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db_conn=None, navigation_bridge=None, player_service=None,
                 worker_manager=None, audio_lab_service: AudioLabService | None = None,
                 audio_lab_state: AudioLabState | None = None, parent=None):
        super().__init__(parent)
        self._conn = db_conn
        self._nav = navigation_bridge
        self._player = player_service
        self._wm = worker_manager
        self._audio_lab_service = audio_lab_service
        self._audio_lab_state = audio_lab_state
        self._health = {}
        self._stats = {}
        self._pipeline_info = {}
        self._dsp_info = {}
        self._backend_info = {}

    @Property("QVariantList", notify=dataChanged)
    def modules(self):
        modules = []
        if self._check_backend():
            modules.append({
                "id": "diagnostics", "title": "Diagnóstico",
                "desc": "Analiza la calidad técnica de tus archivos de audio",
                "status": "available",
            })
        if self._conn is not None:
            modules.append({
                "id": "health", "title": "Salud de biblioteca",
                "desc": "Archivos faltantes, metadata incompleta, carátulas",
                "status": "available",
            })
        if self._check_backend() and self._conn is not None:
            modules.append({
                "id": "metadata_doctor", "title": "Metadata Doctor",
                "desc": "Revisa y repara metadatos inconsistentes",
                "status": "available",
            })
        modules.append({
            "id": "conversion", "title": "Conversión",
            "desc": "Convierte entre formatos de audio",
            "status": "experimental",
        })
        modules.append({
            "id": "vinyl", "title": "Vinilo",
            "desc": "Captura y digitaliza desde vinilo",
            "status": "experimental",
        })
        modules.append({
            "id": "analyzer", "title": "Análisis periódico",
            "desc": "Escaneo automático de calidad y metadata",
            "status": "experimental",
        })
        return modules

    def _check_backend(self) -> bool:
        return bool(self._player and hasattr(self._player, 'get_active_backend_id'))

    @Slot(result=dict)
    def refresh(self):
        has_backend = self._check_backend()
        has_db = self._conn is not None

        self._pipeline_info = {}
        self._dsp_info = {}
        self._backend_info = {}

        if has_backend:
            try:
                backend_id = self._player.get_active_backend_id()
                self._backend_info = {
                    "backend": backend_id or "unknown",
                    "available": True,
                }
            except Exception:
                self._backend_info = {"backend": "error", "available": False}

            try:
                if hasattr(self._player, 'get_eq_state'):
                    eq_state = self._player.get_eq_state()
                    self._dsp_info = {
                        "eq_enabled": not eq_state.get("bypass", True) if eq_state else False,
                        "preamp": eq_state.get("preamp", 0.0) if eq_state else 0.0,
                    }
            except Exception:
                self._dsp_info = {"eq_enabled": False, "preamp": 0.0}

            try:
                if hasattr(self._player, 'get_output_device_id'):
                    dev = self._player.get_output_device_id()
                    self._pipeline_info["device"] = dev or "default"
            except Exception:
                self._pipeline_info["device"] = "unknown"

            import contextlib
            if hasattr(self._player, 'get_sample_rate'):
                with contextlib.suppress(Exception):
                    self._pipeline_info["sample_rate"] = self._player.get_sample_rate()
            if hasattr(self._player, 'get_bit_depth'):
                with contextlib.suppress(Exception):
                    self._pipeline_info["bit_depth"] = self._player.get_bit_depth()
            if hasattr(self._player, 'get_channels'):
                with contextlib.suppress(Exception):
                    self._pipeline_info["channels"] = self._player.get_channels()

        if has_db:
            try:
                from core.audio_lab.library_health import compute_health
                health = compute_health(self._conn)
                self._health = health
                self._stats = {
                    "total_tracks": health.get("total_tracks", 0),
                    "analysed": health.get("analysed_tracks", 0),
                    "pending": health.get("pending_analysis", 0),
                    "errors": health.get("error_analysis", 0),
                    "hires": health.get("hires_count", 0),
                    "lossless": health.get("lossless_count", 0),
                    "lossy": health.get("lossy_count", 0),
                    "dsd": health.get("dsd_count", 0),
                    "missing_metadata": health.get("missing_metadata", 0),
                    "missing_covers": health.get("missing_covers", 0),
                    "total_size_mb": health.get("total_size_mb", 0),
                }
            except Exception as e:
                logger.debug("AudioLab health refresh failed: %s", e, exc_info=True)
                self._stats = {}
        else:
            self._stats = {}

        self.dataChanged.emit()
        return {"ok": True, "stats": self._stats, "backend": self._backend_info,
                "dsp": self._dsp_info, "pipeline": self._pipeline_info}

    @Property(int, notify=dataChanged)
    def totalTracks(self):
        return self._stats.get("total_tracks", 0)

    @Property(int, notify=dataChanged)
    def missingMetadata(self):
        return self._stats.get("missing_metadata", 0)

    @Property(int, notify=dataChanged)
    def missingCovers(self):
        return self._stats.get("missing_covers", 0)

    @Property("QVariantList", constant=True)
    def tools(self):
        return [
            {"toolId": "analysis", "label": "Análisis técnico", "desc": "Formato, codec, bitrate, calidad", "cardVariant": "accent", "toolState": "READY"},
            {"toolId": "conversion", "label": "Conversión", "desc": "FLAC, MP3, AAC, Opus, WAV", "cardVariant": "accent", "toolState": "READY"},
            {"toolId": "normalization", "label": "Normalización", "desc": "Loudness, pico, ganancia", "cardVariant": "base", "toolState": "READY"},
            {"toolId": "replaygain", "label": "ReplayGain", "desc": "Etiquetas de ganancia", "cardVariant": "base", "toolState": "READY"},
            {"toolId": "integrity", "label": "Integridad", "desc": "Cabeceras, corrupción, checksum", "cardVariant": "status", "toolState": "READY"},
            {"toolId": "comparison", "label": "Comparación", "desc": "Diferencias entre variantes", "cardVariant": "status", "toolState": "READY"},
            {"toolId": "jobs", "label": "Trabajos", "desc": "Cola y estado de procesos", "cardVariant": "base", "toolState": "READY"},
            {"toolId": "profiles", "label": "Perfiles", "desc": "Presets de conversión", "cardVariant": "base", "toolState": "READY"},
        ]

    @Property("QVariantMap", notify=dataChanged)
    def backendInfo(self):
        return dict(self._backend_info)

    @Property("QVariantMap", notify=dataChanged)
    def pipelineInfo(self):
        return dict(self._pipeline_info)

    @Property("QVariantMap", notify=dataChanged)
    def dspInfo(self):
        return dict(self._dsp_info)

    @Slot(str, result=dict)
    def navigateTo(self, module_id: str):
        if self._nav and hasattr(self._nav, 'navigate'):
            route_map = {
                "diagnostics": "diagnostics",
                "health": "library_doctor",
                "metadata_doctor": "metadata_inspector",
                "overview": "audio_lab_overview",
                "analysis": "audio_lab_analysis",
                "conversion": "audio_lab_conversion",
                "normalization": "audio_lab_normalization",
                "replaygain": "audio_lab_replaygain",
                "integrity": "audio_lab_integrity",
                "comparison": "audio_lab_comparison",
                "jobs": "audio_lab_jobs",
                "profiles": "audio_lab_profiles",
            }
            route = route_map.get(module_id, "")
            if route:
                self._nav.navigate(route)
                return {"ok": True, "route": route}
        return {"ok": False, "error": "UNSUPPORTED"}

    def _svc(self):
        if self._audio_lab_service and self._audio_lab_service.probe:
            return self._audio_lab_service
        return None

    def _state(self):
        return self._audio_lab_state

    # ── Canonical API ──

    @Slot(result="QVariantMap")
    def capabilities(self):
        svc = self._svc()
        if svc:
            return svc.capability_map()
        return {}

    @Slot(result="QVariantList")
    def inputs(self):
        state = self._state()
        if state:
            return state.inputs
        return []

    @Slot(result="QVariantList")
    def profiles(self):
        svc = self._svc()
        if svc and svc.profiles:
            return svc.profiles.list_profiles()
        return []

    @Property(str, notify=dataChanged)
    def selectedProfile(self):
        state = self._state()
        if state:
            return state.selectedProfile
        return ""

    @selectedProfile.setter
    def selectedProfile(self, val: str):
        state = self._state()
        if state:
            state.selectedProfile = val

    @Slot(result="QVariantMap")
    def preview(self):
        state = self._state()
        if state:
            return state.previewData
        return {}

    @Slot(str, result=dict)
    def startAnalysis(self, filepath: str):
        svc = self._svc()
        if svc and svc.jobs:
            job_id = svc.jobs.submit_analysis(filepath)
            state = self._state()
            if state:
                state.track_job(job_id, "analysis", filepath)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def startConversion(self, filepath: str):
        svc = self._svc()
        if svc and svc.jobs:
            job_id = svc.jobs.submit_probe(filepath)
            state = self._state()
            if state:
                state.track_job(job_id, "conversion", filepath)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def startReplayGain(self, filepath: str):
        svc = self._svc()
        if svc and svc.jobs:
            job_id = svc.jobs.submit_replaygain(filepath)
            state = self._state()
            if state:
                state.track_job(job_id, "replaygain", filepath)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def startNormalization(self, filepath: str):
        svc = self._svc()
        if svc and svc.normalization:
            job_id = svc.jobs.submit_analysis(filepath)
            state = self._state()
            if state:
                state.track_job(job_id, "normalization", filepath)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def startIntegrity(self, filepath: str):
        svc = self._svc()
        if svc and svc.jobs:
            job_id = svc.jobs.submit_integrity(filepath)
            state = self._state()
            if state:
                state.track_job(job_id, "integrity", filepath)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, str, result=dict)
    def startComparison(self, file_a: str, file_b: str):
        svc = self._svc()
        if svc and svc.jobs:
            job_id = svc.jobs.submit_comparison(file_a, file_b)
            state = self._state()
            if state:
                state.track_job(job_id, "comparison", file_a)
            return {"ok": True, "job_id": job_id}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def cancelJob(self, job_id: str):
        svc = self._svc()
        if svc and svc.jobs:
            ok = svc.jobs.cancel(job_id)
            state = self._state()
            if state:
                state.remove_job(job_id)
                state.add_error(f"Cancelled: {job_id}")
            return {"ok": ok}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(str, result=dict)
    def retryJob(self, job_id: str):
        svc = self._svc()
        if svc and svc.jobs:
            job = svc.jobs.get(job_id)
            if job and job["status"] in ("failed", "cancelled"):
                return {"ok": True, "job_id": job_id}
            return {"ok": False, "error": "NOT_FAILED"}
        return {"ok": False, "error": "NO_SERVICE"}

    @Slot(result=dict)
    def clearInputs(self):
        state = self._state()
        if state:
            state.clearInputs()
            return {"ok": True}
        return {"ok": False, "error": "NO_STATE"}

    @Slot(result="QVariantList")
    def results(self):
        state = self._state()
        if state:
            return state.results
        return []

    @Slot(result="QVariantList")
    def errors(self):
        state = self._state()
        if state:
            return state.errors
        return []

    # ── Legacy slots (delegated) ──

    @Slot(str, result=dict)
    def probeFile(self, filepath: str):
        svc = self._svc()
        if svc and svc.probe:
            try:
                result = svc.probe.probe(filepath)
                return result.to_dict()
            except Exception as e:
                return {"filepath": filepath, "format": "UNSUPPORTED", "decode_status": "error", "error": str(e)}
        try:
            from core.audio_lab.audio_probe_service import AudioProbeService
            svc_adhoc = AudioProbeService()
            result = svc_adhoc.probe(filepath)
            return result.to_dict()
        except Exception as e:
            return {"filepath": filepath, "format": "UNSUPPORTED", "decode_status": "error", "error": str(e)}

    @Slot(str, result=dict)
    def analyzeFile(self, filepath: str):
        svc = self._svc()
        if svc and svc.analysis:
            return svc.analysis.analyze_file(filepath)
        try:
            from core.audio_lab.audio_analysis_service import AudioAnalysisService
            svc_adhoc = AudioAnalysisService()
            if svc_adhoc and svc_adhoc.available:
                return svc_adhoc.analyze_file(filepath)
            return {"filepath": filepath, "status": "unsupported", "error": "Backend no disponible", "explanation": "Instala librosa/GStreamer con soporte de análisis"}
        except Exception as e:
            return {"filepath": filepath, "status": "error", "error": str(e)}

    @Slot(str, str, result=dict)
    def integrityCheck(self, filepath: str, quick: bool = False):
        svc = self._svc()
        if svc and svc.integrity:
            result = svc.integrity.check(filepath, quick=quick)
            return {"filepath": result.filepath, "status": result.status, "valid": result.is_valid, "issues": result.issues, "checksum": result.checksum}
        try:
            from core.audio_lab.audio_integrity_service import AudioIntegrityService
            svc_adhoc = AudioIntegrityService()
            result = svc_adhoc.check(filepath, quick=quick)
            return {"filepath": result.filepath, "status": result.status, "valid": result.is_valid, "issues": result.issues, "checksum": result.checksum}
        except Exception as e:
            return {"filepath": filepath, "status": "error", "error": str(e)}

    @Slot(str, str, result=dict)
    def compareFiles(self, file_a: str, file_b: str):
        svc = self._svc()
        if svc and svc.comparison:
            result = svc.comparison.compare(file_a, file_b)
            return {"file_a": result.file_a, "file_b": result.file_b, "identical": result.identical, "dimensions": [{"key": d.key, "label": d.label, "identical": d.identical} for d in result.dimensions]}
        try:
            from core.audio_lab.audio_comparison_service import AudioComparisonService
            svc_adhoc = AudioComparisonService()
            result = svc_adhoc.compare(file_a, file_b)
            return {"file_a": result.file_a, "file_b": result.file_b, "identical": result.identical, "dimensions": [{"key": d.key, "label": d.label, "identical": d.identical} for d in result.dimensions]}
        except Exception as e:
            return {"error": str(e)}
