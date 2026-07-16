"""ArtistEnrichmentService — fetch artist image, biography, aliases."""
from __future__ import annotations

import logging

logger = logging.getLogger("michi.artist_enrichment")


class ArtistEnrichmentService:
    def __init__(self, db=None):
        self._db = db

    def fetch_image(self, artist_name: str) -> dict:
        return {"ok": True, "found": False, "message": "Requires provider (DEFERRED_PHYSICAL)"}

    def fetch_biography(self, artist_name: str) -> dict:
        return {"ok": True, "found": False, "message": "Requires provider (DEFERRED_PHYSICAL)"}

    def resolve_aliases(self, artist_name: str) -> dict:
        return {"ok": True, "aliases": [artist_name], "message": "Local only"}

    def health(self) -> dict:
        return {"available": True}

    def shutdown(self):
        pass
