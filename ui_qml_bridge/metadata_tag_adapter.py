"""MetadataTagAdapter — safe metadata read/write with mapping, backup, verify, rollback."""
from __future__ import annotations

import logging
import shutil
import tempfile
import time
from pathlib import Path

from metadata.tag_model import TrackTags
from metadata.tag_reader import read_tags
from metadata.tag_writer import write_tags
from ui_qml_bridge.error_catalog import safe_message
import contextlib

logger = logging.getLogger("michi.metadata_adapter")

QML_TO_TAG_KEY = {
    "title": "title",
    "artist": "artist",
    "album": "album",
    "album_artist": "albumartist",
    "genre": "genre",
    "year": "date",
    "track_number": "tracknumber",
    "track_total": "tracktotal",
    "disc_number": "discnumber",
    "disc_total": "disctotal",
    "composer": "composer",
    "comment": "comment",
    "bpm": "bpm",
    "copyright": "copyright",
    "sort_title": "sort_title",
    "sort_artist": "sort_artist",
    "sort_album": "sort_album",
}

TAG_TO_QML_KEY = {v: k for k, v in QML_TO_TAG_KEY.items()}

PRESERVED_FIELDS = {
    "mb_track_id", "mb_album_id", "mb_albumartist_id",
    "isrc", "replaygain_track", "replaygain_album", "replaygain_track_peak",
    "label", "conductor", "compilation", "media_type", "encoder",
    "originaldate", "remixer", "grouping", "mood",
}


def load_tags(filepath: str) -> dict | None:
    """Load full TrackTags from a file. Returns None on error."""
    try:
        return read_tags(filepath)
    except Exception as e:
        logger.debug("load_tags failed: %s", e)
        return None


def qml_key_to_tag_key(qml_key: str) -> str:
    return QML_TO_TAG_KEY.get(qml_key, qml_key)


def apply_patch(base_tags: TrackTags, changes: dict) -> TrackTags:
    """Apply only dirty fields from changes dict to base_tags. Returns modified tags."""
    for qml_key, value in changes.items():
        tag_key = qml_key_to_tag_key(qml_key)
        if hasattr(base_tags, tag_key):
            old_val = getattr(base_tags, tag_key)
            if str(old_val) != str(value):
                setattr(base_tags, tag_key, value)
                base_tags.mark_dirty(tag_key)
    return base_tags


def create_backup(filepath: str) -> str | None:
    """Create a backup of the file. Returns backup path or None."""
    try:
        p = Path(filepath)
        if not p.exists():
            return None
        bak_dir = Path(tempfile.gettempdir()) / "michi_metadata_backup"
        bak_dir.mkdir(parents=True, exist_ok=True)
        bak_path = str(bak_dir / f"{p.stem}_{int(time.time())}{p.suffix}")
        shutil.copy2(filepath, bak_path)
        return bak_path
    except Exception as e:
        logger.debug("create_backup failed: %s", e)
        return None


def write_tags_safe(tags: TrackTags, backup_path: str | None = None) -> dict:
    """Write tags with optional pre-write backup. Returns result dict."""
    if not tags.filepath or not Path(tags.filepath).exists():
        return {"ok": False, "error_code": "FILE_NOT_FOUND", "message": safe_message("FILE_NOT_FOUND")}
    if not tags.dirty:
        return {"ok": False, "error_code": "NO_CHANGES", "message": safe_message("NO_CHANGES")}
    try:
        ok = write_tags(tags)
        if ok:
            return {"ok": True}
        if backup_path and Path(backup_path).exists():
            shutil.copy2(backup_path, tags.filepath)
        return {"ok": False, "error_code": "WRITE_FAILED", "message": safe_message("WRITE_FAILED")}
    except Exception as e:
        logger.debug("write_tags_safe failed: %s", e)
        if backup_path and Path(backup_path).exists():
            with contextlib.suppress(Exception):
                shutil.copy2(backup_path, tags.filepath)
        return {"ok": False, "error_code": "WRITE_FAILED", "message": str(e)}


def verify_changes(filepath: str, expected_changes: dict) -> dict:
    """Verify that changes were actually written. Returns ok/error."""
    try:
        reread = read_tags(filepath)
        if reread is None:
            return {"ok": False, "error_code": "VERIFY_FAILED", "message": safe_message("VERIFY_FAILED")}
        for qml_key, expected_value in expected_changes.items():
            tag_key = qml_key_to_tag_key(qml_key)
            actual_value = str(getattr(reread, tag_key, ""))
            if str(expected_value) != actual_value:
                return {"ok": False, "error_code": "VERIFY_FAILED",
                        "message": f"Field '{qml_key}' expected '{expected_value}' got '{actual_value}'"}
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error_code": "VERIFY_FAILED", "message": str(e)}


def rollback(backup_path: str, original_path: str) -> dict:
    """Restore a file from backup."""
    try:
        if not backup_path or not Path(backup_path).exists():
            return {"ok": False, "error_code": "BACKUP_NOT_FOUND", "message": safe_message("BACKUP_FAILED")}
        shutil.copy2(backup_path, original_path)
        return {"ok": True}
    except Exception as e:
        logger.debug("rollback failed: %s", e)
        return {"ok": False, "error_code": "ROLLBACK_FAILED", "message": safe_message("ROLLBACK_FAILED")}
