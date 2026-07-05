"""CoverProviderBridge — async cover loading with LRU cache."""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, Signal, Property, Slot

logger = logging.getLogger("michi.cover_provider")

_MAX_CACHE = 500


class CoverProviderBridge(QObject):
    coverReady = Signal(str, str)  # cover_key, data_url_or_path

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db
        self._cache: dict[str, dict] = {}
        self._max_cache = _MAX_CACHE

    @Property(int, constant=True)
    def maxCacheSize(self):
        return self._max_cache

    @Property(int, notify=coverReady)
    def cacheSize(self):
        return len(self._cache)

    @Slot(str, result=str)
    def getFallbackGlyph(self, album_key: str) -> str:
        if not album_key:
            return "MM"
        return album_key[:2].upper()

    @Slot(str, result=bool)
    def isCached(self, cover_key: str) -> bool:
        return cover_key in self._cache

    @Slot(str, int, result=str)
    def requestCover(self, cover_key: str, requested_size: int = 180) -> str:
        if not cover_key:
            return ""
        if cover_key in self._cache:
            cached = self._cache[cover_key]
            if cached.get("data_url"):
                return cached["data_url"]
        # Try DB album_art_cache
        data_url = ""
        if self._db and hasattr(self._db, 'conn'):
            try:
                row = self._db.conn.execute(
                    "SELECT data FROM album_art_cache WHERE album_hash=?",
                    (cover_key,)
                ).fetchone()
                if row and row[0]:
                    import base64
                    data_url = f"data:image/jpeg;base64,{base64.b64encode(row[0]).decode('ascii')}"
            except Exception:
                pass
        self._insert_cache(cover_key, data_url)
        return data_url

    def _insert_cache(self, key: str, data_url: str):
        if len(self._cache) >= self._max_cache:
            oldest = next(iter(self._cache))
            del self._cache[oldest]
        self._cache[key] = {"data_url": data_url, "size": len(data_url)}

    @Slot(str, result=dict)
    def invalidateCover(self, cover_key: str):
        self._cache.pop(cover_key, None)
        return {"ok": True}

    @Slot(result=dict)
    def clearCache(self):
        self._cache.clear()
        return {"ok": True}

    @Slot(result=dict)
    def cacheStats(self):
        return {"ok": True, "size": len(self._cache), "max": self._max_cache}
