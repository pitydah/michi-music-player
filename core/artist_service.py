"""ArtistService — business logic for artist operations extracted from artist_controller."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.artist_service")


class ArtistService:
    def __init__(self, db=None, playback_service=None, library_query_service=None):
        self._db = db
        self._playback = playback_service
        self._library_query = library_query_service

    def play_artist(self, artist_name: str) -> dict:
        tracks = self.get_tracks(artist_name)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._playback and hasattr(self._playback, 'play_list'):
            try:
                self._playback.play_list(tracks)
                return {"ok": True, "count": len(tracks)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def queue_artist(self, artist_name: str) -> dict:
        tracks = self.get_tracks(artist_name)
        if not tracks:
            return {"ok": False, "error": "NO_TRACKS"}
        if self._playback and hasattr(self._playback, 'add_to_queue'):
            try:
                self._playback.add_to_queue(tracks)
                return {"ok": True, "count": len(tracks)}
            except Exception as e:
                return {"ok": False, "error": str(e)}
        return {"ok": False, "error": "SERVICE_UNAVAILABLE"}

    def get_tracks(self, artist_name: str) -> list[dict]:
        if self._library_query:
            try:
                return self._library_query.tracks_for_artist(artist_name) or []
            except Exception:
                pass
        return []

    def get_albums(self, artist_name: str) -> list[dict]:
        if self._library_query:
            try:
                return self._library_query.albums_for_artist(artist_name) or []
            except Exception:
                pass
        return []

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
