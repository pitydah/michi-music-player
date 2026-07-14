from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Qt


class AlbumDetailModel(QAbstractListModel):
    TrackNumberRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    DurationRole = Qt.UserRole + 4
    TrackIdRole = Qt.UserRole + 5
    TrackUidRole = Qt.UserRole + 6

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._album_info: dict[str, Any] = {}
        self._query_service = None

    def roleNames(self):
        return {self.TrackNumberRole: b"trackNumber", self.TitleRole: b"title",
                self.ArtistRole: b"artist", self.DurationRole: b"duration",
                self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackNumberRole: "track_number", self.TitleRole: "title",
                   self.ArtistRole: "artist", self.DurationRole: "duration",
                   self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def load(self, album_key: str, query_service=None):
        self._query_service = query_service or self._query_service
        if not self._query_service:
            return
        try:
            detail = self._query_service.fetch_album_detail(album_key)
            if not detail:
                return
            self._album_info = {k: v for k, v in detail.items() if k != "tracks"}
            tracks = detail.get("tracks", [])
            self.beginResetModel()
            self._items = [
                {"track_number": t.get("track_number", 0), "title": t.get("title", ""),
                 "artist": t.get("artist", ""), "duration": t.get("duration", 0),
                 "track_id": t.get("track_id", 0), "track_uid": t.get("track_uid", "")}
                for t in tracks
            ]
            self.endResetModel()
        except Exception:
            self.beginResetModel()
            self._items = []
            self.endResetModel()

    @property
    def album_title(self) -> str:
        return self._album_info.get("title", "")

    @property
    def album_artist(self) -> str:
        return self._album_info.get("artist", "")

    @property
    def album_year(self) -> int:
        return self._album_info.get("year", 0)

    @property
    def track_count(self) -> int:
        return self._album_info.get("track_count", 0)

    @property
    def duration(self) -> float:
        return self._album_info.get("duration", 0.0)

    @property
    def album_key(self) -> str:
        return self._album_info.get("album_key", "")

    @property
    def cover_key(self) -> str:
        return self._album_info.get("cover_key", self.album_key)

    def clear(self):
        self.beginResetModel()
        self._items = []
        self._album_info = {}
        self.endResetModel()

    def get_track(self, row: int) -> dict | None:
        if 0 <= row < len(self._items):
            return dict(self._items[row])
        return None
