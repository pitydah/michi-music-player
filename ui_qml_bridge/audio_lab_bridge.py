"""AudioLabBridge — connects Audio Lab QML to real diagnostics and health services.

NO muestra cards sin backend real.
Migra: pipeline activo, input/output format, sample rate, bit depth, channels,
resampling, backend, bit-perfect, DSP, device, cache, metadata health, library health.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.audio_lab.bridge")


class AudioLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db_conn=None, navigation_bridge=None, player_service=None,
                 worker_manager=None, parent=None):
        super().__init__(parent)
        self._conn = db_conn
        self._nav = navigation_bridge
        self._player = player_service
        self._wm = worker_manager
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
            }
            route = route_map.get(module_id, "")
            if route:
                self._nav.navigate(route)
                return {"ok": True, "route": route}
        return {"ok": False, "error": "UNSUPPORTED"}
