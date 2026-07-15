"""AlbumService — business logic for album operations extracted from album_controller."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.album_service")


class AlbumService:
    def __init__(self, db=None, playback_service=None, library_query_service=None):
        self._db = db
        self._playback = playback_service
        self._library_query = library_query_service

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
        if self._library_query:
            try:
                return self._library_query.tracks_for_album(album_key) or []
            except Exception:
                pass
        return []

    def search_cover(self, album_title: str, artist: str = "") -> dict:
        return {"ok": True, "message": "Cover search requires network provider"}

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
