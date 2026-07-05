"""TrackListModel — QAbstractListModel for scalable track display in QML."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Property, Signal
from pathlib import Path


class TrackListModel(QAbstractListModel):
    dataChanged = Signal()

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

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: list[dict[str, Any]] = []
        self._all_items: list = []
        self._page_size = 500
        self._loaded_count = 0
        self._total_count = 0

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
        return self._loaded_count < self._total_count

    def fetchMore(self, parent=QModelIndex()):
        if parent.isValid():
            return
        remaining = self._total_count - self._loaded_count
        count = min(self._page_size, remaining)
        if count <= 0:
            return
        start = self._loaded_count
        end = min(start + count, len(self._all_items))
        new_items = [self._item_to_dict(s) for s in self._all_items[start:end]]
        self.beginInsertRows(QModelIndex(), len(self._items), len(self._items) + len(new_items) - 1)
        self._items.extend(new_items)
        self._loaded_count = end
        self.endInsertRows()
        self.dataChanged.emit()

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
            self.FormatRole: "format",
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

    @Property(int, notify=dataChanged)
    def count(self):
        return len(self._items)

    def resetFromItems(self, items: list):
        self.beginResetModel()
        self._all_items = items
        self._total_count = len(items)
        self._loaded_count = 0
        self._items = []
        self.endResetModel()
        self.dataChanged.emit()
        self.fetchMore()

    def setItems(self, items: list[dict]):
        self.beginResetModel()
        self._items = items
        self._loaded_count = len(items)
        self._total_count = len(items)
        self.endResetModel()
        self.dataChanged.emit()

    def appendItems(self, items: list[dict]):
        if not items:
            return
        self.beginInsertRows(QModelIndex(), len(self._items), len(self._items) + len(items) - 1)
        self._items.extend(items)
        self._loaded_count = len(self._items)
        self.endInsertRows()
        self.dataChanged.emit()

    def updateItem(self, index: int, data: dict):
        if 0 <= index < len(self._items):
            self._items[index].update(data)
            self.dataChanged.emit()

    def removeItem(self, index: int):
        if 0 <= index < len(self._items):
            self.beginRemoveRows(QModelIndex(), index, index)
            self._items.pop(index)
            self.endRemoveRows()
            self.dataChanged.emit()

    def _item_to_dict(self, s) -> dict:
        fp = getattr(s, 'filepath', '') or ''
        album_key = getattr(s, 'album_key', None) or getattr(s, 'album', '') or ''
        return {
            "track_id": getattr(s, 'id', 0) or 0,
            "track_uid": getattr(s, 'track_uid', '') or '',
            "title": getattr(s, 'title', None) or Path(fp).stem or '',
            "artist": getattr(s, 'artist', '') or '',
            "album": getattr(s, 'album', '') or '',
            "album_key": album_key,
            "duration": getattr(s, 'duration', 0) or 0,
            "format": (getattr(s, 'ext', '') or '').lstrip("."),
            "year": getattr(s, 'year', 0) or 0,
            "genre": getattr(s, 'genre', '') or '',
            "track_number": getattr(s, 'track_number', 0) or 0,
            "cover_key": album_key,
        }
