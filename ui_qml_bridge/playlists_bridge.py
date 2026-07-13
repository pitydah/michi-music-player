"""PlaylistsBridge — connects QML Playlists page to real LibraryDB playlist backend."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal, Property, Slot
import logging
import os
from pathlib import Path

logger = logging.getLogger("michi.playlists")


class PlaylistsBridge(QObject):
    dataChanged = Signal()

    def __init__(self, db=None, selection_context=None, player_service=None,
                 playlist_service=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._sel_ctx = selection_context
        self._player = player_service
        self._playlists = []
        self._svc = playlist_service

    def setSelectionContext(self, ctx):
        self._sel_ctx = ctx

    def _can(self) -> bool:
        return self._svc is not None or (self._db is not None and hasattr(self._db, 'get_playlists'))

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
        if self._svc:
            result = self._svc.create(name)
            if result.get("ok"):
                self.refresh()
            return result
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
        if self._svc:
            result = self._svc.delete(pid)
            if result.get("ok"):
                self.refresh()
            return result
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
        if self._svc:
            result = self._svc.rename(pid, name)
            if result.get("ok"):
                self.refresh()
            return result
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            self._db.update_playlist(pid, name=name)
            self.refresh()
            return {"ok": True}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def _get_playlist_items_internal(self, pid: int) -> list[dict]:
        """Internal: returns items with filepath for backend operations."""
        if not self._can():
            return []
        try:
            items = self._db.get_playlist_items(pid)
            return [
                {
                    "track_id": getattr(item, 'id', 0),
                    "track_uid": getattr(item, 'track_uid', '') or '',
                    "filepath": getattr(item, 'filepath', '') or '',
                    "title": getattr(item, 'title', '') or '',
                    "artist": getattr(item, 'artist', '') or '',
                    "album": getattr(item, 'album', '') or '',
                    "duration": getattr(item, 'duration', 0) or 0,
                    "position": idx,
                }
                for idx, item in enumerate(items)
            ]
        except Exception:
            return []

    def _playlist_item_to_public(self, item: dict) -> dict:
        return {
            "track_id": item.get("track_id", 0),
            "track_uid": item.get("track_uid", ""),
            "public_ref": f"track_{item.get('track_id', 0)}",
            "title": item.get("title", ""),
            "artist": item.get("artist", ""),
            "album": item.get("album", ""),
            "duration": item.get("duration", 0),
            "cover_key": item.get("album_key", "") or item.get("album", ""),
            "missing": not bool(item.get("filepath")),
        }

    @Slot(int, result=dict)
    def getPlaylistDetail(self, pid: int):
        internal = self._get_playlist_items_internal(pid)
        if not internal and self._can():
            return {"ok": True, "tracks": [], "count": 0}
        if not internal:
            return {"ok": False, "error": "NO_DB"}
        tracks = [self._playlist_item_to_public(t) for t in internal]
        return {"ok": True, "tracks": tracks, "count": len(tracks)}

    @Slot(int, str, str, result=dict)
    def addTrackToPlaylist(self, pid: int, filepath: str = "", track_id: str = ""):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        if not filepath and not track_id and self._sel_ctx:
            filepath = self._sel_ctx.selectedFilepath
            track_id = self._sel_ctx.selectedTrackId
        try:
            if not filepath and not track_id:
                return {"ok": False, "error": "NO_SELECTION"}
            if track_id:
                try:
                    tid = int(track_id)
                except (ValueError, TypeError):
                    tid = 0
                if tid:
                    self._db.add_track_to_playlist(pid, track_id=tid)
                    self.refresh()
                    return {"ok": True}
            if filepath and Path(filepath).is_file():
                self._db.add_track_to_playlist(pid, filepath)
                self.refresh()
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

    @Slot(int, result=dict)
    def addSelectedTrackToPlaylist(self, pid: int):
        return self.addTrackToPlaylist(pid)

    @Slot(int, "QVariantList", result=dict)
    def batchAddTracks(self, pid: int, tracks: list):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        count = 0
        for t in tracks:
            fp = t.get("filepath", "") if isinstance(t, dict) else ""
            tid = t.get("track_id", 0) if isinstance(t, dict) else 0
            if tid:
                self._db.add_track_to_playlist(pid, track_id=int(tid))
                count += 1
            elif fp:
                self._db.add_track_to_playlist(pid, filepath=fp)
                count += 1
        self.refresh()
        return {"ok": True, "count": count}

    @Slot(int, "QVariantList", result=dict)
    def batchAddTrackIds(self, playlist_id: int, track_ids: list):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        count = 0
        for tid in track_ids:
            try:
                self._db.add_track_to_playlist(playlist_id, track_id=int(tid))
                count += 1
            except (ValueError, TypeError):
                continue
        self.refresh()
        return {"ok": True, "count": count}

    @Slot(int, result=dict)
    def duplicatePlaylist(self, pid: int):
        if self._svc:
            result = self._svc.duplicate(pid)
            if result.get("ok"):
                self.refresh()
            return result
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            internal = self._get_playlist_items_internal(pid)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            orig_name = ""
            for p in self._playlists:
                if p.get("id") == pid:
                    orig_name = p.get("title", "")
                    break
            new_name = f"{orig_name} (copia)" if orig_name else "Copia"
            new_pid = self._db.create_playlist(new_name)
            for t in internal:
                fp = t.get("filepath", "")
                if fp:
                    self._db.add_track_to_playlist(new_pid, filepath=fp)
            self.refresh()
            return {"ok": True, "id": new_pid, "name": new_name}
        except Exception as e:
            logger.debug("duplicatePlaylist failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(int, result=dict)
    def clearPlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            if hasattr(self._db, 'clear_playlist'):
                self._db.clear_playlist(pid)
                self.refresh()
                return {"ok": True}
            detail = self.getPlaylistDetail(pid)
            if detail.get("ok"):
                for t in detail.get("tracks", []):
                    self._db.remove_track_from_playlist(pid, t.get("track_id", 0))
                self.refresh()
                return {"ok": True}
            return {"ok": False, "error": "NO_TRACKS"}
        except Exception as e:
            logger.debug("clearPlaylist failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(int, int, int, result=dict)
    def reorderTrack(self, pid: int, from_index: int, to_index: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            if hasattr(self._db, 'reorder_playlist_track'):
                self._db.reorder_playlist_track(pid, from_index, to_index)
                return {"ok": True}
            return {"ok": False, "error": "UNSUPPORTED"}
        except Exception as e:
            logger.debug("reorderTrack failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(int, int, result=dict)
    def playPlaylistFromIndex(self, pid: int, index: int = 0):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            internal = self._get_playlist_items_internal(pid)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal[index:] if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_TRACKS"}
            if self._player and hasattr(self._player, 'enqueue'):
                self._player.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            return {"ok": False, "error": "UNSUPPORTED"}
        except Exception as e:
            logger.debug("playPlaylistFromIndex failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(result=dict)
    def playlistScore(self) -> dict:
        """Return playlist module score based on real state."""
        score = 0
        if self._can():
            score += 20
        if self._playlists:
            real = [p for p in self._playlists if not p.get("is_demo")]
            count = len(real)
            if count > 0:
                score += min(30, count * 5)
        if self._db and hasattr(self._db, 'get_playlist_items'):
            score += 20
        if self._db and hasattr(self._db, 'update_playlist'):
            score += 15
        if self._db and hasattr(self._db, 'delete_playlist'):
            score += 15
        return {
            "score": min(100, score),
            "has_db": self._can(),
            "playlist_count": len([p for p in self._playlists if not p.get("is_demo")]),
            "can_create": self._can() and hasattr(self._db, 'create_playlist') if self._db else False,
            "can_delete": self._can() and hasattr(self._db, 'delete_playlist') if self._db else False,
            "can_rename": self._can() and hasattr(self._db, 'update_playlist') if self._db else False,
        }

    @Slot(str, result=dict)
    def saveQueueAsPlaylist(self, name: str):
        if self._svc:
            result = self._svc.save_queue(self._player, name)
            if result.get("ok"):
                self.refresh()
            return result
        if not name:
            return {"ok": False, "error": "EMPTY_NAME"}
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            fps = []
            if self._player and hasattr(self._player, 'get_queue'):
                q = self._player.get_queue()
                for item in (q or []):
                    fp = getattr(item, 'filepath', None) if not isinstance(item, dict) else item.get("filepath", "")
                    if fp:
                        fps.append(fp)
            if not fps and self._player and hasattr(self._player, 'current'):
                cur = self._player.current
                if cur:
                    fp = getattr(cur, 'filepath', '') if not isinstance(cur, dict) else cur.get("filepath", "")
                    if fp:
                        fps.append(fp)
            if not fps:
                return {"ok": False, "error": "NO_TRACKS"}
            pid = self._db.create_playlist(name)
            for fp in fps:
                self._db.add_track_to_playlist(pid, filepath=fp)
            self.refresh()
            return {"ok": True, "id": pid}
        except Exception as e:
            logger.debug("saveQueueAsPlaylist failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def previewPlaylistImport(self, filepath: str):
        if self._svc:
            return self._svc.import_preview(filepath)
        if not filepath or not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        try:
            from ui.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(filepath)
            valid = 0
            missing = 0
            for entry in entries:
                fp = getattr(entry, 'filepath', entry) if not isinstance(entry, str) else entry
                if isinstance(fp, str) and Path(fp).is_file():
                    valid += 1
                else:
                    missing += 1
            return {
                "ok": True, "format": Path(filepath).suffix,
                "name": Path(filepath).stem, "total_entries": len(entries),
                "valid_entries": valid, "missing_entries": missing,
                "encoding": "utf-8",
            }
        except Exception as e:
            return {"ok": False, "error": str(e)}

    @Slot(str, str, result=dict)
    def confirmPlaylistImport(self, filepath: str, name: str = ""):
        if self._svc:
            result = self._svc.import_confirm(filepath, name)
            if result.get("ok"):
                self.refresh()
            return result
        if not filepath or not Path(filepath).is_file():
            return {"ok": False, "error": "FILE_NOT_FOUND"}
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            from ui.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(filepath)
            playlist_name = name or Path(filepath).stem
            pid = self._db.create_playlist(playlist_name)
            count = 0
            for entry in entries:
                fp = getattr(entry, 'filepath', entry) if not isinstance(entry, str) else entry
                if isinstance(fp, str) and Path(fp).is_file():
                    self._db.add_track_to_playlist(pid, filepath=fp)
                    count += 1
            self.refresh()
            return {"ok": True, "id": pid, "count": count}
        except Exception as e:
            logger.debug("confirmPlaylistImport failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(str, result=dict)
    def cancelPlaylistImport(self, import_id: str):
        return {"ok": True}

    @Slot(str, result=dict)
    def importM3U(self, filepath: str):
        return self.confirmPlaylistImport(filepath)

    @Slot(str, result=dict)
    def importM3U8(self, filepath: str):
        return self.confirmPlaylistImport(filepath)

    @Slot(int, str, result=dict)
    def exportM3U(self, playlist_id: int, destination_path: str):
        if self._svc:
            return self._svc.export(playlist_id, destination_path)
        if not destination_path:
            return {"ok": False, "error": "EMPTY_PATH"}
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            from ui.playlist_io import export_m3u
            internal = self._get_playlist_items_internal(playlist_id)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_VALID_TRACKS"}
            export_m3u(destination_path, fps)
            return {"ok": True, "count": len(fps)}
        except Exception as e:
            logger.debug("exportM3U failed: %s", e)
            return {"ok": False, "error": str(e)}

    @Slot(int, str, result=dict)
    def exportM3U8(self, playlist_id: int, destination_path: str):
        return self.exportM3U(playlist_id, destination_path)

    @Slot(int, result=dict)
    def playPlaylist(self, pid: int):
        if not self._can():
            return {"ok": False, "error": "NO_DB"}
        try:
            internal = self._get_playlist_items_internal(pid)
            if not internal:
                return {"ok": False, "error": "NO_TRACKS"}
            fps = [t["filepath"] for t in internal if t.get("filepath")]
            if not fps:
                return {"ok": False, "error": "NO_TRACKS"}
            if self._player and hasattr(self._player, 'enqueue'):
                self._player.enqueue(fps, play_now=True)
                return {"ok": True, "count": len(fps)}
            return {"ok": False, "error": "UNSUPPORTED"}
        except Exception as e:
            logger.debug("Play playlist failed", exc_info=True)
            return {"ok": False, "error": str(e)}

    @staticmethod
    def _format_duration(secs: float) -> str:
        if secs <= 0:
            return ""
        h = int(secs // 3600)
        m = int((secs % 3600) // 60)
        return f"{h}h {m}m" if h > 0 else f"{m} min"
