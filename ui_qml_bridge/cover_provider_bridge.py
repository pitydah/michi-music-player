"""CoverProviderBridge — bounded LRU access to service-backed cover art.

Delegates all cover resolution to CoverArtService (pure domain service).
No direct SQLite connections — the service handles all persistence.

Covers are cached per ``(cover_key, size_bucket)`` so a small thumbnail and a
large hero image do not evict each other. Source images are downscaled to the
requested bucket before encoding to keep memory and data-URL size bounded.
"""
from __future__ import annotations

import base64
import json
import logging
import time
from collections import OrderedDict

from PySide6.QtCore import QBuffer, QByteArray, QIODevice, QObject, Property, Qt, Signal, Slot
from PySide6.QtGui import QImage

logger = logging.getLogger("michi.cover_provider")

_MAX_CACHE = 128
_MAX_COVER_BYTES = 10 * 1024 * 1024
_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}
_MISS_TTL_SECONDS = 30  # cache misses expire after 30s
_HIT_TTL_SECONDS = 3600  # cache hits expire after 1 hour
_SIZE_BUCKETS = (64, 128, 256, 512, 1024)


def _bucket_for(size: int) -> int:
    """Snap a requested pixel size to the nearest upper bucket."""
    requested = max(1, int(size))
    for bucket in _SIZE_BUCKETS:
        if requested <= bucket:
            return bucket
    return _SIZE_BUCKETS[-1]


class CoverProviderBridge(QObject):
    coverReady = Signal(str, str)  # cover_key, data_url
    coverInvalidated = Signal(str)  # cover_key
    cacheChanged = Signal()

    def __init__(self, artwork_service=None, parent=None):
        super().__init__(parent)
        self._artwork_service = artwork_service
        # cover_key -> {bucket: data_url}; outer OrderedDict is the LRU order.
        self._cache: OrderedDict[str, OrderedDict[int, str]] = OrderedDict()
        # (cover_key, bucket) -> expiry timestamp
        self._cache_expiry: dict[tuple[str, int], float] = {}
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
        """Return a data URL for ``cover_key`` and cache both hits and misses.

        The cache is keyed by ``(cover_key, size_bucket)`` so distinct UI sizes
        (thumbnail vs hero) coexist without re-fetching or re-encoding.
        """
        key = str(cover_key or "").strip()
        if not key:
            return ""
        bucket = _bucket_for(requested_size)

        cached = self._cache.get(key)
        if cached is not None and bucket in cached:
            expiry = self._cache_expiry.get((key, bucket))
            if expiry is not None and expiry < time.time():
                self._evict_bucket(key, bucket)
            else:
                value = cached.pop(bucket)
                cached[bucket] = value  # LRU touch within the bucket
                self._cache.pop(key)
                self._cache[key] = cached  # LRU touch the outer entry
                self._thumbnail_references.setdefault(key, set()).add(max(1, requested_size))
                return value

        data_url = self._resolve_for_bucket(key, bucket)
        self._thumbnail_references.setdefault(key, set()).add(max(1, requested_size))
        self._insert_cache(key, bucket, data_url)
        self.coverReady.emit(key, data_url)
        return data_url

    def _request_from_service(self, cover_key: str) -> str:
        """Backward-compatible resolver (largest bucket, no upscaling)."""
        return self._resolve_for_bucket(cover_key, _SIZE_BUCKETS[-1])

    def _resolve_for_bucket(self, cover_key: str, bucket: int) -> str:
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
            resized = self._resize_to_bucket(data, mime, bucket)
            if resized is not None:
                resized_mime, resized_data = resized
                return self._to_data_url(resized_mime, resized_data)
            return self._to_data_url(mime, data)
        except Exception as error:
            logger.debug("Cover service lookup failed for %s: %s", cover_key, error)
            return ""

    @staticmethod
    def _to_data_url(mime: str, data: bytes) -> str:
        encoded = base64.b64encode(data).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    @staticmethod
    def _resize_to_bucket(data: bytes, mime: str, bucket: int) -> tuple[str, bytes] | None:
        """Downscale ``data`` to ``bucket`` px; return (mime, bytes) or None.

        Returns None when the image is already smaller than the bucket or cannot
        be decoded, in which case the caller falls back to the raw bytes.
        """
        image = QImage()
        if not image.loadFromData(data):
            return None
        if max(image.width(), image.height()) <= bucket:
            return None
        scaled = image.scaled(bucket, bucket, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        fmt = "PNG" if mime == "image/png" else "JPG"
        buffer_bytes = QByteArray()
        buffer = QBuffer(buffer_bytes)
        buffer.open(QIODevice.WriteOnly)
        if not scaled.save(buffer, fmt):
            return None
        out_mime = "image/png" if fmt == "PNG" else "image/jpeg"
        return out_mime, bytes(buffer_bytes)

    def _insert_cache(self, key: str, bucket: int, data_url: str) -> None:
        buckets = self._cache.get(key)
        if buckets is None:
            buckets = OrderedDict()
        elif bucket in buckets:
            buckets.pop(bucket)
        buckets[bucket] = data_url
        self._cache[key] = buckets  # (re)insert to refresh LRU position
        ttl = _MISS_TTL_SECONDS if not data_url else _HIT_TTL_SECONDS
        self._cache_expiry[(key, bucket)] = time.time() + ttl
        while len(self._cache) > self._max_cache:
            self._pop_oldest()
        self.cacheChanged.emit()

    def _pop_oldest(self) -> None:
        oldest_key = next(iter(self._cache))
        buckets = self._cache.pop(oldest_key)
        for bucket in list(buckets.keys()):
            self._cache_expiry.pop((oldest_key, bucket), None)
        self._thumbnail_references.pop(oldest_key, None)

    def _evict_bucket(self, key: str, bucket: int) -> None:
        buckets = self._cache.get(key)
        if buckets is not None:
            buckets.pop(bucket, None)
            if not buckets:
                self._cache.pop(key, None)
                self._thumbnail_references.pop(key, None)
        self._cache_expiry.pop((key, bucket), None)

    @Slot(str, result=dict)
    def invalidateCover(self, cover_key: str) -> dict:
        """Invalidate every cached bucket for one cover key."""
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
        buckets = self._cache.pop(key, None)
        if buckets:
            for bucket in list(buckets.keys()):
                self._cache_expiry.pop((key, bucket), None)
        self._thumbnail_references.pop(key, None)
        return buckets is not None

    @Slot(result=dict)
    def clearCache(self) -> dict:
        keys = list(
            dict.fromkeys(
                (*self._cache, *self._thumbnail_references)
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
        resolved = sum(1 for buckets in self._cache.values() if any(buckets.values()))
        return {
            "ok": True,
            "size": len(self._cache),
            "max": self._max_cache,
            "resolved": resolved,
            "misses": len(self._cache) - resolved,
        }
