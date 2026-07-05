"""AlbumListModel — QAbstractListModel for scalable album grid display in QML."""

from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Property, Signal


class AlbumListModel(QAbstractListModel):
    dataChanged = Signal()

    AlbumKeyRole = Qt.UserRole + 1
    TitleRole = Qt.UserRole + 2
    ArtistRole = Qt.UserRole + 3
    YearRole = Qt.UserRole + 4
    TrackCountRole = Qt.UserRole + 5
    DurationRole = Qt.UserRole + 6
    CoverKeyRole = Qt.UserRole + 7

    def __init__(self, parent=None):
        super().__init__(parent)
        self._albums: list[dict[str, Any]] = []

    def roleNames(self):
        return {
            self.AlbumKeyRole: b"albumKey",
            self.TitleRole: b"title",
            self.ArtistRole: b"artist",
            self.YearRole: b"year",
            self.TrackCountRole: b"trackCount",
            self.DurationRole: b"duration",
            self.CoverKeyRole: b"coverKey",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._albums)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._albums):
            return None
        item = self._albums[index.row()]
        mapping = {
            self.AlbumKeyRole: "album_key",
            self.TitleRole: "title",
            self.ArtistRole: "artist",
            self.YearRole: "year",
            self.TrackCountRole: "track_count",
            self.DurationRole: "duration",
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
        return len(self._albums)

    def resetFromAlbums(self, albums: list[dict]):
        self.beginResetModel()
        self._albums = albums
        self.endResetModel()
        self.dataChanged.emit()

    def _build_from_songs(self, songs: list) -> list[dict]:
        seen: dict[str, dict] = {}
        for s in songs:
            album_key = getattr(s, 'album_key', None) or getattr(s, 'album', '') or ''
            if not album_key:
                continue
            if album_key not in seen:
                seen[album_key] = {
                    "album_key": album_key,
                    "title": getattr(s, 'album', '') or album_key,
                    "artist": getattr(s, 'albumartist', '') or getattr(s, 'artist', '') or '',
                    "year": getattr(s, 'year', 0) or 0,
                    "track_count": 0,
                    "duration": 0.0,
                    "cover_key": album_key,
                }
            entry = seen[album_key]
            entry["track_count"] += 1
            entry["duration"] += getattr(s, 'duration', 0) or 0
        return sorted(seen.values(), key=lambda x: (x.get("year", 0) or 0, x.get("title", "") or ""))

    def resetFromSongs(self, songs: list):
        albums = self._build_from_songs(songs)
        self.resetFromAlbums(albums)
