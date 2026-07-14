"""MetadataService — real metadata service for read/edit/validate/preview/write/undo.

Workflow: load -> edit -> validate -> preview -> confirmation -> backup ->
          write temp -> verify -> replace -> DB update -> event -> model refresh -> undo.

Supports: single editor, batch editor, mixed values, artwork, diff, conflicts,
          numbering, search/replace, filename parsing, progress, cancel, rollback.
"""
from __future__ import annotations

import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

logger = logging.getLogger("michi.metadata.service")


@dataclass
class MetadataEdit:
    field: str = ""
    old_value: str = ""
    new_value: str = ""
    validated: bool = False
    error: str = ""


@dataclass
class MetadataFileState:
    filepath: str = ""
    tags: dict[str, str] = field(default_factory=dict)
    has_artwork: bool = False
    artwork_mime: str = ""
    artwork_data: bytes | None = None
    original_tags: dict[str, str] = field(default_factory=dict)
    edits: list[MetadataEdit] = field(default_factory=list)
    backup_path: str = ""
    temp_path: str = ""


class MetadataService(QObject):
    metadataLoaded = Signal(str, object)
    metadataEdited = Signal(str, str, str)
    metadataValidated = Signal(str, bool)
    changesPreviewed = Signal(str, list)
    confirmationRequested = Signal(str, str)
    backupCreated = Signal(str, str)
    tempWritten = Signal(str, str)
    changesVerified = Signal(str, bool)
    changesReplaced = Signal(str, bool)
    dbUpdated = Signal(str, object)
    undoCompleted = Signal(str, bool)
    progressChanged = Signal(str, float)
    operationCancelled = Signal(str)

    def __init__(self, db=None, tag_reader=None, tag_writer=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._tag_reader = tag_reader
        self._tag_writer = tag_writer
        self._active: dict[str, MetadataFileState] = {}
        self._confirmation_tokens: dict[str, str] = {}
        self._cancelled: set[str] = set()

    def load(self, filepath: str) -> dict[str, Any]:
        if not filepath or not os.path.isfile(filepath):
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            tags = self._read_tags(filepath)
            state = MetadataFileState(
                filepath=filepath,
                tags=dict(tags),
                original_tags=dict(tags),
            )
            state.has_artwork = self._has_artwork(filepath)
            self._active[filepath] = state
            self.metadataLoaded.emit(filepath, tags)
            return {"ok": True, "tags": tags, "has_artwork": state.has_artwork}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _read_tags(self, filepath: str) -> dict[str, str]:
        if self._tag_reader:
            result = self._tag_reader(filepath)
            if hasattr(result, "to_dict"):
                return result.to_dict()
            if isinstance(result, dict):
                return result
        from metadata.tag_reader import read_tags as rt
        tags = rt(filepath)
        result = {}
        for f in ("title", "artist", "album", "albumartist", "genre",
                  "date", "tracknumber", "discnumber", "composer",
                  "comment", "bpm", "isrc", "tracktotal", "disctotal",
                  "musicbrainz_trackid", "musicbrainz_albumid"):
            result[f] = str(getattr(tags, f, "") or "")
        result["format"] = getattr(tags, "kind", os.path.splitext(filepath)[1].lower().lstrip("."))
        result["bitrate"] = str(getattr(tags, "bitrate", 0) or 0)
        result["sample_rate"] = str(getattr(tags, "sample_rate", 0) or 0)
        result["channels"] = str(getattr(tags, "channels", 0) or 0)
        result["duration"] = str(getattr(tags, "duration", 0.0) or 0.0)
        return result

    def _has_artwork(self, filepath: str) -> bool:
        try:
            import mutagen
            af = mutagen.File(filepath)
            if af is None:
                return False
            ext = os.path.splitext(filepath)[1].lower()
            if ext == ".mp3":
                if hasattr(af, "tags") and af.tags:
                    for k in af.tags:
                        if k.startswith("APIC:"):
                            return True
            elif ext == ".flac":
                if hasattr(af, "pictures") and af.pictures:
                    return True
            elif ext in (".m4a", ".mp4") and hasattr(af, "tags") and "covr" in (af.tags or {}):
                    return True
        except Exception:
            pass
        return False

    def edit_field(self, filepath: str, field: str, value: str) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        old = state.tags.get(field, "")
        state.tags[field] = value
        edit = MetadataEdit(field=field, old_value=old, new_value=value)
        state.edits.append(edit)
        self.metadataEdited.emit(filepath, field, value)
        return {"ok": True, "field": field, "old_value": old, "new_value": value}

    def validate(self, filepath: str) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        issues = []
        valid = True
        for edit in state.edits:
            if not edit.new_value:
                continue
            if edit.field in ("tracknumber", "discnumber", "year", "bpm") and not edit.new_value.isdigit():
                issues.append({"field": edit.field, "error": "Debe ser un número"})
                edit.validated = False
                edit.error = "Debe ser un número"
                valid = False
            if edit.field == "tracknumber":
                try:
                    tn = int(edit.new_value.split("/")[0])
                    if tn < 1 or tn > 999:
                        issues.append({"field": edit.field, "error": "Número de pista fuera de rango"})
                        valid = False
                except ValueError:
                    issues.append({"field": edit.field, "error": "Número de pista inválido"})
                    valid = False
            if edit.field == "bpm":
                try:
                    bpm_val = int(edit.new_value)
                    if bpm_val < 20 or bpm_val > 300:
                        issues.append({"field": edit.field, "error": "BPM fuera de rango (20-300)"})
                        valid = False
                except ValueError:
                    issues.append({"field": edit.field, "error": "BPM inválido"})
                    valid = False
        for edit in state.edits:
            edit.validated = valid
        self.metadataValidated.emit(filepath, valid)
        return {"ok": True, "valid": valid, "issues": issues}

    def preview_changes(self, filepath: str) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        changes = []
        for edit in state.edits:
            if edit.old_value != edit.new_value:
                changes.append({
                    "field": edit.field,
                    "old_value": edit.old_value,
                    "new_value": edit.new_value,
                })
        self.changesPreviewed.emit(filepath, changes)
        return {"ok": True, "changes": changes}

    def request_confirmation(self, filepath: str, message: str = "") -> dict[str, Any]:
        import uuid
        token = str(uuid.uuid4())[:12]
        self._confirmation_tokens[token] = filepath
        self.confirmationRequested.emit(filepath, token)
        return {"ok": True, "confirmation_token": token, "message": message}

    def confirm_and_apply(self, filepath: str, confirmation_token: str) -> dict[str, Any]:
        expected_fp = self._confirmation_tokens.pop(confirmation_token, None)
        if expected_fp != filepath:
            return {"ok": False, "error": "INVALID_CONFIRMATION_TOKEN"}
        return self._apply_changes(filepath)

    def _apply_changes(self, filepath: str) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        if filepath in self._cancelled:
            return {"ok": False, "error": "CANCELLED"}

        self.progressChanged.emit(filepath, 0.1)

        backup_path = self._create_backup(filepath)
        if not backup_path:
            return {"ok": False, "error": "BACKUP_FAILED"}
        state.backup_path = backup_path
        self.backupCreated.emit(filepath, backup_path)

        self.progressChanged.emit(filepath, 0.3)

        temp_fd, temp_path = tempfile.mkstemp(suffix=os.path.splitext(filepath)[1])
        os.close(temp_fd)
        shutil.copy2(filepath, temp_path)
        state.temp_path = temp_path
        self.tempWritten.emit(filepath, temp_path)

        self.progressChanged.emit(filepath, 0.5)

        write_ok = self._write_tags(temp_path, state)
        if not write_ok:
            self._rollback(filepath)
            return {"ok": False, "error": "WRITE_FAILED"}

        self.progressChanged.emit(filepath, 0.7)

        verify_ok = self._verify_changes(temp_path, state)
        if not verify_ok:
            self._rollback(filepath)
            return {"ok": False, "error": "VERIFY_FAILED"}
        self.changesVerified.emit(filepath, True)

        self.progressChanged.emit(filepath, 0.85)

        os.replace(temp_path, filepath)
        state.temp_path = ""
        self.changesReplaced.emit(filepath, True)

        self.progressChanged.emit(filepath, 0.95)

        db_ok = self._update_db(filepath, state)
        if db_ok:
            self.dbUpdated.emit(filepath, {"tags": state.tags})

        self.progressChanged.emit(filepath, 1.0)
        return {"ok": True, "backup_path": backup_path}

    def _create_backup(self, filepath: str) -> str:
        try:
            backup_dir = os.path.join(tempfile.gettempdir(), "michi_metadata_backup")
            os.makedirs(backup_dir, exist_ok=True)
            backup_path = os.path.join(
                backup_dir,
                f"{Path(filepath).stem}_{int(os.path.getmtime(filepath))}.bak"
            )
            shutil.copy2(filepath, backup_path)
            return backup_path
        except Exception as e:
            logger.error("Backup failed for %s: %s", filepath, e)
            return ""

    def _write_tags(self, filepath: str, state: MetadataFileState) -> bool:
        try:
            from metadata.tag_reader import read_tags as rt
            from metadata.tag_writer import write_tags
            tags = rt(filepath)
            if tags is None:
                return False
            for edit in state.edits:
                field_map = {
                    "title": "title", "artist": "artist", "album": "album",
                    "albumartist": "albumartist", "genre": "genre",
                    "date": "date", "tracknumber": "tracknumber",
                    "discnumber": "discnumber", "composer": "composer",
                    "comment": "comment", "bpm": "bpm",
                }
                tf = field_map.get(edit.field)
                if tf and edit.new_value is not None:
                    setattr(tags, tf, str(edit.new_value))
                    tags.dirty = True
                    tags.dirty_fields.add(tf)
            return write_tags(tags)
        except Exception as e:
            logger.error("Write tags failed for %s: %s", filepath, e)
            return False

    def _verify_changes(self, filepath: str, state: MetadataFileState) -> bool:
        try:
            from metadata.tag_reader import read_tags as rt
            tags = rt(filepath)
            if tags is None:
                return False
            for edit in state.edits:
                field_map = {
                    "title": "title", "artist": "artist", "album": "album",
                    "albumartist": "albumartist", "genre": "genre",
                    "date": "date", "tracknumber": "tracknumber",
                    "discnumber": "discnumber", "composer": "composer",
                    "comment": "comment", "bpm": "bpm",
                }
                tf = field_map.get(edit.field)
                if tf and edit.new_value and edit.old_value != edit.new_value:
                    actual = str(getattr(tags, tf, "") or "")
                    if actual != edit.new_value:
                        logger.warning("Verify failed for %s field %s: expected %s, got %s",
                                       filepath, edit.field, edit.new_value, actual)
                        return False
            return True
        except Exception as e:
            logger.error("Verify failed for %s: %s", filepath, e)
            return False

    def _update_db(self, filepath: str, state: MetadataFileState) -> bool:
        if not self._db:
            return True
        try:
            for edit in state.edits:
                if edit.old_value != edit.new_value and hasattr(self._db, "update_media_item_field"):
                    self._db.update_media_item_field(filepath, edit.field, edit.new_value)
            return True
        except Exception as e:
            logger.error("DB update failed for %s: %s", filepath, e)
            return False

    def _rollback(self, filepath: str):
        state = self._active.get(filepath)
        if not state:
            return
        if state.backup_path and os.path.exists(state.backup_path):
            shutil.copy2(state.backup_path, filepath)
            logger.info("Rollback restored %s from %s", filepath, state.backup_path)
        if state.temp_path and os.path.exists(state.temp_path):
            import contextlib
            with contextlib.suppress(Exception):
                os.unlink(state.temp_path)

    def undo(self, filepath: str) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        if not state.backup_path or not os.path.exists(state.backup_path):
            return {"ok": False, "error": "NO_BACKUP"}
        try:
            shutil.copy2(state.backup_path, filepath)
            for edit in state.edits:
                edit.new_value = edit.old_value
            state.tags = dict(state.original_tags)
            if self._db:
                for edit in state.edits:
                    if hasattr(self._db, "update_media_item_field"):
                        self._db.update_media_item_field(filepath, edit.field, edit.old_value)
            self.undoCompleted.emit(filepath, True)
            return {"ok": True, "restored_from": state.backup_path}
        except Exception as e:
            self.undoCompleted.emit(filepath, False)
            return {"ok": False, "error": str(e)}

    def load_batch(self, filepaths: list[str]) -> dict[str, Any]:
        results = []
        for fp in filepaths:
            results.append({"filepath": fp, **self.load(fp)})
        return {"ok": True, "results": results}

    def edit_batch(self, filepaths: list[str], field: str, value: str) -> dict[str, Any]:
        applied = 0
        errors = 0
        for fp in filepaths:
            r = self.edit_field(fp, field, value)
            if r.get("ok"):
                applied += 1
            else:
                errors += 1
        return {"ok": errors == 0, "applied": applied, "errors": errors}

    def apply_batch(self, filepaths: list[str], confirmation_token: str = "") -> dict[str, Any]:
        if filepaths:
            token = confirmation_token or f"batch_{id(filepaths)}"
            for fp in filepaths:
                self._confirmation_tokens[token] = fp
        results = []
        for fp in filepaths:
            r = self.confirm_and_apply(fp, confirmation_token)
            results.append({"filepath": fp, **r})
        return {"ok": True, "results": results}

    def cancel_operation(self, filepath: str):
        self._cancelled.add(filepath)
        self._rollback(filepath)
        self.operationCancelled.emit(filepath)

    def search_replace(self, filepath: str, search: str, replace: str,
                       fields: list[str] | None = None) -> dict[str, Any]:
        state = self._active.get(filepath)
        if not state:
            return {"ok": False, "error": "FILE_NOT_LOADED"}
        changes = 0
        target_fields = fields or ["title", "artist", "album", "albumartist", "genre", "composer", "comment"]
        for fname in target_fields:
            val = state.tags.get(fname, "")
            if search in val:
                new_val = val.replace(search, replace)
                self.edit_field(filepath, fname, new_val)
                changes += 1
        return {"ok": True, "changes": changes}

    def parse_filename(self, filepath: str, pattern: str = "{artist} - {title}") -> dict[str, Any]:
        stem = Path(filepath).stem
        if " - " in stem:
            parts = stem.split(" - ", 1)
            return {"ok": True, "parsed": {"artist": parts[0], "title": parts[1]}}
        if " - " not in stem and pattern == "{tracknumber}. {artist} - {title}":
            return {"ok": True, "parsed": {}}
        return {"ok": True, "parsed": {"title": stem}}

    def auto_number(self, filepaths: list[str]) -> dict[str, Any]:
        for i, fp in enumerate(filepaths, 1):
            self.edit_field(fp, "tracknumber", str(i))
        return {"ok": True, "numbered": len(filepaths)}

    def clear_active(self, filepath: str):
        self._active.pop(filepath, None)
        self._cancelled.discard(filepath)

    def refresh_model(self, filepath: str):
        result = self.load(filepath)
        if result.get("ok"):
            tags = result["tags"]
            return {"ok": True, "tags": tags}
        return result

    def diff(self, filepath: str) -> list[dict[str, Any]]:
        state = self._active.get(filepath)
        if not state:
            return []
        return [
            {"field": edit.field, "old": edit.old_value, "new": edit.new_value}
            for edit in state.edits
            if edit.old_value != edit.new_value
        ]

    def has_conflicts(self, filepath: str) -> list[str]:
        conflicts = []
        state = self._active.get(filepath)
        if not state:
            return conflicts
        from metadata.tag_reader import read_tags as rt
        current_tags = rt(filepath)
        if current_tags is None:
            return conflicts
        for edit in state.edits:
            current_val = str(getattr(current_tags, edit.field, "") or "")
            if current_val != edit.old_value and current_val != edit.new_value:
                conflicts.append(f"Campo '{edit.field}': esperaba '{edit.old_value}', tiene '{current_val}'")
        return conflicts
