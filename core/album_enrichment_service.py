"""AlbumEnrichmentService — fetch album metadata and cover from providers."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.album_enrichment")


class AlbumEnrichmentService:
    def __init__(self, db=None):
        self._db = db

    def fetch_metadata(self, album_title: str, artist: str = "") -> dict:
        return {"ok": True, "found": False, "message": "Requires MusicBrainz provider (DEFERRED_PHYSICAL)"}

    def fetch_cover(self, album_title: str, artist: str = "") -> dict:
        return {"ok": True, "found": False, "message": "Requires CoverArtArchive provider (DEFERRED_PHYSICAL)"}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
