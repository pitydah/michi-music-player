"""TrackListModel — BasePagedListModel with 12+ roles via QueryService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class TrackListModel(BasePagedListModel):
    TrackIdRole = Qt.UserRole + 1
    TrackUidRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ArtistRole = Qt.UserRole + 4
    AlbumRole = Qt.UserRole + 5
    AlbumKeyRole = Qt.UserRole + 6
    DurationRole = Qt.UserRole + 7
    FormatRole = Qt.UserRole + 8
    YearRole = Qt.UserRole + 9
    GenreRole = Qt.UserRole + 10
    TrackNumberRole = Qt.UserRole + 11
    CoverKeyRole = Qt.UserRole + 12

    def __init__(self, query_service=None, query_executor=None, parent=None):
        super().__init__(page_size=250, parent=parent)
        self._qs = query_service
        self._qe = query_executor
        self._search = ""
        self._artist_filter = ""
        self._album_filter = ""
        self._fmt_filter = ""
        self._sort = "title"
        self._asc = True

    def roleNames(self):
        return {
            self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
            self.TitleRole: b"title", self.ArtistRole: b"artist",
            self.AlbumRole: b"album", self.AlbumKeyRole: b"albumKey",
            self.DurationRole: b"duration", self.FormatRole: b"format",
            self.YearRole: b"year", self.GenreRole: b"genre",
            self.TrackNumberRole: b"trackNumber", self.CoverKeyRole: b"coverKey",
        }

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
            self.TitleRole: "title", self.ArtistRole: "artist",
            self.AlbumRole: "album", self.AlbumKeyRole: "album_key",
            self.DurationRole: "duration", self.FormatRole: "format",
            self.YearRole: "year", self.GenreRole: "genre",
            self.TrackNumberRole: "track_number", self.CoverKeyRole: "cover_key",
        }
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self, search: str = "", artist: str = "", album: str = "",
                fmt: str = "", sort: str = "title", asc: bool = True):
        self._search = search
        self._artist_filter = artist
        self._album_filter = album
        self._fmt_filter = fmt
        self._sort = sort
        self._asc = asc
        kw = dict(search=search, artist=artist, album=album, fmt=fmt, sort=sort, asc=asc)
        super().refresh(**kw)

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        return self._qs.count_tracks(**kwargs)

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        kw = dict(kwargs)
        asc = kw.pop("asc", True)
        return self._qs.fetch_tracks(offset=offset, limit=limit, ascending=asc, **kw)
