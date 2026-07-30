"""CoverArtService — pure domain service for album artwork resolution.

Resolution chain:
  1. Cache by cover_key (album_art_cache)
  2. Key prefix "track:" → lookup track's album_key → album_art_cache
  3. Key prefix "file:" → embedded cover from file (mutagen)
  4. Sidecar cover in same directory (cover.jpg, folder.jpg, front.png)
  5. Placeholder

Key namespace:
  album:<album_key>   → album_art_cache
  track:<track_uid>   → lookup album_key from media_items
  file:<content_hash> → embedded or sidecar by filepath
"""
from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger("michi.artwork_resolver")

_SUPPORTED_SIDECAR = {"cover.jpg", "cover.png", "folder.jpg", "folder.png",
                      "front.jpg", "front.png", "AlbumArt.jpg", "AlbumArt.png"}


class CoverArtService:
    """Pure domain service for album cover art resolution.

    Full resolution chain with support for album/track/file keys.
    """

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def resolve_cover(self, cover_key: str, filepath: str = "") -> bytes | None:
        """Resolve cover art bytes for a cover key, with filepath fallback."""
        mime, data = self.resolve_cover_with_mime(cover_key, filepath)
        return data

    def resolve_cover_with_mime(self, cover_key: str, filepath: str = "") -> tuple[str | None, bytes | None]:
        """Full resolution chain with MIME type."""
        if not cover_key and not filepath:
            return None, None

        key = str(cover_key or "").strip()

        # Step 1: Try cache by key
        if key and self._db is not None:
            try:
                row = self._db.get_album_art_cache(key)
                if row and row[1]:
                    logger.debug("Cover cache HIT for %s", key)
                    return str(row[0] or "image/jpeg"), bytes(row[1])
            except Exception:
                pass

        # Step 2: Parse key namespace
        if key.startswith("album:") and self._db is not None:
            # Strip prefix and try cache
            actual_key = key[6:]
            try:
                row = self._db.get_album_art_cache(actual_key)
                if row and row[1]:
                    logger.debug("Cover cache HIT (album:) for %s", actual_key)
                    return str(row[0] or "image/jpeg"), bytes(row[1])
            except Exception:
                pass

        elif key.startswith("track:") and self._db is not None:
            # Lookup cover_key from track's album in media_items
            try:
                cursor = self._db.conn.execute(
                    "SELECT m.cover_key FROM media_items m WHERE m.track_uid = ? LIMIT 1",
                    (key[6:],)
                )
                row = cursor.fetchone()
                if row and row[0]:
                    inner = self._db.get_album_art_cache(row[0])
                    if inner and inner[1]:
                        logger.debug("Cover resolved via track→album for %s", key)
                        return str(inner[0] or "image/jpeg"), bytes(inner[1])
            except Exception:
                pass

        # Step 3: Embedded cover from file (mutagen)
        fp = filepath or (key[5:] if key.startswith("file:") else "")
        if fp and os.path.isfile(fp):
            try:
                import mutagen
                audio = mutagen.File(fp)
                if audio is not None:
                    for tag in ("APIC:", "covr", "metadata_block_picture"):
                        pic = audio.get(tag) or (audio.tags.get(tag) if hasattr(audio, 'tags') and audio.tags else None)
                        if pic:
                            if hasattr(pic, 'data'):
                                logger.debug("Cover: embedded in %s", fp)
                                mime = getattr(pic, 'mime', 'image/jpeg') or 'image/jpeg'
                                return str(mime), bytes(pic.data)
                            elif isinstance(pic, bytes):
                                return "image/jpeg", pic
                            elif isinstance(pic, list) and pic:
                                p = pic[0]
                                if hasattr(p, 'data'):
                                    m = getattr(p, 'mime', 'image/jpeg') or 'image/jpeg'
                                    return str(m), bytes(p.data)
                    # APIC in mutagen
                    for t in list(audio.tags.values()) if hasattr(audio, 'tags') and audio.tags else []:
                        if hasattr(t, 'data') and hasattr(t, 'mime'):
                            logger.debug("Cover: APIC from %s", fp)
                            return str(t.mime or 'image/jpeg'), bytes(t.data)
            except Exception as exc:
                logger.debug("Embedded cover read failed for %s: %s", fp, exc)

        # Step 4: Sidecar cover in same directory
        if fp and os.path.isfile(fp):
            basedir = os.path.dirname(os.path.abspath(fp))
            for name in _SUPPORTED_SIDECAR:
                sidecar = os.path.join(basedir, name)
                if os.path.isfile(sidecar):
                    try:
                        with open(sidecar, "rb") as sf:
                            sdata = sf.read()
                        ext = os.path.splitext(name)[1].lower()
                        mime = {"jpg": "image/jpeg", "png": "image/png"}.get(ext, "image/jpeg")
                        logger.debug("Cover: sidecar %s for %s", name, fp)
                        return mime, sdata
                    except Exception:
                        pass

        # Step 5: Placeholder
        return None, None

    def cache_cover(self, album_key: str, data: bytes, mime: str = "image/jpeg") -> bool:
        """Cache cover art bytes for an album key."""
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
