"""AlbumPagedListModel — BasePagedListModel with all album-level roles for grid/list views."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class AlbumPagedListModel(BasePagedListModel):
    AlbumKeyRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    YearRole = Qt.UserRole + 4
    TrackCountRole = Qt.UserRole + 5
    DurationRole = Qt.UserRole + 6
    CoverKeyRole = Qt.UserRole + 7
    ArtistIdRole = Qt.UserRole + 8
    AlbumArtistRole = Qt.UserRole + 9
    DiscCountRole = Qt.UserRole + 10
    FormatsRole = Qt.UserRole + 11
    MaxQualityRole = Qt.UserRole + 12
    LastPlayedRole = Qt.UserRole + 13
    DateAddedRole = Qt.UserRole + 14
    FavoriteRole = Qt.UserRole + 15
    CompilationRole = Qt.UserRole + 16
    GenreRole = Qt.UserRole + 17

    def __init__(self, query_service=None, query_executor=None, parent=None, page_size=100):
        super().__init__(page_size=page_size, query_executor=query_executor, parent=parent)
        self._qs = query_service

    def _owner(self) -> str:
        return "album_paged"

    def roleNames(self):
        return {self.AlbumKeyRole: b"albumKey", self.TitleRole: b"title",
                self.ArtistRole: b"artist", self.YearRole: b"year",
                self.GenreRole: b"genre", self.TrackCountRole: b"trackCount",
                self.DurationRole: b"duration", self.CoverKeyRole: b"coverKey",
                self.ArtistIdRole: b"artistId", self.AlbumArtistRole: b"albumArtist",
                self.DiscCountRole: b"discCount", self.FormatsRole: b"formats",
                self.MaxQualityRole: b"maxQuality", self.LastPlayedRole: b"lastPlayed",
                self.DateAddedRole: b"dateAdded", self.FavoriteRole: b"favorite",
                self.CompilationRole: b"compilation"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.AlbumKeyRole: "album_key", self.TitleRole: "title",
                   self.ArtistRole: "artist", self.YearRole: "year",
                   self.GenreRole: "genre", self.TrackCountRole: "track_count",
                   self.DurationRole: "duration", self.CoverKeyRole: "cover_key",
                   self.ArtistIdRole: "artist_id", self.AlbumArtistRole: "album_artist",
                   self.DiscCountRole: "disc_count", self.FormatsRole: "formats",
                   self.MaxQualityRole: "max_quality", self.LastPlayedRole: "last_played",
                   self.DateAddedRole: "date_added", self.FavoriteRole: "favorite",
                   self.CompilationRole: "compilation"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        return self._qs.count_albums(search=kwargs.get("search", ""))

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        return self._qs.fetch_albums(offset=offset, limit=limit,
                                     search=kwargs.get("search", ""),
                                     sort=kwargs.get("sort", "year"),
                                     asc=kwargs.get("asc", False))
