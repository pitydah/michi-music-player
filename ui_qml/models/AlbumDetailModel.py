"""AlbumDetailModel — QAbstractListModel for album detail view (track list + album info).

Preserved from original: load(), _album_info, cover_key, and track roles.
Extended with additional metadata roles for album detail page.
"""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import QAbstractListModel, QModelIndex, Property, Qt


class AlbumDetailModel(QAbstractListModel):
    TrackNumberRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    DurationRole = Qt.UserRole + 4
    TrackIdRole = Qt.UserRole + 5
    TrackUidRole = Qt.UserRole + 6
    AlbumKeyRole = Qt.UserRole + 7
    GenreRole = Qt.UserRole + 8
    YearRole = Qt.UserRole + 9
    DiscNumberRole = Qt.UserRole + 10
    FormatRole = Qt.UserRole + 11
    CoverKeyRole = Qt.UserRole + 12
    AlbumArtistRole = Qt.UserRole + 13
    TrackCountRole = Qt.UserRole + 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._album_info: dict[str, Any] = {}
        self._query_service = None

    def roleNames(self):
        return {self.TrackNumberRole: b"trackNumber", self.TitleRole: b"title",
                self.ArtistRole: b"artist", self.DurationRole: b"duration",
                self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.AlbumKeyRole: b"albumKey", self.GenreRole: b"genre",
                self.YearRole: b"year", self.DiscNumberRole: b"discNumber",
                self.FormatRole: b"format", self.CoverKeyRole: b"coverKey",
                self.AlbumArtistRole: b"albumArtist", self.TrackCountRole: b"trackCount"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackNumberRole: "track_number", self.TitleRole: "title",
                   self.ArtistRole: "artist", self.DurationRole: "duration",
                   self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.AlbumKeyRole: "album_key", self.GenreRole: "genre",
                   self.YearRole: "year", self.DiscNumberRole: "disc_number",
                   self.FormatRole: "format", self.CoverKeyRole: "cover_key",
                   self.AlbumArtistRole: "album_artist", self.TrackCountRole: "track_count"}
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
                 "track_id": t.get("track_id", 0), "track_uid": t.get("track_uid", ""),
                 "album_key": album_key, "genre": t.get("genre", ""),
                 "year": t.get("year", 0), "disc_number": t.get("disc_number", 0),
                 "format": t.get("format", ""), "cover_key": t.get("cover_key", ""),
                 "album_artist": t.get("album_artist", ""), "track_count": t.get("track_count", 0)}
                for t in tracks
            ]
            self.endResetModel()
        except Exception:
            self.beginResetModel()
            self._items = []
            self._album_info = {}
            self.endResetModel()

    def get_track(self, row: int) -> dict[str, Any] | None:
        if 0 <= row < len(self._items):
            return self._items[row]
        return None

    def clear(self):
        self.beginResetModel()
        self._items = []
        self._album_info = {}
        self.endResetModel()

    @property
    def album_key(self):
        return self._album_info.get("album_key", "")

    @property
    def cover_key(self):
        return self._album_info.get("cover_key", "") or self.album_key

    @property
    def album_title(self):
        return self._album_info.get("title", "")

    @property
    def album_artist(self):
        return self._album_info.get("artist", "")

    @property
    def album_year(self):
        return self._album_info.get("year", 0)

    @property
    def track_count(self):
        return self._album_info.get("track_count", len(self._items))

    @property
    def duration(self):
        return self._album_info.get("duration", sum(t.get("duration", 0) for t in self._items))

    @Property(str, notify=lambda: None)
    def albumTitle(self):
        return self.album_title

    @Property(str, notify=lambda: None)
    def albumArtist(self):
        return self.album_artist

    @Property(int, notify=lambda: None)
    def albumYear(self):
        return self.album_year

    @Property(str, notify=lambda: None)
    def albumGenre(self):
        return self._album_info.get("genre", "")

    @Property(int, notify=lambda: None)
    def trackCount(self):
        return self.track_count

    @Property(int, notify=lambda: None)
    def totalDuration(self):
        return self.duration

    @Property(bool, notify=lambda: None)
    def compilation(self):
        return self._album_info.get("compilation", False)

    @Property(bool, notify=lambda: None)
    def favorite(self):
        return self._album_info.get("favorite", False)
