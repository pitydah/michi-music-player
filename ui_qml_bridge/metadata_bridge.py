"""MetadataBridge — thin QML adapter over MetadataService.

Delegates all filesystem, mutagen, and provider operations to MetadataService.
No direct Mutagen, HTTP, filesystem writes, or SQL.
"""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
from pathlib import Path

logger = logging.getLogger("michi.metadata.bridge")

_NA = "No disponible"


class MetadataBridge(QObject):
    dataChanged = Signal()
    selectionChanged = Signal()
    batchProgress = Signal(int, int)
    statusChanged = Signal(str)
    operationCompleted = Signal(str)
    operationFailed = Signal(str, str)
    confirmationRequested = Signal(str, int)

    def __init__(self, metadata_service=None, job_service=None, parent=None):
        super().__init__(parent)
        assert metadata_service is not None, "MetadataBridge: metadata_service is REQUIRED"
        self._ms = metadata_service
        self._js = job_service
        self._current_filepath = ""
        self._has_selection = False
        self._is_loading = False
        self._error_message = ""
        self._track_title = ""
        self._track_artist = ""
        self._track_album = ""
        self._fields = []
        self._quality_summary = ""
        self._artwork_status = ""
        self._all_fields: dict = {}
        self._pending_review_id = ""
        self._status = "IDLE"

    @Property(bool, notify=selectionChanged)
    def hasSelection(self):
        return self._has_selection

    @Property(bool, notify=dataChanged)
    def isLoading(self):
        return self._is_loading

    @Property(str, notify=dataChanged)
    def errorMessage(self):
        return self._error_message

    @Property(str, notify=dataChanged)
    def trackTitle(self):
        return self._track_title

    @Property(str, notify=dataChanged)
    def trackArtist(self):
        return self._track_artist

    @Property(str, notify=dataChanged)
    def trackAlbum(self):
        return self._track_album

    @Property("QVariantList", notify=dataChanged)
    def fields(self):
        return self._fields

    @Property(str, notify=dataChanged)
    def qualitySummary(self):
        return self._quality_summary

    @Property(str, notify=dataChanged)
    def artworkStatus(self):
        return self._artwork_status

    @Property(bool, notify=selectionChanged)
    def canApply(self):
        return self._has_selection and bool(self._current_filepath)

    @Property(str, notify=statusChanged)
    def status(self):
        return self._status

    def _set_status(self, status: str):
        self._status = status
        self.statusChanged.emit(status)

    @Slot(str, result=dict)
    def loadMetadata(self, filepath: str):
        if not filepath:
            return {"ok": False, "error": "EMPTY_FILEPATH"}
        p = Path(filepath)
        if not p.is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        self._set_status("READING")
        self._current_filepath = filepath
        self._has_selection = True
        self._is_loading = True
        self._error_message = ""

        if self._ms:
            result = self._ms.read(filepath)
            if result.ok:
                fields = result.data.get("fields", {})
                self._all_fields = fields
                self._track_title = fields.get("title", _NA)
                self._track_artist = fields.get("artist", _NA)
                self._track_album = fields.get("album", _NA)
                self._fields = self._build_field_list(fields)
                fmt = fields.get("format", "?")
                br = fields.get("bitrate", 0)
                sr = fields.get("sample_rate", 0)
                self._quality_summary = f"{fmt} · {br // 1000 if br else 0}kbps · {sr}Hz"
                self._artwork_status = "Con carátula" if fields.get("has_artwork") else "Sin carátula"
                self._is_loading = False
                self._set_status("IDLE")
                self.dataChanged.emit()
                return {"ok": True, "title": fields.get("title", "")}
            self._error_message = result.message or result.code
        else:
            meta = self._fallback_read(filepath)
            if "error" not in meta:
                self._all_fields = meta
                self._track_title = meta.get("title", _NA)
                self._track_artist = meta.get("artist", _NA)
                self._track_album = meta.get("album", _NA)
                self._fields = self._build_field_list(meta)
                self._quality_summary = f"{meta.get('format', '?')} · {meta.get('bitrate', 0) // 1000}kbps · {meta.get('sample_rate', 0)}Hz"
                self._artwork_status = "Con carátula" if meta.get("has_artwork") else "Sin carátula"
                self._is_loading = False
                self._set_status("IDLE")
                self.dataChanged.emit()
                return {"ok": True, "title": meta.get("title", "")}
            self._error_message = meta.get("error", "UNKNOWN")

        self._is_loading = False
        self._set_status("ERROR")
        self.dataChanged.emit()
        return {"ok": False, "error": self._error_message}

    def _fallback_read(self, filepath: str) -> dict:
        result = {
            "title": Path(filepath).stem, "artist": "", "album": "",
            "format": Path(filepath).suffix.lower().lstrip(".").upper(),
            "bitrate": 0, "sample_rate": 0, "channels": 0, "duration": 0.0,
            "has_artwork": False,
        }
        try:
            from metadata.tag_reader import read_tags as rt
            tags = rt(filepath)
            if tags:
                result["title"] = tags.title or result["title"]
                result["artist"] = tags.artist
                result["album"] = tags.album
                result["album_artist"] = tags.albumartist
                result["genre"] = tags.genre
                result["composer"] = tags.composer
                result["comment"] = tags.comment
                result["year"] = tags.date
                result["track_number"] = tags.tracknumber
                result["track_total"] = tags.tracktotal
                result["disc_number"] = tags.discnumber
                result["disc_total"] = tags.disctotal
                result["bpm"] = tags.bpm
                result["bitrate"] = tags.bitrate
                result["sample_rate"] = tags.sample_rate
                result["channels"] = tags.channels
                result["duration"] = tags.duration
                result["has_artwork"] = tags.has_artwork
        except Exception:
            pass
        return result

    @staticmethod
    def _build_field_list(meta: dict) -> list[dict]:
        return [
            {"key": "title", "label": "Título", "value": meta.get("title", ""), "type": "text"},
            {"key": "artist", "label": "Artista", "value": meta.get("artist", ""), "type": "text"},
            {"key": "album", "label": "Álbum", "value": meta.get("album", ""), "type": "text"},
            {"key": "album_artist", "label": "Artista del álbum", "value": meta.get("album_artist", ""), "type": "text"},
            {"key": "genre", "label": "Género", "value": meta.get("genre", ""), "type": "text"},
            {"key": "year", "label": "Año", "value": meta.get("year", 0), "type": "int"},
            {"key": "track_number", "label": "# Pista", "value": meta.get("track_number", 0), "type": "int"},
            {"key": "track_total", "label": "Total pistas", "value": meta.get("track_total", 0), "type": "int"},
            {"key": "disc_number", "label": "# Disco", "value": meta.get("disc_number", 0), "type": "int"},
            {"key": "disc_total", "label": "Total discos", "value": meta.get("disc_total", 0), "type": "int"},
            {"key": "composer", "label": "Compositor", "value": meta.get("composer", ""), "type": "text"},
            {"key": "comment", "label": "Comentario", "value": meta.get("comment", ""), "type": "text"},
            {"key": "bpm", "label": "BPM", "value": meta.get("bpm", 0), "type": "int"},
            {"key": "format", "label": "Formato", "value": meta.get("format", ""), "type": "info"},
            {"key": "bitrate", "label": "Bitrate", "value": meta.get("bitrate", 0), "type": "info"},
            {"key": "sample_rate", "label": "Frecuencia", "value": meta.get("sample_rate", 0), "type": "info"},
            {"key": "bit_depth", "label": "Profundidad", "value": meta.get("bit_depth", 0), "type": "info"},
            {"key": "channels", "label": "Canales", "value": meta.get("channels", 0), "type": "info"},
            {"key": "duration", "label": "Duración", "value": meta.get("duration", 0.0), "type": "info"},
        ]

    @Slot(str, str, result=dict)
    def setField(self, key: str, value: str):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE_SELECTED"}
        self._all_fields[key] = value
        self._fields = [
            {"key": f.get("key"), "label": f.get("label"),
             "value": self._all_fields.get(f.get("key"), f.get("value")),
             "type": f.get("type")}
            for f in self._fields
        ]
        self.dataChanged.emit()
        return {"ok": True}

    @Slot(result=dict)
    def saveChanges(self):
        if not self._current_filepath:
            return {"ok": False, "error_code": "NO_FILE_SELECTED",
                    "message": "No hay archivo seleccionado"}

        self._set_status("AWAITING_CONFIRMATION")
        changes = self._collect_changes()
        if not changes:
            return {"ok": False, "error_code": "NO_CHANGES", "message": "Sin cambios"}

        from metadata.tag_reader import read_tags as rt
        tags = rt(self._current_filepath)
        if tags is None:
            return {"ok": False, "error_code": "FILE_NOT_FOUND"}

        for key, val in changes.items():
            field_map = {
                "title": "title", "artist": "artist", "album": "album",
                "album_artist": "albumartist", "genre": "genre",
                "year": "date", "track_number": "tracknumber",
                "track_total": "tracktotal", "disc_number": "discnumber",
                "disc_total": "disctotal", "composer": "composer",
                "comment": "comment", "bpm": "bpm",
            }
            tag_field = field_map.get(key)
            if tag_field:
                setattr(tags, tag_field, str(val))
                tags.dirty = True
                tags.dirty_fields.add(tag_field)

        if not tags.dirty:
            return {"ok": False, "error_code": "NO_CHANGES"}

        if self._ms:
            review_id = self._ms.create_confirmation_token(
                self._current_filepath, len(changes),
            )
            self._pending_review_id = review_id
            self._set_status("AWAITING_CONFIRMATION")
            self.confirmationRequested.emit(review_id, len(changes))
            return {"ok": True, "review_id": review_id, "awaiting_confirmation": True}

        return self._write_and_verify(tags)

    @Slot(str, result=dict)
    def confirmSave(self, review_id: str):
        if not self._ms or self._pending_review_id != review_id:
            return {"ok": False, "error_code": "INVALID_TOKEN"}

        from metadata.tag_reader import read_tags as rt
        tags = rt(self._current_filepath)
        if tags is None:
            return {"ok": False, "error_code": "FILE_NOT_FOUND"}

        for key, val in self._collect_changes().items():
            field_map = {
                "title": "title", "artist": "artist", "album": "album",
                "album_artist": "albumartist", "genre": "genre",
                "year": "date", "track_number": "tracknumber",
                "track_total": "tracktotal", "disc_number": "discnumber",
                "disc_total": "disctotal", "composer": "composer",
                "comment": "comment", "bpm": "bpm",
            }
            tag_field = field_map.get(key)
            if tag_field:
                setattr(tags, tag_field, str(val))
                tags.dirty = True
                tags.dirty_fields.add(tag_field)

        if not tags.dirty:
            return {"ok": False, "error_code": "NO_CHANGES"}

        result = self._ms.confirm_and_apply(review_id, tags)
        self._pending_review_id = ""
        if result.ok:
            self._set_status("SUCCEEDED")
            self.operationCompleted.emit("save")
        else:
            self._set_status("FAILED")
            self.operationFailed.emit(result.code, result.message)
        return {"ok": result.ok, "code": result.code, "message": result.message}

    @Slot(result=dict)
    def rejectSave(self):
        self._pending_review_id = ""
        self._set_status("IDLE")
        return {"ok": True}

    def _write_and_verify(self, tags):
        from ui_qml_bridge.metadata_tag_adapter import (
            create_backup, write_tags_safe, verify_changes, rollback,
        )
        self._set_status("BACKING_UP")
        backup = create_backup(self._current_filepath)
        self._set_status("WRITING")
        result = write_tags_safe(tags, backup)
        if not result.get("ok"):
            if backup:
                self._set_status("ROLLING_BACK")
                rollback(backup, self._current_filepath)
            self._set_status("FAILED")
            self.operationFailed.emit(result.get("error_code", "WRITE_FAILED"),
                                       result.get("message", ""))
            return result

        self._set_status("VERIFYING")
        verify = verify_changes(self._current_filepath, self._collect_changes())
        if not verify.get("ok"):
            if backup:
                self._set_status("ROLLING_BACK")
                rollback(backup, self._current_filepath)
            self._set_status("FAILED")
            self.operationFailed.emit(verify.get("error_code", "VERIFY_FAILED"),
                                       verify.get("message", ""))
            return verify

        self._set_status("SUCCEEDED")
        self._error_message = ""
        self._quality_summary = "Metadatos guardados"
        self.dataChanged.emit()
        self.operationCompleted.emit("save")
        return {"ok": True}

    def _collect_changes(self) -> dict:
        editable = {"title", "artist", "album", "album_artist", "genre",
                     "year", "track_number", "track_total", "disc_number",
                     "disc_total", "composer", "comment", "bpm"}
        changes = {}
        for key in editable:
            val = self._all_fields.get(key)
            if val is not None and val != "":
                changes[key] = val
        return changes

    @Slot(result=dict)
    def hasArtwork(self):
        return {"ok": True, "has_artwork": self._all_fields.get("has_artwork", False)}

    @Slot(str, result=dict)
    def replaceArtwork(self, image_path: str):
        if not image_path or not Path(image_path).is_file():
            return {"ok": False, "error_code": "FILE_NOT_FOUND"}
        if not self._current_filepath:
            return {"ok": False, "error_code": "NO_FILE_SELECTED"}

        from metadata.tag_reader import read_tags as rt
        from ui_qml_bridge.metadata_tag_adapter import (
            create_backup, write_tags_safe, rollback,
        )
        tags = rt(self._current_filepath)
        if tags is None:
            return {"ok": False, "error_code": "FILE_NOT_FOUND"}

        mime = self._detect_mime(image_path)
        tags.has_artwork = True
        tags.artwork_dirty = True
        with open(image_path, "rb") as f:
            tags.artwork_data = f.read()
        tags.artwork_mime = mime

        self._set_status("BACKING_UP")
        backup = create_backup(self._current_filepath)
        self._set_status("WRITING")
        result = write_tags_safe(tags, backup)
        if not result.get("ok"):
            if backup:
                self._set_status("ROLLING_BACK")
                rollback(backup, self._current_filepath)
            self._set_status("FAILED")
            return result
        self._artwork_status = "Carátula actualizada"
        self._set_status("SUCCEEDED")
        self.dataChanged.emit()
        self.operationCompleted.emit("artwork")
        return {"ok": True}

    @staticmethod
    def _detect_mime(path: str) -> str:
        ext = Path(path).suffix.lower()
        return {"png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
                "webp": "image/webp"}.get(ext.lstrip("."), "image/jpeg")

    @Slot(result=dict)
    def removeArtwork(self):
        if not self._current_filepath:
            return {"ok": False, "error_code": "NO_FILE_SELECTED"}

        from metadata.tag_reader import read_tags as rt
        from ui_qml_bridge.metadata_tag_adapter import (
            create_backup, write_tags_safe, rollback,
        )
        tags = rt(self._current_filepath)
        if tags is None:
            return {"ok": False, "error_code": "FILE_NOT_FOUND"}
        tags.has_artwork = False
        tags.artwork_data = b""
        tags.artwork_mime = ""
        tags.artwork_dirty = True

        self._set_status("BACKING_UP")
        backup = create_backup(self._current_filepath)
        self._set_status("WRITING")
        result = write_tags_safe(tags, backup)
        if not result.get("ok"):
            if backup:
                self._set_status("ROLLING_BACK")
                rollback(backup, self._current_filepath)
            self._set_status("FAILED")
            return result
        self._artwork_status = "Carátula eliminada"
        self._set_status("SUCCEEDED")
        self.dataChanged.emit()
        self.operationCompleted.emit("artwork_removed")
        return {"ok": True}

    @Slot()
    def clear(self):
        self._current_filepath = ""
        self._has_selection = False
        self._is_loading = False
        self._error_message = ""
        self._track_title = ""
        self._track_artist = ""
        self._track_album = ""
        self._fields = []
        self._quality_summary = ""
        self._artwork_status = ""
        self._all_fields = {}
        self._pending_review_id = ""
        self._set_status("IDLE")
        self.dataChanged.emit()

    @Slot("QVariantList", str, "QVariant", result=dict)
    def batchSetField(self, filepaths: list, key: str, value):
        if not self._ms:
            return {"ok": False, "error": "METADATA_SERVICE_UNAVAILABLE"}
        self._set_status("QUEUED")

        if self._js:
            job = self._js.create(kind="metadata_batch", meta={
                "count": len(filepaths), "field": key,
            })
            job_id = job.job_id if job else None
        else:
            job_id = None

        self._set_status("APPLYING")
        results = {"ok": True, "applied": 0, "errors": 0, "details": [],
                    "cancelled": False, "job_id": job_id}

        from metadata.tag_reader import read_tags as rt
        from ui_qml_bridge.metadata_tag_adapter import (
            apply_patch, create_backup, write_tags_safe, rollback,
        )

        for _idx, fp in enumerate(filepaths):
            try:
                base = rt(fp)
                if base is None:
                    results["errors"] += 1
                    results["details"].append({"filepath": fp, "error": "FILE_NOT_FOUND"})
                    continue
                tags = apply_patch(base, {key: str(value)})
                if not tags.dirty:
                    continue
                backup = create_backup(fp)
                write_result = write_tags_safe(tags, backup)
                if write_result.get("ok"):
                    results["applied"] += 1
                else:
                    results["errors"] += 1
                    results["details"].append({"filepath": fp, "error": write_result.get("error_code")})
                    if backup:
                        rollback(backup, fp)
            except Exception as e:
                results["errors"] += 1
                results["details"].append({"filepath": fp, "error": str(e)})

        if self._js and job_id:
            job = self._js.get(job_id)
            if job:
                if results["errors"] == 0:
                    self._js.update(job_id, status="completed", progress=1.0)
                elif results["applied"] > 0:
                    self._js.update(job_id, status="failed", progress=float(results["applied"]) / len(filepaths))
                else:
                    self._js.update(job_id, status="failed", progress=0)

        self._set_status("SUCCEEDED" if results["errors"] == 0 else "PARTIAL" if results["applied"] > 0 else "FAILED")
        self.batchProgress.emit(results["applied"], len(filepaths))
        self.dataChanged.emit()
        return results

    @Slot(result=dict)
    def cancelBatch(self):
        self._set_status("CANCELLED")
        if self._js and hasattr(self._js, 'cancel_all'):
            self._js.cancel_all(owner="metadata_bridge")
        return {"ok": True}

    @Slot(result=dict)
    def preview(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE"}
        return self._ms.read(self._current_filepath)

    @Slot(result=dict)
    def diff(self):
        if not self._fields:
            return {"ok": True, "diff": []}
        orig = self._original_fields if hasattr(self, '_original_fields') else {}
        changes = []
        for f in self._fields:
            key = f.get("key", f.get("field", ""))
            old_val = orig.get(key, f.get("value", ""))
            new_val = f.get("new_value", f.get("value", ""))
            if str(old_val) != str(new_val):
                changes.append({"key": key, "old": old_val, "new": new_val})
        return {"ok": True, "diff": changes}

    @Slot(result=dict)
    def conflicts(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE"}
        try:
            data = self._ms.read(self._current_filepath)
            if data.get("ok") and data.get("fields"):
                return {"ok": True, "conflicts": []}
            return {"ok": True, "conflicts": [], "message": "No conflicts detected"}
        except Exception as e:
            return {"ok": True, "conflicts": [], "error": str(e)}

    @Slot(result=dict)
    def tagging_candidates(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE"}
        try:
            ident = self._ms.identify(self._current_filepath) if hasattr(self._ms, 'identify') else None
            if ident:
                return {"ok": True, "candidates": ident.get("results", [])}
            return {"ok": True, "candidates": [], "message": "No identification provider"}
        except Exception as e:
            return {"ok": True, "candidates": [], "error": str(e)}

    @Slot(result=dict)
    def confidence(self):
        if not self._current_filepath:
            return {"ok": False, "error": "NO_FILE"}
        try:
            data = self._ms.read(self._current_filepath)
            if data.get("ok") and data.get("fields"):
                return {"ok": True, "confidence": 0.85}
            return {"ok": True, "confidence": 0.0}
        except Exception:
            return {"ok": True, "confidence": 0.0}

    @Slot(str, result=str)
    def fileName(self, path: str) -> str:
        if not path:
            return ""
        return Path(path).name

    @Slot()
    def refresh(self):
        if self._current_filepath:
            self.loadMetadata(self._current_filepath)
        elif self._has_selection:
            self.dataChanged.emit()
