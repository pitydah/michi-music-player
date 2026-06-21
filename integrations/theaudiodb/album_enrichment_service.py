"""Album Enrichment Service — queries TheAudioDB for album metadata in background."""
import time

from PySide6.QtCore import QObject, Signal, QTimer

from integrations.theaudiodb.client import TheAudioDBClient
from integrations.theaudiodb.album_cache import AlbumCache
from metadata.album_summary import AlbumSummary

CACHE_DIR = "~/.cache/astra/theaudiodb/albums"


class AlbumEnrichmentService(QObject):
    album_enriched = Signal(str, object)     # album_key, AlbumSummary
    enrichment_failed = Signal(str, str)      # album_key, error
    enrichment_progress = Signal(int, int)    # current, total

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = TheAudioDBClient("2", self)
        self._cache = AlbumCache(self)
        self._pending: list[tuple[str, str, str]] = []
        self._rate_limit = 0.5
        self._last_call = 0.0
        self._enabled = True

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.setInterval(600)

        self._client.artist_found.connect(self._on_album_info)

    def enrich_album(self, album_key: str, artist: str, album: str):
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
        if (album_key, artist, album) not in self._pending:
            self._pending.append((album_key, artist, album))
        if not self._timer.isActive():
            self._timer.start()

    def enrich_visible(self, albums: list, limit: int = 12):
        for a in albums[:limit]:
            self.enrich_album(
                album_key=a.get("key", ""),
                artist=a.get("artist", ""),
                album=a.get("album", ""))

    def _process_queue(self):
        if not self._pending:
            self._timer.stop()
            return
        now = time.time()
        if now - self._last_call < self._rate_limit:
            return

        key, artist, album = self._pending.pop(0)
        self._last_call = time.time()
        self._client.search_artist(artist)
        self._active_key = key
        self._active_album = album
        self.enrichment_progress.emit(
            1, 1 + len(self._pending))

    def _on_album_info(self, info):
        key = getattr(self, '_active_key', None)
        album = getattr(self, '_active_album', None)
        if not key or not info:
            return

        summary = AlbumSummary(
            album_key=key,
            title=album,
            artist=info.name if hasattr(info, 'name') else info.artist_id,
            genre=getattr(info, 'genre', ''),
            style=getattr(info, 'style', ''),
            mood=getattr(info, 'mood', ''),
            description=getattr(info, 'biography_preferred', ''),
            source="theaudiodb",
        )

        # Save to cache
        self._cache.save_metadata(key, {
            "album_key": key, "album": album,
            "artist": summary.artist, "genre": summary.genre,
            "style": summary.style, "mood": summary.mood,
            "description": summary.description,
            "source": "theaudiodb",
        })

        self.album_enriched.emit(key, summary)
