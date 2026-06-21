"""Artist Enrichment Service — multi-provider: MusicBrainz + Wikipedia + Cover Art Archive."""
import os
import time
import locale

from PySide6.QtCore import QObject, Signal, QTimer

from integrations.theaudiodb.cache import ArtistCache, IMAGES_DIR
from integrations.theaudiodb.models import ArtistExternalInfo
from integrations.musicbrainz.client import MusicBrainzClient
from integrations.wikipedia.client import WikipediaClient


class ArtistEnrichmentService(QObject):
    artist_enriched = Signal(str, object)       # artist_key, ArtistExternalInfo
    artist_image_loaded = Signal(str, str)      # artist_key, local_path
    enrichment_failed = Signal(str, str)         # artist_key, error
    enrichment_progress = Signal(int, int)       # current, total

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mb = MusicBrainzClient(self)
        self._wiki = WikipediaClient(self)
        self._cache = ArtistCache(self)
        self._enabled = True
        self._wiki_lang = "es"
        self._pending: list[str] = []
        self._active_keys: dict[str, str] = {}   # key → display_name
        self._current_key = ""
        self._rate_limit = 1.0                   # MB rate limit: 1/s
        self._last_call = 0.0
        self._queued = 0
        self._running = 0

        # Permanent signal connections
        self._mb.artists_found.connect(self._on_mb_search_results)
        self._mb.artist_found.connect(self._on_mb_artist_result)
        self._mb.error_occurred.connect(self._on_client_error)
        self._wiki.bio_loaded.connect(self._on_bio_loaded)
        self._wiki.image_url_found.connect(self._on_wiki_image)
        self._wiki.error_occurred.connect(lambda e: None)  # non-fatal
        self._cache.image_downloaded.connect(self.artist_image_loaded.emit)

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._process_queue)
        self._timer.setInterval(1100)  # 1.1s for MB rate limit

    def configure(self, api_key: str = "", enabled: bool = True):
        """Configure enrichment. api_key unused for free providers.

        Detects system language for Wikipedia bios.
        """
        self._enabled = enabled
        self._wiki_lang = self._detect_language()

    @staticmethod
    def _detect_language() -> str:
        """Detect system language: settings override, then $LANG, then locale, fallback 'es'."""
        try:
            from core.settings_manager import get as sget
            lang = sget("artist_enrichment/wiki_lang") or ""
            if lang and len(lang) >= 2:
                return lang[:2]
        except Exception:
            pass

        sys_lang = os.environ.get("LANG", "") or locale.getdefaultlocale()[0] or ""
        code = sys_lang[:2] if len(sys_lang) >= 2 else "es"

        valid = {"es", "en", "fr", "de", "pt", "it", "ja", "ru", "zh", "ko",
                 "nl", "pl", "sv", "ar", "tr", "cs", "ca", "eu", "gl"}
        return code if code in valid else "en"

    def enrich_artist(self, group, force: bool = False):
        if not self._enabled or not group or not group.key:
            return
        key = group.key
        search_name = group.display_name or group.key

        # Check cache first (unless forced)
        if not force:
            cached = self._cache.get_cached_artist(key)
            if cached and not self._cache.is_stale(key):
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

    def enrich_visible_artists(self, groups: list, limit: int = 12):
        for g in groups[:limit]:
            self.enrich_artist(g)

    def refresh_artist(self, artist_key: str):
        self._cache.clear_artist_cache(artist_key)

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
        if self._current_key:
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
        self._mb.search_artist(search_name)

    def _on_mb_search_results(self, results: list):
        key = self._current_key
        self._current_key = ""
        if not key:
            return
        if not results:
            self._cache_not_found(key)
            self.enrichment_failed.emit(key, "No encontrado en MusicBrainz")
            return

        info = results[0]
        self._save_and_emit(key, _parse_to_info(info))

        # Fetch bio and image in background
        display_name = info.get("name") or info.get("sort_name") or key
        self._wiki.fetch_bio(key, display_name, self._wiki_lang)
        self._wiki.fetch_image(key, display_name, self._wiki_lang)

    def _on_mb_artist_result(self, info: dict | None):
        key = self._current_key
        self._current_key = ""
        if not key:
            return
        if not info or not info.get("name"):
            self._cache_not_found(key)
            self.enrichment_failed.emit(key, "No encontrado en MusicBrainz")
            return
        self._save_and_emit(key, _parse_to_info(info))

    def _on_bio_loaded(self, artist_key: str, bio: str):
        if not bio:
            return
        cached = self._cache.get_cached_artist(artist_key)
        if cached:
            cached["biography_es"] = bio if self._wiki_lang == "es" else cached.get("biography_es", bio)
            cached["biography_en"] = bio if self._wiki_lang == "en" else cached.get("biography_en", "")
            cached["biography"] = bio
            self._cache.save_artist(artist_key, cached)
            info = _dict_to_info(cached)
            if info:
                self.artist_enriched.emit(artist_key, info)

    def _on_wiki_image(self, artist_key: str, image_url: str):
        if not image_url:
            return
        target = os.path.join(IMAGES_DIR, f"{artist_key}_thumb.jpg")
        self._cache.download_image(image_url, target, artist_key)
        # Also update cached metadata with the URL
        cached = self._cache.get_cached_artist(artist_key)
        if cached:
            cached["thumb_url"] = image_url
            self._cache.save_artist(artist_key, cached)

    def _on_client_error(self, msg: str):
        key = self._current_key
        self._current_key = ""
        if key:
            self.enrichment_failed.emit(key, msg)

    def _save_and_emit(self, key: str, info: ArtistExternalInfo):
        thumb_path = os.path.join(IMAGES_DIR, f"{key}_thumb.jpg")
        banner_path = os.path.join(IMAGES_DIR, f"{key}_banner.jpg")
        logo_path = os.path.join(IMAGES_DIR, f"{key}_logo.png")
        info.thumb_path = thumb_path
        info.banner_path = banner_path
        info.logo_path = logo_path

        fanart_paths = []
        for fi, _url in enumerate((info.fanart_urls or [])[:4]):
            fp = os.path.join(IMAGES_DIR, f"{key}_fanart_{fi}.jpg")
            fanart_paths.append(fp)
        info.fanart_paths = fanart_paths

        self._cache.save_artist(key, _info_to_dict(info))
        self.artist_enriched.emit(key, info)

    def _cache_not_found(self, key: str):
        self._cache.save_artist(key, {
            "_not_found": True, "_updated": time.time()})


def _parse_to_info(data: dict) -> ArtistExternalInfo:
    """Convert MusicBrainz parser dict to ArtistExternalInfo."""
    return ArtistExternalInfo(
        provider=data.get("provider", "musicbrainz"),
        artist_id=data.get("artist_id", ""),
        name=data.get("name", ""),
        mbid=data.get("mbid", ""),
        biography=data.get("biography", ""),
        biography_en=data.get("biography_en", ""),
        biography_es=data.get("biography_es", ""),
        genre=data.get("genre", ""),
        style=data.get("style", ""),
        mood=data.get("mood", ""),
        country=data.get("country", ""),
        formed_year=data.get("formed_year", ""),
        website=data.get("website", ""),
        fanart_urls=data.get("fanart_urls", []),
    )


def _info_to_dict(info: ArtistExternalInfo) -> dict:
    return {k: v for k, v in info.__dict__.items()
            if not k.startswith("_")}


def _dict_to_info(data: dict) -> ArtistExternalInfo | None:
    if data.get("_not_found"):
        return None
    return ArtistExternalInfo(**{
        k: v for k, v in data.items()
        if k in ArtistExternalInfo.__dataclass_fields__})
