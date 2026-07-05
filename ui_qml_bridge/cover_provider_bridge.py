"""CoverProviderBridge — async cover loading with cache."""
from __future__ import annotations

import hashlib
import logging

from PySide6.QtCore import QObject, Signal, Slot

logger = logging.getLogger("michi.cover_provider")

_COVER_CACHE: dict[str, str] = {}
_MAX_CACHE = 500


class CoverProviderBridge(QObject):
    coverReady = Signal(str, str)  # cover_key, filepath_or_data_url

    def __init__(self, db=None, parent=None):
        super().__init__(parent)
        self._db = db

    @Slot(str, result=str)
    def getFallbackGlyph(self, album_key: str) -> str:
        if not album_key:
            return "MM"
        return album_key[:2].upper()

    @Slot(str, result=bool)
    def isCached(self, cover_key: str) -> bool:
        return cover_key in _COVER_CACHE

    def _make_key(self, album_key: str) -> str:
        return hashlib.md5(album_key.encode()).hexdigest()[:16]

    def clear_cache(self):
        _COVER_CACHE.clear()
