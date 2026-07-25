"""CoverArtService — pure domain service for album artwork resolution.

No Qt imports, no QPixmap — works with bytes only.
Reads from album_art_cache through the existing LibraryDB interface.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.artwork_resolver")


class CoverArtService:
    """Pure domain service for album cover art resolution.

    Uses the existing LibraryDB interface (get_album_art_cache) for reads
    and raw SQL for writes. No direct SQLite connections, no QPixmap.
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def resolve_cover(self, album_key: str) -> bytes | None:
        """Resolve cover art bytes for an album key.

        Returns raw image bytes or None when no cover is found.
        """
        if not album_key or self._db is None:
            return None
        try:
            row = self._db.get_album_art_cache(album_key)
            if row:
                return bytes(row[1])
        except Exception:
            logger.exception("Failed to resolve cover for %s", album_key)
        return None

    def resolve_cover_with_mime(self, album_key: str) -> tuple[str | None, bytes | None]:
        """Resolve cover art with its MIME type.

        Returns (mime, data) tuple or (None, None).
        """
        if not album_key or self._db is None:
            return None, None
        try:
            row = self._db.get_album_art_cache(album_key)
            if row:
                return str(row[0] or "image/jpeg"), bytes(row[1])
        except Exception:
            logger.exception("Failed to resolve cover for %s", album_key)
        return None, None

    def cache_cover(self, album_key: str, data: bytes, mime: str = "image/jpeg") -> bool:
        """Cache cover art bytes for an album key.

        Returns True on success, False on failure.
        """
        if not album_key or not data or self._db is None:
            return False
        try:
            self._db.conn.execute(
                "INSERT OR REPLACE INTO album_art_cache "
                "(album_hash, mime, data) VALUES (?, ?, ?)",
                (album_key, mime, data),
            )
            self._db.conn.commit()
            return True
        except Exception:
            logger.exception("Failed to cache cover for %s", album_key)
            return False
