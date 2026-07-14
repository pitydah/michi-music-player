"""HistoryListModel — BasePagedListModel with SQL pagination via HistoryQueryService (no N+1)."""
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
    DeviceRole = Qt.UserRole + 8
    AlbumKeyRole = Qt.UserRole + 9

    def __init__(self, db=None, history_query_service=None, query_executor=None, parent=None):
        super().__init__(page_size=200, query_executor=query_executor, parent=parent)
        self._db = db
        self._hqs = history_query_service

    def _owner(self) -> str:
        return "history"

    def roleNames(self):
        return {self.TrackIdRole: b"trackId", self.TrackUidRole: b"trackUid",
                self.TitleRole: b"title", self.ArtistRole: b"artist",
                self.AlbumRole: b"album", self.DurationRole: b"duration",
                self.PlayedAtRole: b"playedAt", self.DeviceRole: b"device",
                self.AlbumKeyRole: b"albumKey"}

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._items):
            return None
        item = self._items[index.row()]
        mapping = {self.TrackIdRole: "track_id", self.TrackUidRole: "track_uid",
                   self.TitleRole: "title", self.ArtistRole: "artist",
                   self.AlbumRole: "album", self.DurationRole: "duration",
                   self.PlayedAtRole: "played_at", self.DeviceRole: "device",
                   self.AlbumKeyRole: "album_key"}
        key = mapping.get(role, "")
        if key:
            return item.get(key, "")
        if role == Qt.DisplayRole:
            return item.get("title", "")
        return None

    def refresh(self):
        super().refresh()

    def _fetch_count(self, **kwargs) -> int:
        if self._hqs and hasattr(self._hqs, 'count_history'):
            try:
                return self._hqs.count_history(
                    artist=kwargs.get("artist", ""),
                    album=kwargs.get("album", ""),
                    device=kwargs.get("device", ""),
                    search=kwargs.get("search", ""),
                )
            except Exception:
                return 0
        if not self._db or not hasattr(self._db, 'get_play_history'):
            return 0
        try:
            rows = self._db.get_play_history()
            return len(rows) if rows else 0
        except Exception:
            return 0

    def _fetch_page(self, offset: int, limit: int, **kwargs) -> list[dict[str, Any]]:
        if self._hqs and hasattr(self._hqs, 'fetch_history'):
            try:
                return self._hqs.fetch_history(
                    offset=offset, limit=limit,
                    artist=kwargs.get("artist", ""),
                    album=kwargs.get("album", ""),
                    device=kwargs.get("device", ""),
                    search=kwargs.get("search", ""),
                )
            except Exception:
                return []
        if not self._db or not hasattr(self._db, 'get_play_history'):
            return []
        try:
            all_rows = self._db.get_play_history()
            if not all_rows:
                return []
            page = all_rows[offset:offset + limit]
            result = []
            for r in page:
                track_id = r.get("track_id", "")
                resolved = self._resolve_track(track_id)
                if resolved:
                    resolved["played_at"] = r.get("played_at", "")
                    resolved["device"] = r.get("device", "")
                    result.append(resolved)
                else:
                    result.append({"track_id": 0, "track_uid": "",
                                   "title": track_id, "artist": "", "album": "",
                                   "duration": 0, "played_at": r.get("played_at", ""),
                                   "device": r.get("device", "")})
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
                        "duration": row[5] or 0}
            return None
        except Exception:
            return None
