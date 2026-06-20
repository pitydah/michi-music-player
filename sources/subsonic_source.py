"""SubsonicSource — wraps SubsonicClient as a MusicSource."""

from sources.base_source import MusicSource, TrackRef
from streaming.subsonic_client import SubsonicClient


class SubsonicSource(MusicSource):
    def __init__(self, client: SubsonicClient):
        self._client = client

    def list_tracks(self) -> list[TrackRef]:
        """List recent tracks from newest albums (first 100 albums' tracks)."""
        refs: list[TrackRef] = []
        try:
            albums = self._client.get_albums()[:100]
            for album in albums:
                for t in self._client.get_album_tracks(album.id):
                    refs.append(TrackRef(
                        uri=self._client.get_stream_url(t.id),
                        title=t.title,
                        artist=t.artist,
                        album=t.album,
                        duration=float(t.duration) if t.duration else 0.0,
                        track_number=t.track,
                        cover_path=(
                            self._client.get_cover_url(album.cover_id, 200)
                            if album.cover_id else ""
                        ),
                    ))
        except Exception:
            import logging
        logging.getLogger("astra").debug("Subsonic source: request failed")
        return refs

    def search(self, query: str) -> list[TrackRef]:
        try:
            resp = self._client._get("search3", {
                "query": query,
                "artistCount": 10,
                "albumCount": 10,
                "songCount": 30,
            })
            sr = resp.get("searchResult3", {})
            refs: list[TrackRef] = []

            for s in sr.get("song", []):
                refs.append(TrackRef(
                    uri=self._client.get_stream_url(s["id"]),
                    title=s.get("title", ""),
                    artist=s.get("artist", ""),
                    album=s.get("album", ""),
                    duration=float(s.get("duration", 0)),
                    track_number=s.get("track", 0),
                    cover_path=(
                        self._client.get_cover_url(s.get("coverArt", ""), 200)
                        if s.get("coverArt") else ""
                    ),
                    genre=s.get("genre", ""),
                ))
            return refs
        except Exception:
            return []

    def list_artists(self) -> list:
        """Expose artists for the remote browser (not part of MusicSource)."""
        try:
            return self._client.get_artists()
        except Exception:
            return []

    def list_albums(self, artist_id: str = None) -> list:
        """Expose albums for the remote browser."""
        try:
            return self._client.get_albums(artist_id)
        except Exception:
            return []

    def list_album_tracks(self, album_id: str) -> list[TrackRef]:
        try:
            return [TrackRef(
                uri=self._client.get_stream_url(t.id),
                title=t.title,
                artist=t.artist,
                album=t.album,
                duration=float(t.duration) if t.duration else 0.0,
                track_number=t.track,
                cover_path=(
                    self._client.get_cover_url(album_id, 200)
                    if album_id else ""
                ),
            ) for t in self._client.get_album_tracks(album_id)]
        except Exception:
            return []

    def can_stream(self, track: TrackRef) -> bool:
        return True
