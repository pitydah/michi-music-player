"""CoverProviderBridge — bounded LRU access to service-backed cover art.

Delegates all cover resolution to CoverArtService (pure domain service).
No direct SQLite connections — the service handles all persistence.
"""
from __future__ import annotations

import base64
import logging
from collections import OrderedDict

from PySide6.QtCore import QObject, Property, Signal, Slot

logger = logging.getLogger("michi.cover_provider")

_MAX_CACHE = 128
_MAX_COVER_BYTES = 10 * 1024 * 1024
_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MISS_TTL_SECONDS = 30  # cache misses expire after 30s
_HIT_TTL_SECONDS = 3600  # cache hits expire after 1 hour


class CoverProviderBridge(QObject):
    coverReady = Signal(str, str)  # cover_key, data_url
    cacheChanged = Signal()

    def __init__(self, artwork_service=None, parent=None):
        super().__init__(parent)
        self._artwork_service = artwork_service
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._cache_expiry: dict[str, float] = {}  # key → expiry timestamp
        self._max_cache = _MAX_CACHE
        self._last_filepath: str = ""

    @Slot(str)
    def setLastFilepath(self, filepath: str) -> None:
        """Store last known filepath for cover resolution fallback."""
        self._last_filepath = filepath or ""

    @Slot(result=str)
    def lastFilepath(self) -> str:
        return self._last_filepath

    def set_filepath(self, fp: str) -> None:
        self._last_filepath = fp or ""

    @Property(int, constant=True)
    def maxCacheSize(self):
        return self._max_cache

    @Property(int, notify=cacheChanged)
    def cacheSize(self):
        return len(self._cache)

    @Slot(str, result=str)
    def getFallbackGlyph(self, album_key: str) -> str:
        compact = "".join(ch for ch in str(album_key or "") if ch.isalnum())
        return (compact[:2] or "MM").upper()

    @Slot(str, result=bool)
    def isCached(self, cover_key: str) -> bool:
        return str(cover_key or "") in self._cache

    @Slot(str, int, result=str)
    def requestCover(self, cover_key: str, requested_size: int = 180) -> str:
        """Return a data URL for ``cover_key`` and cache both hits and misses."""
        del requested_size  # reserved for a future thumbnail provider
        key = str(cover_key or "").strip()
        if not key:
            return ""

        if key in self._cache:
            # Check expiry
            expiry = self._cache_expiry.get(key)
            if expiry is not None and expiry < __import__("time").time():
                # Expired — remove and re-fetch
                self._cache.pop(key, None)
                self._cache_expiry.pop(key, None)
            else:
                value = self._cache.pop(key)
                self._cache[key] = value
                return value

        data_url = self._request_from_service(key)
        self._insert_cache(key, data_url)
        self.coverReady.emit(key, data_url)
        return data_url

    def _request_from_service(self, cover_key: str) -> str:
        service = self._artwork_service
        if service is None:
            return ""
        try:
            mime, data = service.resolve_cover_with_mime(cover_key, filepath=self._last_filepath)
            if not data:
                return ""
            mime = str(mime or "image/jpeg").lower()
            if mime not in _SUPPORTED_MIME:
                mime = "image/jpeg"
            if len(data) > _MAX_COVER_BYTES:
                logger.warning(
                    "Ignoring oversized cover %s (%d bytes)", cover_key, len(data)
                )
                return ""
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception as error:
            logger.debug("Cover service lookup failed for %s: %s", cover_key, error)
            return ""

    def _insert_cache(self, key: str, data_url: str) -> None:
        if key in self._cache:
            self._cache.pop(key)
        self._cache[key] = data_url
        # Set TTL: short for misses, longer for hits
        ttl = _MISS_TTL_SECONDS if not data_url else _HIT_TTL_SECONDS
        self._cache_expiry[key] = __import__("time").time() + ttl
        while len(self._cache) > self._max_cache:
            oldest = next(iter(self._cache))
            self._cache.pop(oldest, None)
            self._cache_expiry.pop(oldest, None)
        self.cacheChanged.emit()

    @Slot(str, result=dict)
    def invalidateCover(self, cover_key: str):
        removed = self._cache.pop(str(cover_key or ""), None) is not None
        if removed:
            self.cacheChanged.emit()
        return {"ok": True, "removed": removed}

    @Slot(result=dict)
    def clearCache(self):
        count = len(self._cache)
        self._cache.clear()
        if count:
            self.cacheChanged.emit()
        return {"ok": True, "cleared": count}

    @Slot(result=dict)
    def cacheStats(self):
        resolved = sum(1 for value in self._cache.values() if value)
        return {
            "ok": True,
            "size": len(self._cache),
            "max": self._max_cache,
            "resolved": resolved,
            "misses": len(self._cache) - resolved,
        }
