"""Texture cache — LRU cache for generated acrylic/noise textures.

Keys are tuples of parameters. Entries expire when the source mtime changes.
"""

from __future__ import annotations

import logging
from collections import OrderedDict

from PySide6.QtGui import QPixmap

logger = logging.getLogger("michi.texture_cache")


class TextureCache:
    def __init__(self, maxsize: int = 64):
        self._maxsize = maxsize
        self._cache: OrderedDict = OrderedDict()

    def get(self, key: tuple) -> QPixmap | None:
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def put(self, key: tuple, pixmap: QPixmap):
        if len(self._cache) >= self._maxsize:
            self._cache.popitem(last=False)
        self._cache[key] = pixmap

    def clear(self):
        self._cache.clear()


texture_cache = TextureCache(maxsize=128)
