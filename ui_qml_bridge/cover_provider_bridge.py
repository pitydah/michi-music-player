"""CoverProviderBridge — bounded LRU access to repository-backed cover art.

The previous bridge delegated to a placeholder QObject and therefore cached an
empty string for every album. This implementation preserves delegation when a
real cover service is injected and otherwise reads the canonical
``album_art_cache`` table using a short-lived read-only SQLite connection.
"""
from __future__ import annotations

import base64
import logging
import sqlite3
from collections import OrderedDict
from pathlib import Path

from PySide6.QtCore import QObject, Property, Signal, Slot

logger = logging.getLogger("michi.cover_provider")

_MAX_CACHE = 128
_MAX_COVER_BYTES = 10 * 1024 * 1024
_SUPPORTED_MIME = {"image/jpeg", "image/png", "image/webp", "image/gif"}


class CoverProviderBridge(QObject):
    coverReady = Signal(str, str)  # cover_key, data_url
    cacheChanged = Signal()

    def __init__(self, cover_bridge=None, parent=None):
        super().__init__(parent)
        self._cover_bridge = cover_bridge
        self._cache: OrderedDict[str, str] = OrderedDict()
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
        del requested_size  # reserved for a future thumbnail provider
        key = str(cover_key or "").strip()
        if not key:
            return ""

        if key in self._cache:
            value = self._cache.pop(key)
            self._cache[key] = value
            return value

        data_url = self._request_from_delegate(key)
        if not data_url:
            data_url = self._request_from_database(key)
        self._insert_cache(key, data_url)
        self.coverReady.emit(key, data_url)
        return data_url

    def _request_from_delegate(self, cover_key: str) -> str:
        delegate = self._cover_bridge
        if delegate is None or not hasattr(delegate, "get_cover_data_url"):
            return ""
        try:
            return str(delegate.get_cover_data_url(cover_key) or "")
        except Exception as error:
            logger.debug("Cover delegate failed for %s: %s", cover_key, error)
            return ""

    def _request_from_database(self, cover_key: str) -> str:
        connection = None
        try:
            from core.paths import database_path

            path = Path(database_path())
            if not path.exists():
                return ""
            uri = f"file:{path.as_posix()}?mode=ro"
            connection = sqlite3.connect(uri, uri=True, timeout=1.0)
            row = connection.execute(
                "SELECT mime, data FROM album_art_cache WHERE album_hash=?",
                (cover_key,),
            ).fetchone()
            if not row or not row[1]:
                return ""
            mime = str(row[0] or "image/jpeg").lower()
            if mime not in _SUPPORTED_MIME:
                mime = "image/jpeg"
            data = bytes(row[1])
            if len(data) > _MAX_COVER_BYTES:
                logger.warning(
                    "Ignoring oversized cover %s (%d bytes)", cover_key, len(data)
                )
                return ""
            encoded = base64.b64encode(data).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception as error:
            logger.debug("Cover database lookup failed for %s: %s", cover_key, error)
            return ""
        finally:
            if connection is not None:
                connection.close()

    def _insert_cache(self, key: str, data_url: str) -> None:
        if key in self._cache:
            self._cache.pop(key)
        self._cache[key] = data_url
        while len(self._cache) > self._max_cache:
            self._cache.popitem(last=False)
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
