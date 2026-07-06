"""ArtistListModel — BasePagedListModel backed by LibraryQueryService."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class ArtistListModel(BasePagedListModel):
    NameRole = Qt.UserRole + 1
    TrackCountRole = Qt.UserRole + 2
    AlbumCountRole = Qt.UserRole + 3
    CoverKeyRole = Qt.UserRole + 4

    def __init__(self, query_service=None, query_executor=None, parent=None):
        super().__init__(page_size=100, query_executor=query_executor, parent=parent)
        self._qs = query_service

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.TrackCountRole: b"trackCount",
            self.AlbumCountRole: b"albumCount",
            self.CoverKeyRole: b"coverKey",
        }

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.NameRole: "name",
            self.TrackCountRole: "track_count",
            self.AlbumCountRole: "album_count",
            self.CoverKeyRole: "cover_key",
        }
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("name", "")
        return None

    def _fetch_count(self, **kwargs) -> int:
        if not self._qs:
            return 0
        return self._qs.count_artists(search=kwargs.get("search", ""))

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._qs:
            return []
        return self._qs.fetch_artists(offset=offset, limit=limit,
                                      search=kwargs.get("search", ""),
                                      sort=kwargs.get("sort", "name"),
                                      ascending=kwargs.get("asc", True))
