"""Artist Enrichment Service — queries TheAudioDB and updates UI incrementally."""
import os
import time

from PySide6.QtCore import QObject, Signal, QTimer

from integrations.theaudiodb.client import TheAudioDBClient
from integrations.theaudiodb.cache import ArtistCache, IMAGES_DIR
from integrations.theaudiodb.models import ArtistExternalInfo
from library.artist_grouping import ArtistGroup


class ArtistEnrichmentService(QObject):
    artist_enriched = Signal(str, object)      # artist_key, ArtistExternalInfo
    artist_image_loaded = Signal(str, str)     # artist_key, local_path
    enrichment_failed = Signal(str, str)        # artist_key, error
    enrichment_progress = Signal(int, int)      # current, total

    def __init__(self, parent=None):
        super().__init__(parent)
        self._client = TheAudioDBClient("2", self)
        self._cache = ArtistCache(self)
        self._enabled = True
        self._pending: list[str] = []
        self._active = {}
        self._rate_limit = 0.5  # seconds between calls
        self._last_call = 0.0
        self._queued = 0
        self._running = 0

        # Connect client signals (per-request connections in _process_queue)
        self._cache.image_downloaded.connect(self.artist_image_loaded.emit)

        # Rate limit timer
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.setInterval(600)

    def configure(self, api_key: str = "2", enabled: bool = True):
        self._client.set_api_key(api_key)
        self._enabled = enabled

    def enrich_artist(self, group: ArtistGroup):
        if not self._enabled or not group or not group.key:
            return
        key = group.key
        # Check cache first
        cached = self._cache.get_cached_artist(key)
        if cached and not self._cache.is_stale(key):
            info = _dict_to_info(cached)
            if info and info.has_any_data:
                self.artist_enriched.emit(key, info)
                return

        # Queue for API
        if key not in self._active and key not in self._pending:
            self._pending.append(key)
            self._queued += 1
        if not self._timer.isActive():
            self._timer.start()

    def enrich_visible_artists(self, groups: list[ArtistGroup], limit: int = 12):
        for g in groups[:limit]:
            self.enrich_artist(g)

    def refresh_artist(self, artist_key: str):
        self._cache.clear_artist_cache(artist_key)
        # Will re-fetch on next enrich call

    def cancel_pending(self):
        self._pending.clear()
        self._active.clear()
        self._queued = 0
        self._running = 0
        self._timer.stop()

    def clear_cache(self):
        self._cache = ArtistCache(self)

    # ── Internal ──

    def _process_queue(self):
        if not self._pending:
            self._timer.stop()
            return
        now = time.time()
        if now - self._last_call < self._rate_limit:
            return

        key = self._pending.pop(0)
        self._active[key] = True
        self._last_call = time.time()
        self._running += 1
        self.enrichment_progress.emit(self._running, self._running + len(self._pending))

        # Track this key through the response
        self._client.artists_found.connect(
            lambda results, k=key: self._on_search_results_for(k, results))
        self._client.error_occurred.connect(
            lambda msg, k=key: self._on_client_error_for(k, msg))
        self._client.search_artist(key)

    def _on_search_results_for(self, key: str, results: list):
        self._client.artists_found.disconnect()
        self._client.error_occurred.disconnect()
        self._active.pop(key, None)

        if not results:
            self._cache_not_found(key)
            self.enrichment_failed.emit(key, "No encontrado en TheAudioDB")
            return

        best = results[0]
        self._save_and_emit(key, best)

    def _on_client_error_for(self, key: str, msg: str):
        self._client.artists_found.disconnect()
        self._client.error_occurred.disconnect()
        self._active.pop(key, None)
        self.enrichment_failed.emit(key, msg)


    def _save_and_emit(self, key: str, info: ArtistExternalInfo):
        self._cache.save_artist(key, _info_to_dict(info))
        self.artist_enriched.emit(key, info)
        # Download images in background
        if info.thumb_url:
            self._cache.download_image(
                info.thumb_url,
                os.path.join(IMAGES_DIR, f"{key}_thumb.jpg"), key)
        if info.banner_url:
            self._cache.download_image(
                info.banner_url,
                os.path.join(IMAGES_DIR, f"{key}_banner.jpg"), key)
        if info.logo_url:
            self._cache.download_image(
                info.logo_url,
                os.path.join(IMAGES_DIR, f"{key}_logo.png"), key)

    def _cache_not_found(self, key: str):
        self._cache.save_artist(key, {
            "_not_found": True, "_updated": time.time()})
        # Mark as stale later than usual so we don't hammer
        # (handled by is_stale logic)


def _info_to_dict(info: ArtistExternalInfo) -> dict:
    return {k: v for k, v in info.__dict__.items()
            if not k.startswith("_")}


def _dict_to_info(data: dict) -> ArtistExternalInfo | None:
    if data.get("_not_found"):
        return None
    return ArtistExternalInfo(**{
        k: v for k, v in data.items()
        if k in ArtistExternalInfo.__dataclass_fields__})
