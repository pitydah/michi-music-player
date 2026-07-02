from PySide6.QtCore import QObject, Signal, Property, Slot


class PlaylistsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db_conn=None, parent=None):
        super().__init__(parent)
        self._conn = db_conn
        self._store = None
        self._playlists = []

    def _ensure_store(self):
        if self._store is None and self._conn is not None:
            from library.playlists.playlist_store import PlaylistStore
            self._store = PlaylistStore(self._conn)

    @Property("QVariantList", notify=dataChanged)
    def playlists(self):
        return self._playlists

    @Slot()
    def refresh(self):
        self._ensure_store()
        result = []
        if self._store:
            try:
                summaries = self._store.get_all_playlists(include_stats=True)
                for s in summaries:
                    result.append({
                        "id": s.id,
                        "title": s.name,
                        "track_count": s.track_count,
                        "duration": self._format_duration(s.total_duration),
                        "cover_key": f"playlist_{s.id}",
                        "is_smart": s.is_smart,
                        "updated_at": s.updated_at,
                        "description": s.description,
                    })
            except Exception:
                import logging
                logging.getLogger("michi.playlists").debug("PlaylistStore refresh failed", exc_info=True)
        if not result:
            result = [
                {"title": "Favoritas", "track_count": 12, "duration": "45:30", "cover_key": "fav", "id": 0},
                {"title": "Descubrimientos", "track_count": 8, "duration": "32:15", "cover_key": "disc", "id": 0},
            ]
        self._playlists = result
        self.dataChanged.emit()

    def _format_duration(self, secs: float) -> str:
        if secs <= 0:
            return ""
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        if h > 0:
            return f"{h}h {m}m"
        return f"{m} min"
