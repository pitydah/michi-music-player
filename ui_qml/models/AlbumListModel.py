"""AlbumListModel — BasePagedListModel with 7 roles via QueryService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, Slot

from ui_qml.models.BasePagedListModel import BasePagedListModel


class AlbumListModel(BasePagedListModel):
    AlbumKeyRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    YearRole = Qt.UserRole + 4
    TrackCountRole = Qt.UserRole + 5
    DurationRole = Qt.UserRole + 6
    CoverKeyRole = Qt.UserRole + 7
    DecadeRole = Qt.UserRole + 8

    def __init__(self, query_service=None, query_executor=None, parent=None, page_size=100):
        super().__init__(page_size=page_size, query_executor=query_executor, parent=parent)
        self._qs = query_service

    def _owner(self) -> str:
        return "albums"

    def roleNames(self):
        return {self.AlbumKeyRole: b"albumKey", self.TitleRole: b"title",
                self.ArtistRole: b"artist", self.YearRole: b"year",
                self.TrackCountRole: b"trackCount", self.DurationRole: b"duration",
                self.CoverKeyRole: b"coverKey", self.DecadeRole: b"decade"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.AlbumKeyRole: "album_key", self.TitleRole: "title",
                   self.ArtistRole: "artist", self.YearRole: "year",
                   self.TrackCountRole: "track_count", self.DurationRole: "duration",
                   self.CoverKeyRole: "cover_key", self.DecadeRole: "decade"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self, search: str = "", artist: str = "", album: str = "",
                fmt: str = "", genre: str = "", composer: str = "", year: str = "",
                folder: str = "", favorites: bool = False, unplayed: bool = False,
                missing: bool = False, sort: str = "year", asc: bool = False):
        kw = dict(search=search, artist=artist, album=album, fmt=fmt, genre=genre,
                  composer=composer, year=year, folder=folder, favorites=favorites,
                  unplayed=unplayed, missing=missing, sort=sort, asc=asc)
        super().refresh(**kw)
        return {"ok": True, "search": search, "sort": sort, "asc": asc}

    @Slot(str, result=dict)
    def refreshForArtist(self, artist: str):
        return self.refresh(search=artist, sort="year", asc=True)

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        filters = {key: value for key, value in kwargs.items() if key not in ("sort", "asc")}
        return self._qs.count_albums(**filters)

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        return self._qs.fetch_albums(offset=offset, limit=limit, **kwargs)
