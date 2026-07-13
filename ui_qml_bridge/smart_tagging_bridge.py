"""SmartTaggingBridge — async, selective, safe smart tagging with cancel and progress."""
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
    scanCompleted = Signal(int)
    progressChanged = Signal(float)

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
        self._progress = 0.0
        self._cancel_requested = False

    def set_service(self, service):
        self._service = service

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def suggestions(self):
        return self._suggestions

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

    @Slot(int, result=dict)
    def scanTrackById(self, track_id: int):
        if self._status in ("scanning", "applying"):
            return {"ok": False, "error_code": "BUSY", "message": "Ya hay un escaneo en curso"}
        self._progress = 0.0
        self._status = "queued"
        self.dataChanged.emit()
        if not self._service:
            self._status = "unavailable"
            self.dataChanged.emit()
            return {"ok": False, "error_code": "UNSUPPORTED", "message": "Servicio no disponible"}
        self._status = "scanning"
        self._scan_counter += 1
        gen = self._scan_counter
        self._progress = 0.1
        self.progressChanged.emit(self._progress)
        self.dataChanged.emit()

        qs = self._qs
        service = self._service

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            track = None
            if qs:
                try:
                    track = qs.fetch_track_internal(track_id)
                except Exception:
                    track = None
            if gen != self._scan_counter:
                return {"stale": True}
            if not track:
                return {"error": "TRACK_NOT_FOUND"}
            ctx.token.raise_if_cancelled()
            from library.media_item import TrackMetadata
            meta = TrackMetadata(filepath=track["filepath"],
                                 title=track.get("title", ""),
                                 artist=track.get("artist", ""),
                                 album=track.get("album", ""))
            if hasattr(service, 'suggest_for_track'):
                results = service.suggest_for_track(meta)
                ctx.token.raise_if_cancelled()
                return {"results": results or [], "filepath": track.get("filepath", "")}
            return {"error": "NO_SUGGEST_SERVICE"}

        def _done(res):
            if gen != self._scan_counter:
                self._status = "stale"
                self.dataChanged.emit()
                return
            if res.get("error"):
                self._status = "error"
                self.dataChanged.emit()
                return
            self._current_filepath = res.get("filepath", "")
            results = res.get("results", [])
            self._suggestions = [
                {"id": i, "field": getattr(s, 'field', ''),
                 "current": getattr(s, 'current', '') or "",
                 "suggested": getattr(s, 'suggested', '') or "",
                 "confidence": getattr(s, 'confidence', 0.0) or 0.0,
                 "source": getattr(s, 'source', '') or "", "selected": False,
                 "warning": getattr(s, 'warning', '') or ""}
                for i, s in enumerate(results)
            ]
            self._selected_ids.clear()
            self._status = "review"
            self._progress = 1.0
            self.progressChanged.emit(self._progress)
            self.dataChanged.emit()
            self.scanCompleted.emit(len(self._suggestions))

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(f"st_{track_id}", _task, on_done=_done,
                              pass_context=True, cancellable=True, owner="smart_tagging")
        else:
            _done(_task(None))
        return {"ok": True, "queued": True}

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
        if self._status != "review":
            return {"ok": False, "error_code": "NOT_REVIEW", "message": "No hay sugerencias para aplicar"}
        if not self._suggestions or not self._selected_ids:
            return {"ok": False, "error_code": "NO_SUGGESTIONS", "message": "Sin sugerencias seleccionadas"}
        if not self._current_filepath:
            return {"ok": False, "error_code": "NO_FILE", "message": "Archivo no encontrado"}
        self._status = "applying"
        self._progress = 0.0
        self.dataChanged.emit()

        filepath = self._current_filepath
        suggestions = list(self._suggestions)
        selected_ids = set(self._selected_ids)
        gen = self._scan_counter

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            base = load_tags(filepath)
            if base is None:
                return {"error": "FILE_NOT_FOUND"}
            changes = {}
            for s in suggestions:
                if s.get("id") in selected_ids and s.get("field") and s.get("suggested"):
                    changes[s["field"]] = s["suggested"]
            tags = apply_patch(base, changes)
            if not tags.dirty:
                return {"error": "NO_CHANGES"}
            ctx.report_progress(0.3, "Backup...")
            backup = create_backup(filepath)
            ctx.report_progress(0.5, "Escribiendo...")
            result = write_tags_safe(tags, backup)
            if not result.get("ok"):
                if backup:
                    rollback_tags(backup, filepath)
                return {"error": result.get("error_code", "WRITE_FAILED")}
            ctx.report_progress(1.0, "Completado")
            return {"ok": True, "applied": len(changes)}

        def _done(res):
            if gen != self._scan_counter:
                self._status = "stale"
                self.dataChanged.emit()
                return
            if res.get("error"):
                self._status = "error"
                self.dataChanged.emit()
                return
            self._progress = 1.0
            self.progressChanged.emit(self._progress)
            self._status = "completed"
            self.dataChanged.emit()

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(f"st_apply_{id(self)}", _task, on_done=_done,
                              pass_context=True, cancellable=True, owner="smart_tagging")
        else:
            _done(_task(None))
        return {"ok": True, "queued": True}

    @Slot(result=dict)
    def cancelScan(self):
        self._cancel_requested = True
        self._status = "cancel_requested"
        self._progress = 0.0
        self._suggestions = []
        self._selected_ids.clear()
        self.dataChanged.emit()
        self.progressChanged.emit()
        return {"ok": True}

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
