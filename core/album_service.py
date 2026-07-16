"""AlbumService — business logic for album operations."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.album_service")


def _album_key(album: str, artist: str) -> str:
    return f"{artist or '?'} / {album or '?'}"


class AlbumService:
    def __init__(self, db=None, playback_service=None, library_query_service=None,
                 worker_manager=None):
        self._db = db
        self._playback = playback_service
        self._library_query = library_query_service
        self._wm = worker_manager

    def _tracks_for_album(self, album_key: str) -> list[dict]:
        if self._library_query:
            try:
                return self._library_query.tracks_for_album(album_key) or []
            except Exception:
                pass
        return []

    def _fetch_album_key(self, title: str, artist: str = "") -> str | None:
        if not self._db:
            return None
        try:
            if artist:
                row = self._db.conn.execute(
                    "SELECT DISTINCT album, artist FROM media_items "
                    "WHERE deleted_at IS NULL AND album=? AND artist=? LIMIT 1",
                    (title, artist)).fetchone()
            else:
                row = self._db.conn.execute(
                    "SELECT DISTINCT album, artist FROM media_items "
                    "WHERE deleted_at IS NULL AND album=? LIMIT 1",
                    (title,)).fetchone()
            if row:
                return _album_key(row[0], row[1] or "")
            return None
        except Exception as e:
            logger.debug("AlbumService._fetch_album_key failed: %s", e)
            return None

    def play_album(self, tracks: list) -> dict:
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._playback and hasattr(self._playback, 'play_list'):
            try:
                self._playback.play_list(tracks)
                return {"ok": True, "count": len(tracks)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def play_next_album(self, current_album_key: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            rows = self._db.conn.execute(
                "SELECT DISTINCT album, artist FROM media_items "
                "WHERE deleted_at IS NULL AND album IS NOT NULL AND album != '' "
                "AND (album || '/' || artist) > ? "
                "ORDER BY album, artist LIMIT 1",
                (current_album_key,)).fetchall()
            if rows:
                ak = _album_key(rows[0][0], rows[0][1] or "")
                tracks = self._tracks_for_album(ak)
                return self.play_album(tracks)
            return {"ok": False, "error": "NO_NEXT_ALBUM"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def queue_album(self, tracks: list) -> dict:
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._playback and hasattr(self._playback, 'add_to_queue'):
            try:
                self._playback.add_to_queue(tracks)
                return {"ok": True, "count": len(tracks)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def get_tracks(self, album_key: str) -> list[dict]:
        return self._tracks_for_album(album_key)

    def create_playlist_from_tracks(self, name: str, tracks: list) -> dict:
        if not self._db or not tracks:
            return {"ok": False, "error": "NO_DB_OR_TRACKS"}
        try:
            pid = self._db.create_playlist(name[:80])
            for t in tracks:
                fp = t.get("filepath", t.get("uri", ""))
                if fp:
                    self._db.add_to_playlist(pid, fp)
            return {"ok": True, "playlist_id": pid, "count": len(tracks)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def search_cover(self, album_title: str, artist: str = "") -> dict:
        return {"ok": True, "message": "Cover search requires network provider",
                "title": album_title, "artist": artist}

    def analyze_album_quality(self, tracks: list) -> dict:
        from audio.quality_classifier import classify_audio_quality
        results = []
        for t in tracks:
            fp = t.get("filepath", t.get("uri", ""))
            if fp and os.path.isfile(fp):
                q = classify_audio_quality(fp)
                results.append({"filepath": fp, "quality": q})
        return {"ok": True, "results": results, "count": len(results)}

    def open_album_folder(self, filepath: str) -> dict:
        folder = os.path.dirname(filepath) if filepath else ""
        if folder and os.path.isdir(folder):
            try:
                import subprocess
                subprocess.Popen(["xdg-open", folder])
                return {"ok": True, "folder": folder}
            except Exception:
                pass
        return {"ok": False, "error": "FOLDER_NOT_FOUND"}

    def tracks_from_group(self, group_id: str) -> list[dict]:
        if not self._db:
            return []
        try:
            rows = self._db.conn.execute(
                "SELECT filepath, title, artist, album FROM media_items "
                "WHERE deleted_at IS NULL AND (album || '/' || artist)=? ORDER BY track_number",
                (group_id,)).fetchall()
            return [{"filepath": r[0], "title": r[1], "artist": r[2], "album": r[3]} for r in rows]
        except Exception:
            return []

    def navigate_to_album_by_title(self, title: str, artist: str = "") -> dict:
        ak = self._fetch_album_key(title, artist)
        if ak:
            return {"ok": True, "album_key": ak}
        return {"ok": False, "error": "ALBUM_NOT_FOUND"}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
