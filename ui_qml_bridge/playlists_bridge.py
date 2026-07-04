"""PlaylistsBridge — connects QML Playlists page to real LibraryDB playlist backend."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
import os

logger = logging.getLogger("michi.playlists")


class PlaylistsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, selection_context=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._sel_ctx = selection_context
        self._playlists = []

    def setSelectionContext(self, ctx):
        self._sel_ctx = ctx

    def _can(self) -> bool:
        return self._db is not None and hasattr(self._db, 'get_playlists')

    @Property("QVariantList", notify=dataChanged)
    def playlists(self):
        return self._playlists

    @Slot()
    def refresh(self):
        result = []
        if self._can():
            try:
                plists = self._db.get_playlists()
                for p in plists:
                    pid = p.get("id", 0) if isinstance(p, dict) else getattr(p, 'id', 0)
                    name = p.get("name", "") if isinstance(p, dict) else getattr(p, 'name', '')
                    track_count = p.get("track_count", 0) if isinstance(p, dict) else getattr(p, 'track_count', 0)
                    result.append({
                        "id": pid,
                        "title": name,
                        "track_count": track_count,
                        "duration": "",
                        "cover_key": f"playlist_{pid}",
                        "is_smart": False,
                        "updated_at": "",
                        "description": "",
                    })
            except Exception:
                logger.debug("Playlist refresh failed", exc_info=True)
                result = []
        if not result and os.environ.get("MICHI_QML_DEMO") == "1":
            result = [
                {"id": 0, "title": "Favoritas", "track_count": 12, "duration": "45:30",
                 "cover_key": "fav", "is_demo": True},
                {"id": 0, "title": "Descubrimientos", "track_count": 8, "duration": "32:15",
                 "cover_key": "disc", "is_demo": True},
            ]
        self._playlists = result
        self.dataChanged.emit()

    @Slot(str, result=dict)
    def createPlaylist(self, name: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            pid = self._db.create_playlist(name)
            self.refresh()
            return {"ok": True, "id": pid}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def deletePlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.delete_playlist(pid)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, str, result=dict)
    def renamePlaylist(self, pid: int, name: str):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.update_playlist(pid, name=name)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def getPlaylistDetail(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            items = self._db.get_playlist_items(pid)
            tracks = []
            for item in items:
                tracks.append({
                    "track_id": getattr(item, 'id', 0),
                    "title": getattr(item, 'title', '') or '',
                    "artist": getattr(item, 'artist', '') or '',
                    "album": getattr(item, 'album', '') or '',
                    "duration": getattr(item, 'duration', 0) or 0,
                    "filepath": getattr(item, 'filepath', '') or '',
                })
            return {"ok": True, "tracks": tracks, "count": len(tracks)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def addSelectedTrackToPlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            if hasattr(self, '_sel_ctx') and self._sel_ctx:
                filepath = self._sel_ctx.selectedFilepath
                track_id = self._sel_ctx.selectedTrackId
            else:
                return {"ok": False, "error": "NO_SELECTION"}
            if track_id:
                self._db.add_track_to_playlist(pid, track_id=track_id)
                return {"ok": True}
            from pathlib import Path
            if filepath and Path(filepath).is_file():
                self._db.add_track_to_playlist(pid, filepath)
                return {"ok": True}
            return {"ok": False, "error": "NO_VALID_TRACK"}
        except Exception as e:
            logger.debug("Add track to playlist failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def removeTrackFromPlaylist(self, pid: int, track_id: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.remove_track_from_playlist(pid, track_id)
            return {"ok": True}
        except Exception as e:
            logger.debug("Remove track from playlist failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @Slot(int)
    def playPlaylist(self, pid: int):
        if self._db and hasattr(self._db, 'play_playlist'):
            try:
                self._db.play_playlist(pid)
            except Exception:
                logger.debug("Play playlist failed", exc_info=True)

    @staticmethod
    def _format_duration(secs: float) -> str:
        if secs <= 0:
            return ""
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m}m" if h > 0 else f"{m} min"
