"""CoverArtService — search, download, cache cover art."""
from __future__ import annotations

import logging
import os
from pathlib import Path

logger = logging.getLogger("michi.cover_art")


class CoverArtService:
    def __init__(self, cache_dir: str = ""):
        self._cache_dir = cache_dir or os.path.expanduser(
            "~/.cache/michi-music-player/cover_art")

    def search_cover(self, title: str, artist: str = "", album: str = "") -> dict:
        return {"ok": True, "found": False, "message": "Requires network provider"}

    def download_cover(self, url: str, filepath: str = "") -> dict:
        return {"ok": False, "error": "DEFERRED_PHYSICAL"}

    def get_cached_path(self, album_key: str) -> str | None:
        p = Path(self._cache_dir) / f"{album_key}.jpg"
        return str(p) if p.exists() else None

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
