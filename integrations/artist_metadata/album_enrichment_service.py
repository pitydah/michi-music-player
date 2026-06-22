"""Album Enrichment Service — queries MusicBrainz + Cover Art Archive for album data."""
import time
import os

from PySide6.QtCore import QObject, Signal, QTimer

from integrations.musicbrainz.client import MusicBrainzClient
from integrations.coverart.client import CoverArtClient
from integrations.artist_metadata.album_cache import AlbumCache
from metadata.album_summary import AlbumSummary

CACHE_DIR = os.path.expanduser("~/.cache/astra/artist_metadata/albums")


class AlbumEnrichmentService(QObject):
    album_enriched = Signal(str, object)     # album_key, AlbumSummary
    enrichment_failed = Signal(str, str)      # album_key, error
    enrichment_progress = Signal(int, int)    # current, total

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = MusicBrainzClient(self)
        self._cover = CoverArtClient(self)
        self._cache = AlbumCache(self)
        self._pending: list[tuple[str, str, str, str]] = []
        self._rate_limit = 1.0
        self._last_call = 0.0
        self._enabled = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.setInterval(600)

        self._client.artists_found.connect(self._on_album_info)
        self._client.albums_found.connect(self._on_release_groups)
        self._client.error_occurred.connect(self._on_error)
        self._cover.cover_found.connect(self._on_cover_found)

    def enrich_album(self, album_key: str, artist: str, album: str, mbid: str = ""):
        if not self._enabled or not artist or not album:
            return
        if not self._cache.is_stale(album_key, days=30):
            cached = self._cache.get_metadata(album_key)
            if cached:
                from metadata.album_info_repository import _dict_to_summary
                s = _dict_to_summary(cached)
                if s:
                    self.album_enriched.emit(album_key, s)
                    return
        if (album_key, artist, album, mbid) not in self._pending:
            self._pending.append((album_key, artist, album, mbid))
        if not self._timer.isActive():
            self._timer.start()

    def enrich_visible(self, albums: list, limit: int = 12):
        for a in albums[:limit]:
            self.enrich_album(
                album_key=a.get("key", ""),
                artist=a.get("artist", ""),
                album=a.get("album", ""),
                mbid=a.get("mbid", ""))

    def _process_queue(self):
        if not self._pending:
            self._timer.stop()
            return
        now = time.time()
        if now - self._last_call < self._rate_limit:
            return

        key, artist, album, mbid = self._pending.pop(0)
        self._last_call = time.time()
        self._active_key = key
        self._active_album = album

        if mbid:
            self._client.get_release_groups(mbid)
        else:
            self._client.search_artist(artist)
        self.enrichment_progress.emit(1, 1 + len(self._pending))

    def _on_album_info(self, results):
        key = getattr(self, '_active_key', None)
        album = getattr(self, '_active_album', None)
        if not key or not album or not results:
            return
        info = results[0] if isinstance(results, list) and results else None
        if not info:
            return
        name = info.get("name", "")
        genre = info.get("genre", "")

        summary = AlbumSummary(
            album_key=key,
            title=album,
            artist=name,
            genre=genre,
            style=info.get("style", ""),
            mood=info.get("mood", ""),
            description="",
            source="musicbrainz",
        )

        self._cache.save_metadata(key, {
            "album_key": key, "album": album,
            "artist": name, "genre": genre,
            "style": info.get("style", ""), "mood": info.get("mood", ""),
            "description": "",
            "source": "musicbrainz",
        })

        self.album_enriched.emit(key, summary)

    def _on_release_groups(self, release_groups: list):
        key = getattr(self, '_active_key', None)
        if not key or not release_groups:
            return
        # Emit basic summary with release-group data
        for rg in release_groups[:5]:
            rg_mbid = rg.get("id", "")
            rg_title = rg.get("title", "")
            if rg_mbid:
                rg_key = f"{key}_{rg_mbid[:8]}"
                summary = AlbumSummary(
                    album_key=rg_key,
                    title=rg_title,
                    artist=self._active_album or "",
                    genre="",
                    source="musicbrainz",
                )
                self.album_enriched.emit(rg_key, summary)
                # Fetch cover art for this release-group
                self._cover.fetch_cover(rg_key, rg_mbid)

    def _on_cover_found(self, album_key: str, image_url: str):
        if not image_url:
            return
        # Store cover URL in cache
        cached = self._cache.get_metadata(album_key)
        cover_data = cached or {}
        cover_data["album_key"] = album_key
        cover_data["cover_url"] = image_url
        cover_data["source"] = "coverartarchive"
        self._cache.save_metadata(album_key, cover_data)
        # Re-emit with cover URL
        from metadata.album_info_repository import _dict_to_summary
        s = _dict_to_summary(cover_data)
        if s:
            self.album_enriched.emit(album_key, s)

    def _on_error(self, msg):
        key = getattr(self, '_active_key', None)
        if key:
            self.enrichment_failed.emit(key, msg)
