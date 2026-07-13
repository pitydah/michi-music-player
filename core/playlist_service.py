"""PlaylistService — business logic for playlist CRUD, import/export, transactions."""
from __future__ import annotations

import logging
from pathlib import Path


logger = logging.getLogger("michi.playlist_service")


class PlaylistTransaction:
    def __init__(self, db):
        self._db = db
        self._active = False

    def begin(self):
        if not self._active:
            self._db.conn.execute("BEGIN")
            self._active = True

    def commit(self):
        if self._active:
            self._db.conn.commit()
            self._active = False

    def rollback(self):
        if self._active:
            self._db.conn.rollback()
            self._active = False


class PlaylistService:
    def __init__(self, db=None):
        self._db = db
        self._txn = PlaylistTransaction(db) if db else None

    def _can(self) -> bool:
        return self._db is not None and hasattr(self._db, 'get_playlists')

    def _error(self, code: str, message: str = "") -> dict:
        return {"ok": False, "error_code": code, "message": message}

    def _ok(self, **kw) -> dict:
        result = {"ok": True}
        result.update(kw)
        return result

    def begin(self) -> dict:
        if self._txn:
            self._txn.begin()
        return self._ok()

    def commit(self) -> dict:
        if self._txn:
            self._txn.commit()
        return self._ok()

    def rollback(self) -> dict:
        if self._txn:
            self._txn.rollback()
        return self._ok()

    def list(self) -> list[dict]:
        if not self._can():
            return []
        try:
            plists = self._db.get_playlists()
            return [
                {
                    "id": p.get("id", 0) if isinstance(p, dict) else getattr(p, 'id', 0),
                    "name": p.get("name", "") if isinstance(p, dict) else getattr(p, 'name', ''),
                    "track_count": p.get("track_count", 0) if isinstance(p, dict) else getattr(p, 'track_count', 0),
                }
                for p in plists
            ]
        except Exception:
            return []

    def create(self, name: str) -> dict:
        if not self._can():
            return self._error("NO_DB")
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        try:
            pid = self._db.create_playlist(name.strip())
            return self._ok(id=pid, name=name.strip())
        except Exception as e:
            return self._error("CREATE_FAILED", str(e))

    def rename(self, pid: int, name: str) -> dict:
        if not self._can():
            return self._error("NO_DB")
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        try:
            self._db.update_playlist(pid, name=name.strip())
            return self._ok()
        except Exception as e:
            return self._error("RENAME_FAILED", str(e))

    def delete(self, pid: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            self._db.delete_playlist(pid)
            return self._ok()
        except Exception as e:
            return self._error("DELETE_FAILED", str(e))

    def duplicate(self, pid: int, new_name: str = "") -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            items = self._get_items_internal(pid)
            if not items:
                return self._error("NO_TRACKS")
            orig_name = ""
            for p in self.list():
                if p.get("id") == pid:
                    orig_name = p.get("name", "")
                    break
            name = new_name or f"{orig_name} (copia)"
            new_pid = self._db.create_playlist(name)
            for t in items:
                fp = t.get("filepath", "")
                if fp:
                    self._db.add_track_to_playlist(new_pid, filepath=fp)
            return self._ok(id=new_pid, name=name, count=len(items))
        except Exception as e:
            return self._error("DUPLICATE_FAILED", str(e))

    def add_track(self, pid: int, track_id: int = 0, filepath: str = "") -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            if track_id:
                self._db.add_track_to_playlist(pid, track_id=track_id)
            elif filepath:
                self._db.add_track_to_playlist(pid, filepath=filepath)
            else:
                return self._error("NO_TRACK_ID")
            return self._ok()
        except Exception as e:
            return self._error("ADD_TRACK_FAILED", str(e))

    def remove_track(self, pid: int, track_id: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            self._db.remove_track_from_playlist(pid, track_id)
            return self._ok()
        except Exception as e:
            return self._error("REMOVE_TRACK_FAILED", str(e))

    def reorder(self, pid: int, from_index: int, to_index: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            if hasattr(self._db, 'reorder_playlist_track'):
                self._db.reorder_playlist_track(pid, from_index, to_index)
                return self._ok()
            return self._error("UNSUPPORTED")
        except Exception as e:
            return self._error("REORDER_FAILED", str(e))

    def get_detail(self, pid: int) -> dict:
        if not self._can():
            return self._error("NO_DB")
        try:
            items = self._get_items_internal(pid)
            tracks = [
                {
                    "track_id": t.get("track_id", 0),
                    "title": t.get("title", ""),
                    "artist": t.get("artist", ""),
                    "album": t.get("album", ""),
                    "duration": t.get("duration", 0),
                    "position": t.get("position", idx),
                }
                for idx, t in enumerate(items)
            ]
            return self._ok(tracks=tracks, count=len(tracks))
        except Exception as e:
            return self._error("DETAIL_FAILED", str(e))

    def _get_items_internal(self, pid: int) -> list[dict]:
        if not self._can():
            return []
        try:
            items = self._db.get_playlist_items(pid)
            return [
                {
                    "track_id": getattr(item, 'id', 0) if not isinstance(item, dict) else item.get("id", 0),
                    "track_uid": getattr(item, 'track_uid', '') if not isinstance(item, dict) else item.get("track_uid", ''),
                    "filepath": getattr(item, 'filepath', '') if not isinstance(item, dict) else item.get("filepath", ''),
                    "title": getattr(item, 'title', '') if not isinstance(item, dict) else item.get("title", ''),
                    "artist": getattr(item, 'artist', '') if not isinstance(item, dict) else item.get("artist", ''),
                    "album": getattr(item, 'album', '') if not isinstance(item, dict) else item.get("album", ''),
                    "duration": getattr(item, 'duration', 0) if not isinstance(item, dict) else item.get("duration", 0),
                    "position": idx,
                }
                for idx, item in enumerate(items)
            ]
        except Exception:
            return []

    def import_preview(self, filepath: str) -> dict:
        if not filepath or not Path(filepath).is_file():
            return self._error("FILE_NOT_FOUND")
        try:
            from ui.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(filepath)
            valid = sum(1 for e in entries if Path(e.filepath if hasattr(e, 'filepath') else str(e)).is_file())
            return self._ok(
                format=Path(filepath).suffix,
                name=Path(filepath).stem,
                total_entries=len(entries),
                valid_entries=valid,
                missing_entries=len(entries) - valid,
            )
        except Exception as e:
            return self._error("IMPORT_PREVIEW_FAILED", str(e))

    def import_confirm(self, filepath: str, name: str = "") -> dict:
        if not filepath or not Path(filepath).is_file():
            return self._error("FILE_NOT_FOUND")
        if not self._can():
            return self._error("NO_DB")
        try:
            from ui.playlist_io import parse_playlist_entries
            entries = parse_playlist_entries(filepath)
            playlist_name = name or Path(filepath).stem
            pid = self._db.create_playlist(playlist_name)
            count = 0
            for entry in entries:
                fp = entry.filepath if hasattr(entry, 'filepath') else str(entry)
                if Path(fp).is_file():
                    self._db.add_track_to_playlist(pid, filepath=fp)
                    count += 1
            return self._ok(id=pid, count=count, name=playlist_name)
        except Exception as e:
            return self._error("IMPORT_CONFIRM_FAILED", str(e))

    def export(self, pid: int, destination_path: str) -> dict:
        if not destination_path:
            return self._error("EMPTY_PATH")
        if not self._can():
            return self._error("NO_DB")
        try:
            from ui.playlist_io import export_m3u
            items = self._get_items_internal(pid)
            if not items:
                return self._error("NO_TRACKS")
            fps = [t["filepath"] for t in items if t.get("filepath")]
            if not fps:
                return self._error("NO_VALID_TRACKS")
            export_m3u(destination_path, fps)
            return self._ok(count=len(fps))
        except Exception as e:
            return self._error("EXPORT_FAILED", str(e))

    def save_queue(self, player_service, name: str) -> dict:
        if not name or not name.strip():
            return self._error("EMPTY_NAME")
        if not self._can():
            return self._error("NO_DB")
        try:
            fps = []
            if player_service and hasattr(player_service, 'get_queue'):
                q = player_service.get_queue()
                for item in (q or []):
                    fp = getattr(item, 'filepath', None) if not isinstance(item, dict) else item.get("filepath", "")
                    if fp:
                        fps.append(fp)
            if not fps and player_service and hasattr(player_service, 'current'):
                cur = player_service.current
                if cur:
                    fp = getattr(cur, 'filepath', '') if not isinstance(cur, dict) else cur.get("filepath", "")
                    if fp:
                        fps.append(fp)
            if not fps:
                return self._error("NO_TRACKS")
            pid = self._db.create_playlist(name.strip())
            for fp in fps:
                self._db.add_track_to_playlist(pid, filepath=fp)
            return self._ok(id=pid, count=len(fps))
        except Exception as e:
            return self._error("SAVE_QUEUE_FAILED", str(e))
