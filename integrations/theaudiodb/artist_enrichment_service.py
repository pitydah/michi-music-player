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
        self._active_keys: dict[str, str] = {}  # key → display_name
        self._current_key = ""
        self._rate_limit = 0.5
        self._last_call = 0.0
        self._queued = 0
        self._running = 0

        # Permanent signal connections
        self._client.artists_found.connect(self._on_search_results)
        self._client.error_occurred.connect(self._on_client_error)
        self._cache.image_downloaded.connect(self.artist_image_loaded.emit)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.setInterval(600)

    def configure(self, api_key: str = "2", enabled: bool = True):
        self._client.set_api_key(api_key)
        self._enabled = enabled

    def enrich_artist(self, group, force: bool = False):
        if not self._enabled or not group or not group.key:
            return
        key = group.key
        search_name = group.display_name or group.key

        # Check cache first (unless forced)
        if not force:
            from core.settings_manager import get as sget
            refresh_days = sget("artist_enrichment/refresh_days") or 30
            cached = self._cache.get_cached_artist(key)
            if cached and not self._cache.is_stale(key, days=refresh_days):
                info = _dict_to_info(cached)
                if info and info.has_any_data:
                    self.artist_enriched.emit(key, info)
                    return

        # Queue for API
        if key not in self._active_keys and key not in self._pending:
            self._pending.append(key)
            self._active_keys[key] = search_name
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
        self._active_keys.clear()
        self._current_key = ""
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
        if self._current_key:  # already processing one
            return
        now = time.time()
        if now - self._last_call < self._rate_limit:
            return

        key = self._pending.pop(0)
        search_name = self._active_keys.pop(key, key)
        self._current_key = key
        self._last_call = time.time()
        self._running += 1
        self.enrichment_progress.emit(self._running, self._running + len(self._pending))
        self._client.search_artist(search_name)

    def _on_search_results(self, results: list):
        key = self._current_key
        self._current_key = ""
        if not key:
            return
        if not results:
            self._cache_not_found(key)
            self.enrichment_failed.emit(key, "No encontrado en TheAudioDB")
            return
        best = _pick_best_match(key, results)
        if not best:
            self._cache_not_found(key)
            self.enrichment_failed.emit(key, "Sin coincidencia aceptable")
            return
        self._save_and_emit(key, best)

    def _on_client_error(self, msg: str):
        key = self._current_key
        self._current_key = ""
        if key:
            self.enrichment_failed.emit(key, msg)


    def _save_and_emit(self, key: str, info: ArtistExternalInfo):
        # Set local paths before saving
        thumb_path = os.path.join(IMAGES_DIR, f"{key}_thumb.jpg")
        banner_path = os.path.join(IMAGES_DIR, f"{key}_banner.jpg")
        logo_path = os.path.join(IMAGES_DIR, f"{key}_logo.png")
        info.thumb_path = thumb_path
        info.banner_path = banner_path
        info.logo_path = logo_path

        # Set fanart paths
        fanart_paths = []
        for fi, _url in enumerate(info.fanart_urls[:4]):
            fp = os.path.join(IMAGES_DIR, f"{key}_fanart_{fi}.jpg")
            fanart_paths.append(fp)
        info.fanart_paths = fanart_paths

        self._cache.save_artist(key, _info_to_dict(info))
        self.artist_enriched.emit(key, info)
        # Download images in background
        if info.thumb_url:
            self._cache.download_image(info.thumb_url, thumb_path, key)
        if info.banner_url:
            self._cache.download_image(info.banner_url, banner_path, key)
        if info.logo_url:
            self._cache.download_image(info.logo_url, logo_path, key)
        for fi, url in enumerate(info.fanart_urls[:4]):
            fp = os.path.join(IMAGES_DIR, f"{key}_fanart_{fi}.jpg")
            self._cache.download_image(url, fp, key)

    def _cache_not_found(self, key: str):
        self._cache.save_artist(key, {
            "_not_found": True, "_updated": time.time()})
        # Mark as stale later than usual so we don't hammer
        # (handled by is_stale logic)


def _pick_best_match(key: str, results: list) -> ArtistExternalInfo | None:
    """Pick the best matching result by normalizing and comparing names."""
    import difflib
    target = key.lower().replace("_", " ").strip()
    best = None
    best_score = 0.0
    for r in results:
        name = (getattr(r, 'name', '') or '').lower().strip()
        if name == target:
            return r  # exact match
        score = difflib.SequenceMatcher(None, target, name).ratio()
        if score > best_score:
            best_score = score
            best = r
    if best_score >= 0.82:
        return best
    return None


def _info_to_dict(info: ArtistExternalInfo) -> dict:
    return {k: v for k, v in info.__dict__.items()
            if not k.startswith("_")}


def _dict_to_info(data: dict) -> ArtistExternalInfo | None:
    if data.get("_not_found"):
        return None
    return ArtistExternalInfo(**{
        k: v for k, v in data.items()
        if k in ArtistExternalInfo.__dataclass_fields__})
