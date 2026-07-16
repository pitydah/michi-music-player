"""SmartTaggingBridge — async, selective, safe smart tagging with cancel and progress.

Supports: single, batch, confidence, preview, select, accept/reject,
progress, cancel, backup, apply, verify, rollback, refresh.
"""
from __future__ import annotations

import logging
import os

from PySide6.QtCore import QObject, Signal, Property, Slot

from ui_qml_bridge.metadata_tag_adapter import (
    load_tags, apply_patch, create_backup,
    write_tags_safe, rollback as rollback_tags, verify_changes,
)

logger = logging.getLogger("michi.smart_tagging")


class SmartTaggingBridge(QObject):
    dataChanged = Signal()
    scanCompleted = Signal(int)
    progressChanged = Signal(float)
    batchProgress = Signal(int, int)

    def __init__(self, service=None, worker_manager=None, query_service=None, parent=None):
        super().__init__(parent)
        assert service is not None, "SmartTaggingBridge: service is REQUIRED"
        assert worker_manager is not None, "SmartTaggingBridge: worker_manager is REQUIRED"
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
        self._batch_mode = False
        self._batch_results: list[dict] = []

    def set_service(self, service):
        self._service = service

    @Property(str, notify=dataChanged)
    def status(self):
        return self._status

    @Property("QVariantList", notify=dataChanged)
    def suggestions(self):
        return list(self._suggestions)

    @Property(float, notify=progressChanged)
    def progress(self):
        return self._progress

    @Property("QVariantList", notify=dataChanged)
    def batchResults(self):
        return list(self._batch_results)

    @Slot(int, result=dict)
    def scanTrackById(self, track_id: int):
        if self._status in ("scanning", "applying"):
            return {"ok": False, "error_code": "BUSY", "message": "Ya hay un escaneo en curso"}
        self._progress = 0.0
        self._status = "queued"
        self._batch_mode = False
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
            if hasattr(service, 'suggest_for_track'):
                results = service.suggest_for_track(track)
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

        def _on_error(code, msg):
            if gen != self._scan_counter:
                return
            self._status = "error"
            self.dataChanged.emit()

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(f"st_{track_id}", _task, on_done=_done,
                              on_error=_on_error,
                              pass_context=True, cancellable=True, owner="smart_tagging")
        else:
            _done(_task(None))
        return {"ok": True, "queued": True}

    @Slot("QVariantList", result=dict)
    def scanBatch(self, track_ids: list):
        if self._status in ("scanning", "applying"):
            return {"ok": False, "error_code": "BUSY", "message": "Ya hay un escaneo en curso"}
        if not track_ids:
            return {"ok": False, "error_code": "NO_TRACKS", "message": "Sin pistas"}
        self._progress = 0.0
        self._status = "scanning"
        self._batch_mode = True
        self._batch_results = []
        self._scan_counter += 1
        gen = self._scan_counter
        self.dataChanged.emit()

        qs = self._qs
        service = self._service

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            all_results = []
            total = len(track_ids)
            for idx, tid in enumerate(track_ids):
                ctx.token.raise_if_cancelled()
                ctx.report_progress((idx + 1) / total, f"Escaneando pista {idx+1}/{total}")
                if gen != self._scan_counter:
                    return {"stale": True, "results": all_results}
                track = None
                if qs:
                    try:
                        track = qs.fetch_track_internal(tid)
                    except Exception:
                        track = None
                if not track:
                    all_results.append({"track_id": tid, "error": "TRACK_NOT_FOUND"})
                    continue
                if hasattr(service, 'suggest_for_track'):
                    try:
                        suggestions = service.suggest_for_track(track)
                    except Exception:
                        suggestions = []
                    all_results.append({
                        "track_id": tid,
                        "filepath": track.get("filepath", ""),
                            "suggestions": [
                                {"field": getattr(s, 'field', ''),
                                 "current": getattr(s, 'current', '') or "",
                                 "suggested": getattr(s, 'suggested', '') or "",
                                 "confidence": getattr(s, 'confidence', 0.0) or 0.0,
                                 "source": getattr(s, 'source', '') or "",
                                 "warning": getattr(s, 'warning', '') or ""}
                                for s in (suggestions or [])
                            ],
                        })
            return {"results": all_results}

        def _done(res):
            if gen != self._scan_counter:
                self._status = "stale"
                self.dataChanged.emit()
                return
            self._batch_results = res.get("results", [])
            self._status = "batch_review"
            self._progress = 1.0
            self.progressChanged.emit(self._progress)
            self.dataChanged.emit()

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(
                f"st_batch_{gen}", _task,
                on_done=_done, pass_context=True, cancellable=True, owner="smart_tagging",
            )
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
    def selectHighConfidence(self, min_confidence: float = 0.8):
        self._selected_ids = set(
            s["id"] for s in self._suggestions
            if s.get("id") is not None and (s.get("confidence", 0) or 0) >= min_confidence
        )
        for s in self._suggestions:
            s["selected"] = s.get("id") in self._selected_ids
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
        if self._status not in ("review", "batch_review"):
            return {"ok": False, "error_code": "NOT_REVIEW", "message": "No hay sugerencias para aplicar"}
        if self._batch_mode:
            return self._applyBatchSelected()
        return self._applySingleSelected()

    def _applySingleSelected(self):
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
            ctx.report_progress(0.8, "Verificando...")
            verify = verify_changes(filepath, changes)
            if not verify.get("ok"):
                if backup:
                    rollback_tags(backup, filepath)
                return {"error": "VERIFY_FAILED"}
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

    def _applyBatchSelected(self):
        self._status = "applying"
        self._progress = 0.0
        self.dataChanged.emit()

        batch_results = list(self._batch_results)
        gen = self._scan_counter

        def _task(ctx):
            ctx.token.raise_if_cancelled()
            results = []
            total = len(batch_results)
            for idx, br in enumerate(batch_results):
                ctx.token.raise_if_cancelled()
                ctx.report_progress((idx + 1) / total, f"Aplicando {idx+1}/{total}")
                fp = br.get("filepath", "")
                suggestions = br.get("suggestions", [])
                if not fp or not suggestions:
                    results.append({"track_id": br.get("track_id"), "ok": False, "error": "NO_DATA"})
                    continue
                base = load_tags(fp)
                if base is None:
                    results.append({"track_id": br.get("track_id"), "ok": False, "error": "FILE_NOT_FOUND"})
                    continue
                changes = {}
                for s in suggestions:
                    if s.get("field") and s.get("suggested"):
                        changes[s["field"]] = s["suggested"]
                if not changes:
                    results.append({"track_id": br.get("track_id"), "ok": True, "applied": 0})
                    continue
                tags = apply_patch(base, changes)
                if not tags.dirty:
                    results.append({"track_id": br.get("track_id"), "ok": True, "applied": 0})
                    continue
                backup = create_backup(fp)
                write_result = write_tags_safe(tags, backup)
                if write_result.get("ok"):
                    results.append({"track_id": br.get("track_id"), "ok": True, "applied": len(changes)})
                else:
                    if backup:
                        rollback_tags(backup, fp)
                    results.append({"track_id": br.get("track_id"), "ok": False, "error": write_result.get("error_code")})
            return {"results": results}

        def _done(res):
            if gen != self._scan_counter:
                self._status = "stale"
                return
            self._batch_results = res.get("results", [])
            self._progress = 1.0
            self.progressChanged.emit(self._progress)
            self._status = "completed"
            self.dataChanged.emit()

        if self._wm and hasattr(self._wm, 'run_task'):
            self._wm.run_task(f"st_batch_apply_{gen}", _task, on_done=_done,
                              pass_context=True, cancellable=True, owner="smart_tagging")
        else:
            _done(_task(None))
        return {"ok": True, "queued": True}

    @Slot(result=dict)
    def acceptAll(self):
        return self.selectAll()

    @Slot(result=dict)
    def rejectAll(self):
        return self.selectNone()

    @Slot(result=dict)
    def cancelScan(self):
        self._cancel_requested = True
        self._status = "cancel_requested"
        self._progress = 0.0
        self._suggestions = []
        self._selected_ids.clear()
        self._batch_results = []
        if self._wm:
            self._wm.cancel_task("st_" + str(self._scan_counter))
        self.dataChanged.emit()
        self.progressChanged.emit(0.0)
        return {"ok": True}

    @Slot(str, result=str)
    def detectFormat(self, filepath: str) -> str:
        ext = os.path.splitext(filepath)[1].lower().lstrip(".")
        return ext if ext else ""

    @Slot()
    def refresh(self):
        self.dataChanged.emit()
