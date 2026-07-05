"""AudioLabBridge — connects Audio Lab QML to real diagnostics and health services."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.audio_lab.bridge")


class AudioLabBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db_conn=None, navigation_bridge=None, parent=None):
        super().__init__(parent)
        self._conn = db_conn
        self._nav = navigation_bridge
        self._health = {}
        self._stats = {}

    @Property("QVariantList", notify=dataChanged)
    def modules(self):
        return [
            {"id": "diagnostics", "title": "Diagnóstico",
             "desc": "Analiza la calidad técnica de tus archivos de audio",
             "status": "available"},
            {"id": "health", "title": "Salud de biblioteca",
             "desc": "Archivos faltantes, metadata incompleta, carátulas",
             "status": "available"},
            {"id": "metadata_doctor", "title": "Metadata Doctor",
             "desc": "Revisa y repara metadatos inconsistentes",
             "status": "available"},
            {"id": "conversion", "title": "Conversión",
             "desc": "Convierte entre formatos de audio",
             "status": "experimental"},
            {"id": "vinyl", "title": "Vinilo",
             "desc": "Captura y digitaliza desde vinilo",
             "status": "experimental"},
            {"id": "analyzer", "title": "Análisis periódico",
             "desc": "Escaneo automático de calidad y metadata",
             "status": "experimental"},
        ]

    @Slot(result=dict)
    def refresh(self):
        if not self._conn:
            self.dataChanged.emit()
            return {"ok": True, "stats": {}}
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
            self.dataChanged.emit()
            return {"ok": True, "stats": self._stats}
        except Exception as e:
            logger.debug("AudioLab health refresh failed", exc_info=True)
            self.dataChanged.emit()
            return {"ok": False, "error": str(e)}

    @Property(int, notify=dataChanged)
    def totalTracks(self):
        return self._stats.get("total_tracks", 0)

    @Property(int, notify=dataChanged)
    def missingMetadata(self):
        return self._stats.get("missing_metadata", 0)

    @Property(int, notify=dataChanged)
    def missingCovers(self):
        return self._stats.get("missing_covers", 0)

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
