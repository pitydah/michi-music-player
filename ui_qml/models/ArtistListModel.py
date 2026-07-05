"""ArtistListModel — QAbstractListModel for scalable artist display."""

from __future__ import annotations

from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex, Property, Signal


class ArtistListModel(QAbstractListModel):
    dataChanged = Signal()

    NameRole = Qt.UserRole + 1
    TrackCountRole = Qt.UserRole + 2
    AlbumCountRole = Qt.UserRole + 3
    CoverKeyRole = Qt.UserRole + 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self._artists: list[dict] = []

    def roleNames(self):
        return {
            self.NameRole: b"name",
            self.TrackCountRole: b"trackCount",
            self.AlbumCountRole: b"albumCount",
            self.CoverKeyRole: b"coverKey",
        }

    def rowCount(self, parent=QModelIndex()):
        return len(self._artists)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._artists):
            return None
        item = self._artists[index.row()]
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

    @Property(int, notify=dataChanged)
    def count(self):
        return len(self._artists)

    def resetFromArtists(self, artists: list[dict]):
        self.beginResetModel()
        self._artists = artists
        self.endResetModel()
        self.dataChanged.emit()

    def buildFromSongs(self, songs: list) -> list[dict]:
        seen: dict[str, dict] = {}
        for s in songs:
            name = getattr(s, 'albumartist', '') or getattr(s, 'artist', '') or ''
            if not name:
                continue
            if name not in seen:
                seen[name] = {"name": name, "track_count": 0, "album_count": 0, "cover_key": ""}
                seen_albums: set = set()
            entry = seen[name]
            entry["track_count"] += 1
            album = getattr(s, 'album', '') or ''
            if album and album not in seen_albums:
                seen_albums.add(album)
                entry["album_count"] += 1
            if not entry["cover_key"]:
                entry["cover_key"] = getattr(s, 'album_key', '') or ''
        return sorted(seen.values(), key=lambda x: x.get("name", "").lower())

    def resetFromSongs(self, songs: list):
        artists = self.buildFromSongs(songs)
        self.resetFromArtists(artists)
