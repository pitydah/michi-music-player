"""HistoryListModel — BasePagedListModel reading play history from DB."""
from __future__ import annotations

from typing import Any

from PySide6.QtCore import Qt

from ui_qml.models.BasePagedListModel import BasePagedListModel


class HistoryListModel(BasePagedListModel):
    TrackIdRole = Qt.UserRole + 1
    TrackUidRole = Qt.UserRole + 2
    TitleRole = Qt.UserRole + 3
    ArtistRole = Qt.UserRole + 4
    AlbumRole = Qt.UserRole + 5
    DurationRole = Qt.UserRole + 6
    PlayedAtRole = Qt.UserRole + 7
    FilepathRole = Qt.UserRole + 8

    def __init__(self, db=None, parent=None):
        super().__init__(page_size=200, parent=parent)
        self._db = db

    def roleNames(self):
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.DurationRole: b"duration",
                self.PlayedAtRole: b"playedAt", self.FilepathRole: b"filepath"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                   self.AlbumRole: "album", self.DurationRole: "duration",
                   self.PlayedAtRole: "played_at", self.FilepathRole: "filepath"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self):
        super().refresh()

    def _fetch_count(self, **kwargs) -> int:
        if not self._db or not hasattr(self._db, 'get_play_history'):
            return 0
        try:
            rows = self._db.get_play_history()
            return len(rows) if rows else 0
        except Exception:
            return 0

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if not self._db or not hasattr(self._db, 'get_play_history'):
            return []
        try:
            rows = self._db.get_play_history()
            if not rows:
                return []
            page = rows[offset:offset + limit]
            result = []
            for r in page:
                track_id = r.get("track_id", "")
                track = self._resolve_track(track_id)
                if track:
                    result.append(track)
                else:
                    result.append({"track_id": 0, "track_uid": "", "title": track_id,
                                   "artist": "", "album": "", "duration": 0,
                                   "played_at": r.get("played_at", ""), "filepath": track_id})
            return result
        except Exception:
            return []

    def _resolve_track(self, track_id: str) -> dict | None:
        if not self._db or not hasattr(self._db, 'conn'):
            return None
        try:
            row = self._db.conn.execute(
                "SELECT id, filepath, title, artist, album, duration, track_uid "
                "FROM media_items WHERE (filepath=? OR CAST(id AS TEXT)=?) AND deleted_at IS NULL",
                (track_id, track_id)
            ).fetchone()
            if row:
                return {"track_id": row[0], "track_uid": row[6] or "",
                        "title": row[2] or "", "artist": row[3] or "", "album": row[4] or "",
                        "duration": row[5] or 0, "filepath": row[1] or "",
                        "played_at": ""}
            return None
        except Exception:
            return None
