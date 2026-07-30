"""CoverProviderBridge — bounded LRU access to service-backed cover art.

Delegates all cover resolution to CoverArtService (pure domain service).
No direct SQLite connections — the service handles all persistence.
"""
from __future__ import annotations

import base64
import json
import logging
import time
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
    coverInvalidated = Signal(str)  # cover_key
    cacheChanged = Signal()

    def __init__(self, artwork_service=None, parent=None):
        super().__init__(parent)
        self._artwork_service = artwork_service
        self._cache: OrderedDict[str, str] = OrderedDict()
        self._cache_expiry: dict[str, float] = {}  # key → expiry timestamp
        self._thumbnail_references: dict[str, set[int]] = {}
        self._max_cache = _MAX_CACHE

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
        key = str(cover_key or "").strip()
        if not key:
            return ""

        if key in self._cache:
            # Check expiry
            expiry = self._cache_expiry.get(key)
            if expiry is not None and expiry < time.time():
                # Expired — remove and re-fetch
                self._cache.pop(key, None)
                self._cache_expiry.pop(key, None)
                self._thumbnail_references.pop(key, None)
            else:
                value = self._cache.pop(key)
                self._cache[key] = value
                self._thumbnail_references.setdefault(key, set()).add(
                    max(1, requested_size)
                )
                return value

        data_url = self._request_from_service(key)
        self._thumbnail_references.setdefault(key, set()).add(max(1, requested_size))
        self._insert_cache(key, data_url)
        self.coverReady.emit(key, data_url)
        return data_url

    def _request_from_service(self, cover_key: str) -> str:
        service = self._artwork_service
        if service is None:
            return ""
        try:
            mime, data = service.resolve_cover_with_mime(cover_key)
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
        self._cache_expiry[key] = time.time() + ttl
        while len(self._cache) > self._max_cache:
            oldest = next(iter(self._cache))
            self._cache.pop(oldest, None)
            self._cache_expiry.pop(oldest, None)
            self._thumbnail_references.pop(oldest, None)
        self.cacheChanged.emit()

    @Slot(str, result=dict)
    def invalidateCover(self, cover_key: str) -> dict:
        """Invalidate every cached reference for one cover key."""
        key = str(cover_key or "").strip()
        removed = self._invalidate_key(key)
        if key:
            self.cacheChanged.emit()
            self.coverInvalidated.emit(key)
        return {"ok": True, "removed": removed}

    @Slot(str, result=dict)
    def invalidateMany(self, keys_json: str) -> dict:
        """Invalidate a JSON array of cover keys in one cache notification."""
        try:
            raw_keys = json.loads(str(keys_json or ""))
        except (TypeError, ValueError, json.JSONDecodeError):
            return {
                "ok": False,
                "invalidated": 0,
                "removed": 0,
                "error": "invalid_json",
            }
        if not isinstance(raw_keys, list):
            return {
                "ok": False,
                "invalidated": 0,
                "removed": 0,
                "error": "invalid_json",
            }

        keys = list(
            dict.fromkeys(str(raw_key or "").strip() for raw_key in raw_keys)
        )
        keys = [key for key in keys if key]
        removed = sum(self._invalidate_key(key) for key in keys)
        if keys:
            self.cacheChanged.emit()
            for key in keys:
                self.coverInvalidated.emit(key)
        return {"ok": True, "invalidated": len(keys), "removed": removed}

    def _invalidate_key(self, key: str) -> bool:
        if not key:
            return False
        had_cache = key in self._cache
        had_expiry = key in self._cache_expiry
        had_thumbnail = key in self._thumbnail_references
        self._cache.pop(key, None)
        self._cache_expiry.pop(key, None)
        self._thumbnail_references.pop(key, None)
        return had_cache or had_expiry or had_thumbnail

    @Slot(result=dict)
    def clearCache(self) -> dict:
        keys = list(
            dict.fromkeys(
                (*self._cache, *self._cache_expiry, *self._thumbnail_references)
            )
        )
        count = len(self._cache)
        self._cache.clear()
        self._cache_expiry.clear()
        self._thumbnail_references.clear()
        if keys:
            self.cacheChanged.emit()
            for key in keys:
                self.coverInvalidated.emit(key)
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
