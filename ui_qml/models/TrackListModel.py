"""TrackListModel — QAbstractListModel backed by LibraryQueryService (paginated)."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Property, Signal


class TrackListModel(QAbstractListModel):
    countChanged = Signal()
    loadingChanged = Signal()
    errorChanged = Signal()
    hasMoreChanged = Signal()

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

    def __init__(self, query_service=None, parent=None):
        super().__init__(parent)
        self._qs = query_service
        self._items: list[dict[str, Any]] = []
        self._total_count = 0
        self._page_size = 250
        self._search = ""
        self._artist_filter = ""
        self._album_filter = ""
        self._fmt_filter = ""
        self._sort = "title"
        self._asc = True
        self._loading = False
        self._error = ""

    def roleNames(self):
        return {
            self.TrackIdRole: b"trackId",
            self.TrackUidRole: b"trackUid",
            self.TitleRole: b"title",
            self.ArtistRole: b"artist",
            self.AlbumRole: b"album",
            self.AlbumKeyRole: b"albumKey",
            self.DurationRole: b"duration",
            self.FormatRole: b"format",
            self.YearRole: b"year",
            self.GenreRole: b"genre",
            self.TrackNumberRole: b"trackNumber",
            self.CoverKeyRole: b"coverKey",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

    def canFetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return False
        return len(self._items) < self._total_count

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid() or not self._qs:
            return
        offset = len(self._items)
        new_items = self._qs.fetch_tracks(
            offset=offset, limit=self._page_size,
            search=self._search, artist=self._artist_filter,
            album=self._album_filter, fmt=self._fmt_filter,
            sort=self._sort, ascending=self._asc,
        )
        if new_items:
            self.beginInsertRows(QModelIndex(), offset, offset + len(new_items) - 1)
            self._items.extend(new_items)
            self.endInsertRows()
            self.countChanged.emit()
            self.hasMoreChanged.emit()

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {
            self.TrackIdRole: "track_id",
            self.TrackUidRole: "track_uid",
            self.TitleRole: "title",
            self.ArtistRole: "artist",
            self.AlbumRole: "album",
            self.AlbumKeyRole: "album_key",
            self.DurationRole: "duration",
            self.FormatRole: "ext",
            self.YearRole: "year",
            self.GenreRole: "genre",
            self.TrackNumberRole: "track_number",
            self.CoverKeyRole: "cover_key",
        }
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    @Property(int, notify=countChanged)
    def count(self):
        return len(self._items)

    @Property(int, notify=countChanged)
    def totalCount(self):
        return self._total_count

    @Property(bool, notify=loadingChanged)
    def loading(self):
        return self._loading

    @Property(str, notify=errorChanged)
    def error(self):
        return self._error

    @Property(bool, notify=hasMoreChanged)
    def hasMore(self):
        return len(self._items) < self._total_count

    def refresh(self, search: str = "", artist: str = "", album: str = "",
                fmt: str = "", sort: str = "title", asc: bool = True):
        self._search = search
        self._artist_filter = artist
        self._album_filter = album
        self._fmt_filter = fmt
        self._sort = sort
        self._asc = asc
        self._loading = True
        self.loadingChanged.emit()
        if self._qs:
            self._total_count = self._qs.count_tracks(
                search=search, artist=artist, album=album, fmt=fmt)
            self.beginResetModel()
            self._items = self._qs.fetch_tracks(
                offset=0, limit=self._page_size,
                search=search, artist=artist, album=album, fmt=fmt,
                sort=sort, ascending=asc,
            )
            self.endResetModel()
            self._error = ""
        else:
            self.beginResetModel()
            self._items = []
            self._total_count = 0
            self.endResetModel()
            self._error = "Query service not available"
        self._loading = False
        self.loadingChanged.emit()
        self.countChanged.emit()
        self.hasMoreChanged.emit()
        self.errorChanged.emit()
