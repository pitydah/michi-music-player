"""SmartTaggingBridge — async, selective, safe smart tagging."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

from ui_qml_bridge.metadata_tag_adapter import (
    load_tags, apply_patch, create_backup,
    write_tags_safe, rollback as rollback_tags,
)

logger = logging.getLogger("michi.smart_tagging")


class SmartTaggingBridge(QObject):
    dataChanged = Signal()
    scanCompleted = Signal(int)  # suggestion_count

    def __init__(self, service=None, worker_manager=None, query_service=None, parent=None):
        super().__init__(parent)
        self._service = service
        self._wm = worker_manager
        self._qs = query_service
        self._suggestions: list[dict] = []
        self._current_filepath = ""
        self._status = "idle"
        self._selected_ids: set[int] = set()
        self._scan_counter = 0

    def set_service(self, service):
        self._service = service

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def suggestions(self):
        return self._suggestions

    @Slot(int, result=dict)
    def scanTrackById(self, track_id: int):
        self._status = "queued"
        self.dataChanged.emit()
        if not self._service:
            self._status = "unavailable"
            self.dataChanged.emit()
            return {"ok": False, "error_code": "UNSUPPORTED", "message": "Servicio no disponible"}
        self._status = "scanning"
        self._scan_counter += 1
        self.dataChanged.emit()
        try:
            track = None
            if self._qs:
                try:
                    track = self._qs.fetch_track_internal(track_id)
                except Exception:
                    track = None
            if not track:
                self._status = "error"
                self.dataChanged.emit()
                return {"ok": False, "error_code": "TRACK_NOT_FOUND", "message": "Track no encontrado"}
            self._current_filepath = track.get("filepath", "")
            from library.media_item import TrackMetadata
            meta = TrackMetadata(filepath=track["filepath"], title=track.get("title", ""),
                                 artist=track.get("artist", ""), album=track.get("album", ""))
            if hasattr(self._service, 'suggest_for_track'):
                results = self._service.suggest_for_track(meta)
                self._suggestions = [
                    {"id": i, "field": getattr(s, 'field', ''), "current": getattr(s, 'current', '') or "",
                     "suggested": getattr(s, 'suggested', '') or "",
                     "confidence": getattr(s, 'confidence', 0.0) or 0.0,
                     "source": getattr(s, 'source', '') or "", "selected": False}
                    for i, s in enumerate(results or [])
                ]
                self._selected_ids.clear()
                self._status = "review"
                self.dataChanged.emit()
                return {"ok": True, "count": len(self._suggestions)}
        except Exception as scan_e:
            logger.debug("scanTrackById failed: %s", scan_e)
            self._status = "error"
            self.dataChanged.emit()
            return {"ok": False, "error_code": "INTERNAL_ERROR", "message": str(scan_e)}
        self._status = "error"
        self.dataChanged.emit()
        return {"ok": False, "error_code": "INTERNAL_ERROR", "message": "Scan failed"}

    @Slot(int, bool, result=dict)
    def setSuggestionSelected(self, suggestion_id: int, selected: bool):
        if selected:
            self._selected_ids.add(suggestion_id)
        else:
            self._selected_ids.discard(suggestion_id)
        for s in self._suggestions:
            if s.get("id") == suggestion_id:
                s["selected"] = selected
                break
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def selectAll(self):
        self._selected_ids = set(s["id"] for s in self._suggestions if s.get("id") is not None)
        for s in self._suggestions:
            s["selected"] = True
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def selectNone(self):
        self._selected_ids.clear()
        for s in self._suggestions:
            s["selected"] = False
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def applySelected(self):
        if not self._suggestions or not self._selected_ids:
            return {"ok": False, "error_code": "NO_SUGGESTIONS", "message": "Sin sugerencias seleccionadas"}
        if not self._current_filepath:
            return {"ok": False, "error_code": "NO_FILE", "message": "Archivo no encontrado"}
        base = load_tags(self._current_filepath)
        if base is None:
            return {"ok": False, "error_code": "FILE_NOT_FOUND", "message": "Archivo no encontrado"}
        changes = {}
        for s in self._suggestions:
            if s.get("id") in self._selected_ids and s.get("field") and s.get("suggested"):
                changes[s["field"]] = s["suggested"]
        tags = apply_patch(base, changes)
        if not tags.dirty:
            return {"ok": False, "error_code": "NO_CHANGES", "message": "Sin cambios"}
        backup = create_backup(self._current_filepath)
        result = write_tags_safe(tags, backup)
        if not result.get("ok"):
            if backup:
                rollback_tags(backup, self._current_filepath)
            return result
        self._status = "applied"
        self.dataChanged.emit()
        return {"ok": True, "applied": len(changes)}

    @Slot(result=dict)
    def cancelScan(self):
        self._status = "idle"
        self._suggestions = []
        self._selected_ids.clear()
        self.dataChanged.emit()
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
