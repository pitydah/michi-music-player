"""Library snapshot section — real library counts from the database.

Consumes ``LibraryQueryService`` when available; otherwise derives counts
from the injected database handle. Never fabricates health values: an
unavailable database reports ``available: False`` with a reason.
"""

from __future__ import annotations

from typing import Any


class LibrarySectionProvider:
    section_key = "library"

    def build(self, context) -> dict[str, Any]:
        db = context.db
        if db is None:
            return {
                "available": False,
                "reason": "database_missing",
                "track_count": 0,
                "album_count": 0,
                "artist_count": 0,
                "genre_count": 0,
            }
        try:
            from core.context.context_snapshot import build_library_health_snapshot
            health = build_library_health_snapshot(db)
            health["available"] = True
            health["reason"] = ""
            return health
        except Exception as exc:
            return {
                "available": False,
                "reason": "library_health_failed",
                "error": str(exc)[:200],
                "track_count": 0,
                "album_count": 0,
                "artist_count": 0,
                "genre_count": 0,
            }
