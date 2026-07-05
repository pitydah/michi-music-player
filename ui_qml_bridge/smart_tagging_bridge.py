"""SmartTaggingBridge — connects QML Smart Tagging page to real SmartTaggingService."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging

logger = logging.getLogger("michi.smart_tagging")


class SmartTaggingBridge(QObject):
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._service = None
        self._suggestions = []
        self._scan_results = []
        self._current_filepath = ""
        self._status = "idle"

    def set_service(self, service):
        self._service = service

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def scanResults(self):
        return self._scan_results

    @Property("QVariantList", notify=dataChanged)
    def suggestions(self):
        return self._suggestions

    @Slot(str)
    def scanTrack(self, filepath: str):
        self._current_filepath = filepath
        self._status = "scanning"
        self.dataChanged.emit()
        if self._service and hasattr(self._service, 'suggest_for_track'):
            try:
                from library.media_item import TrackMetadata
                meta = TrackMetadata(filepath=filepath)
                results = self._service.suggest_for_track(meta)
                self._suggestions = [
                    {"field": s.field, "current": s.current or "", "suggested": s.suggested or "",
                     "confidence": s.confidence or 0.0}
                    for s in (results or [])
                ]
                self._scan_results = [{"filepath": filepath, "status": "ok", "suggestions": len(self._suggestions)}]
                self._status = "done"
            except Exception:
                logger.debug("Smart tagging scan failed", exc_info=True)
                self._status = "error"
        else:
            self._status = "unavailable"
        self.dataChanged.emit()

    @Slot(result=dict)
    def applySuggestions(self):
        if not self._suggestions:
            return {"ok": False, "error": "NO_SUGGESTIONS"}
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE"}
        try:
            from metadata.tag_writer import write_tags
            from metadata.tag_model import TrackTags
            tags = TrackTags()
            for s in self._suggestions:
                field = s.get("field", "")
                suggested = s.get("suggested", "")
                if field and suggested:
                    setattr(tags, field, suggested)
            tags.dirty = True
            ok = write_tags(tags)
            if ok:
                self._status = "applied"
                self.dataChanged.emit()
                return {"ok": True, "applied": len(self._suggestions)}
            return {"ok": False, "error": "WRITE_FAILED"}
        except Exception as e:
            logger.debug("applySuggestions failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
