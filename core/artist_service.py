"""ArtistService — business logic for artist operations."""
from __future__ import annotations

import logging
import os

logger = logging.getLogger("michi.artist_service")


class ArtistService:
    def __init__(self, db=None, playback_service=None, library_query_service=None,
                 worker_manager=None):
        self._db = db
        self._playback = playback_service
        self._library_query = library_query_service
        self._wm = worker_manager

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

    def create_playlist_from_artist(self, artist_name: str) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            tracks = self.get_tracks(artist_name)
            if not tracks:
                return {"ok": False, "error": "NO_TRACKS"}
            pid = self._db.create_playlist(f"{artist_name[:60]} - All")
            for t in tracks:
                fp = t.get("filepath", t.get("uri", ""))
                if fp:
                    self._db.add_to_playlist(pid, fp)
            return {"ok": True, "playlist_id": pid, "count": len(tracks)}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def create_artist_mix(self, artist_name: str, limit: int = 30) -> dict:
        if not self._db:
            return {"ok": False, "error": "NO_DB"}
        try:
            tracks = self.get_tracks(artist_name)
            if not tracks:
                return {"ok": False, "error": "NO_TRACKS"}
            import random
            sample = random.sample(tracks, min(limit, len(tracks)))
            return {"ok": True, "tracks": sample, "count": len(sample),
                    "title": f"{artist_name} Mix"}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def analyze_artist_discography(self, artist_name: str) -> dict:
        from audio.quality_classifier import classify_audio_quality
        tracks = self.get_tracks(artist_name)
        results = []
        for t in tracks:
            fp = t.get("filepath", t.get("uri", ""))
            if fp and os.path.isfile(fp):
                q = classify_audio_quality(fp)
                results.append({"filepath": fp, "quality": q})
        return {"ok": True, "results": results, "count": len(results)}

    def resolve_artist_aliases(self, artist_name: str) -> list[str]:
        return [artist_name]

    def health(self) -> dict:
        return {"available": self._db is not None}

    def shutdown(self):
        pass
