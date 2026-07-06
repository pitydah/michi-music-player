"""QueueListModel — BasePagedListModel reading from PlayerService queue."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class QueueListModel(BasePagedListModel):
    TrackIdRole = Qt.UserRole + 1
    TrackUidRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ArtistRole = Qt.UserRole + 4
    AlbumRole = Qt.UserRole + 5
    AlbumKeyRole = Qt.UserRole + 6
    DurationRole = Qt.UserRole + 7
    FilepathRole = Qt.UserRole + 8

    def __init__(self, player_service=None, parent=None):
        super().__init__(page_size=500, parent=parent)
        self._player = player_service

    def roleNames(self):
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.AlbumKeyRole: b"albumKey",
                self.DurationRole: b"duration", self.FilepathRole: b"filepath"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                   self.AlbumRole: "album", self.AlbumKeyRole: "album_key",
                   self.DurationRole: "duration", self.FilepathRole: "filepath"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self):
        super().refresh()

    def _fetch_count(self, **kwargs) -> int:
        if not self._player or not hasattr(self._player, 'get_queue'):
            return 0
        try:
            q = self._player.get_queue()
            return len(q) if q else 0
        except Exception:
            return 0

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._player or not hasattr(self._player, 'get_queue'):
            return []
        try:
            q = self._player.get_queue()
            if not q:
                return []
            page = q[offset:offset + limit]
            return [self._item_to_dict(i) for i in page]
        except Exception:
            return []

    def _item_to_dict(self, item) -> dict:
        if isinstance(item, dict):
            return {
                "track_id": item.get("id", item.get("track_id", 0)),
                "track_uid": item.get("track_uid", ""),
                "title": item.get("title", ""),
                "artist": item.get("artist", ""),
                "album": item.get("album", ""),
                "album_key": item.get("album_key", ""),
                "duration": item.get("duration", 0),
                "filepath": item.get("filepath", ""),
            }
        return {
            "track_id": getattr(item, "id", getattr(item, "track_id", 0)),
            "track_uid": getattr(item, "track_uid", ""),
            "title": getattr(item, "title", ""),
            "artist": getattr(item, "artist", ""),
            "album": getattr(item, "album", ""),
            "album_key": getattr(item, "album_key", ""),
            "duration": getattr(item, "duration", 0),
            "filepath": getattr(item, "filepath", ""),
        }
