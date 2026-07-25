"""Canonical queue-item projection for QML models and bridges."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Any


def _cover_key_for_path(filepath: str) -> str:
    """Return the stable cover cache key derived from a private media path."""
    if not filepath:
        return ""
    return f"track_{hashlib.md5(filepath.encode()).hexdigest()[:12]}"


def _value(raw: Any, *names: str, default: Any = "") -> Any:
    if isinstance(raw, dict):
        for name in names:
            if name in raw:
                return raw[name]
        return default
    for name in names:
        if hasattr(raw, name):
            return getattr(raw, name)
    return default


def _text(value: Any, default: str = "") -> str:
    return str(value) if value not in (None, "") else default


def _integer(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


@dataclass
class QueueItem:
    """Typed internal queue item with a safe QML role projection."""

    queue_index: int = 0
    track_id: str = ""
    track_uid: str = ""
    title: str = ""
    artist: str = ""
    album: str = ""
    album_key: str = ""
    duration: int = 0
    filepath: str = ""
    cover_key: str = ""
    source_type: str = "local_file"
    is_current: bool = False
    position: int = 0

    def as_dict(self) -> dict[str, str | int | bool]:
        """Return only the complete public QML role contract."""
        return {
            "track_id": self.track_id,
            "track_uid": self.track_uid,
            "title": self.title,
            "artist": self.artist,
            "album": self.album,
            "album_key": self.album_key,
            "duration": self.duration,
            "is_current": self.is_current,
            "position": self.position,
            "cover_key": self.cover_key,
            "source_type": self.source_type,
        }


def queue_item_from_raw(raw: Any, index: int, current_index: int) -> QueueItem:
    """Normalize dict or object queue input into the canonical typed item."""
    filepath = _text(_value(raw, "filepath", "path", "url"))
    cover_key = _text(_value(raw, "cover_key")) or _cover_key_for_path(filepath)
    position = int(index)
    return QueueItem(
        queue_index=position,
        track_id=_text(_value(raw, "track_id", "id")),
        track_uid=_text(_value(raw, "track_uid")),
        title=_text(_value(raw, "title", "name")),
        artist=_text(_value(raw, "artist")),
        album=_text(_value(raw, "album")),
        album_key=_text(_value(raw, "album_key")),
        duration=_integer(_value(raw, "duration", default=0)),
        filepath=filepath,
        cover_key=cover_key,
        source_type=_text(_value(raw, "source_type"), "local_file"),
        is_current=position == int(current_index),
        position=position,
    )
