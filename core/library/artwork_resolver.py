"""Resolve namespaced cover keys to validated image bytes."""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("michi.artwork_resolver")

MAX_COVER_BYTES = 10 * 1024 * 1024
_SIDECAR_PRIORITY = (
    "cover.jpg",
    "cover.jpeg",
    "cover.png",
    "folder.jpg",
    "folder.jpeg",
    "folder.png",
    "front.jpg",
    "front.jpeg",
    "front.png",
    "albumart.jpg",
    "albumart.jpeg",
    "albumart.png",
)


def _detect_image_mime(data: bytes, declared_mime: str | None = None) -> str:
    """Detect common image formats by signature, then use a declared fallback."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if len(data) >= 12 and data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    return str(declared_mime or "image/jpeg").lower()


class CoverArtService:
    """Resolve album, track, and file cover keys without cross-track state."""

    def __init__(self, db: Any = None) -> None:
        self._db = db

    def resolve_cover(self, cover_key: str, filepath: str = "") -> bytes | None:
        """Resolve cover art bytes for a cover key."""
        _mime, data = self.resolve_cover_with_mime(cover_key, filepath)
        return data

    def resolve_cover_with_mime(
        self,
        cover_key: str,
        filepath: str = "",
    ) -> tuple[str | None, bytes | None]:
        """Resolve a cover and return its detected MIME type and bytes."""
        key = str(cover_key or "").strip()
        if not key and not filepath:
            return None, None

        resolved_filepath = str(filepath or "")
        if key.startswith("album:"):
            cached = self._cached_cover(key[6:])
            if cached:
                return cached
        elif key.startswith("track:"):
            album_key, track_filepath = self._track_artwork_context(key[6:])
            if album_key:
                cached = self._cached_cover(album_key)
                if cached:
                    return cached
            resolved_filepath = resolved_filepath or track_filepath
        elif key.startswith("file:"):
            resolved_filepath = resolved_filepath or key[5:]
        elif key:
            cached = self._cached_cover(key)
            if cached:
                return cached

        embedded = self._embedded_cover(resolved_filepath)
        if embedded:
            return embedded
        sidecar = self._sidecar_cover(resolved_filepath)
        return sidecar if sidecar else (None, None)

    def _validated_cover(
        self,
        data: bytes,
        declared_mime: str | None,
        source: str,
    ) -> tuple[str, bytes] | None:
        if len(data) > MAX_COVER_BYTES:
            logger.warning(
                "Rejecting oversized cover from %s (%d bytes; limit %d)",
                source,
                len(data),
                MAX_COVER_BYTES,
            )
            return None
        return _detect_image_mime(data, declared_mime), data

    def _cached_cover(self, album_key: str) -> tuple[str, bytes] | None:
        if not album_key or self._db is None:
            return None
        try:
            row = self._db.get_album_art_cache(album_key)
        except Exception as exc:
            logger.debug("Cover cache lookup failed for %s: %s", album_key, exc)
            return None
        if not row or not row[1]:
            return None
        data = bytes(row[1])
        validated = self._validated_cover(data, str(row[0] or ""), f"cache:{album_key}")
        if validated:
            logger.debug("Cover cache HIT for %s", album_key)
        return validated

    def _track_artwork_context(self, track_uid: str) -> tuple[str, str]:
        if not track_uid or self._db is None:
            return "", ""
        try:
            row = self._db.conn.execute(
                "SELECT COALESCE(album_key, ''), COALESCE(filepath, '') "
                "FROM media_items WHERE track_uid = ? AND deleted_at IS NULL LIMIT 1",
                (track_uid,),
            ).fetchone()
        except Exception as exc:
            logger.debug("Track artwork lookup failed for %s: %s", track_uid, exc)
            return "", ""
        if not row:
            return "", ""
        return str(row[0] or ""), str(row[1] or "")

    def _embedded_cover(self, filepath: str) -> tuple[str, bytes] | None:
        path = Path(filepath)
        if not filepath or not path.is_file():
            return None
        try:
            import mutagen

            audio = mutagen.File(path)
            if audio is None:
                return None
            tags = getattr(audio, "tags", None)
            for tag in ("APIC:", "covr", "metadata_block_picture"):
                picture = audio.get(tag) or (tags.get(tag) if tags else None)
                resolved = self._picture_bytes(picture, path)
                if resolved:
                    return resolved
            for picture in list(tags.values()) if tags else []:
                resolved = self._picture_bytes(picture, path)
                if resolved:
                    return resolved
        except Exception as exc:
            logger.debug("Embedded cover read failed for %s: %s", path, exc)
        return None

    def _picture_bytes(self, picture: Any, path: Path) -> tuple[str, bytes] | None:
        if isinstance(picture, list):
            picture = picture[0] if picture else None
        if picture is None:
            return None
        raw_data = getattr(picture, "data", picture if isinstance(picture, bytes) else None)
        if not raw_data:
            return None
        data = bytes(raw_data)
        mime = str(getattr(picture, "mime", "") or "")
        validated = self._validated_cover(data, mime, f"embedded:{path}")
        if validated:
            logger.debug("Cover: embedded in %s", path)
        return validated

    def _sidecar_cover(self, filepath: str) -> tuple[str, bytes] | None:
        path = Path(filepath)
        if not filepath or not path.is_file():
            return None
        try:
            entries = {
                candidate.name.lower(): candidate
                for candidate in sorted(path.parent.iterdir(), key=lambda item: item.name.lower())
                if candidate.is_file()
            }
        except OSError as exc:
            logger.debug("Sidecar listing failed for %s: %s", path, exc)
            return None
        for name in _SIDECAR_PRIORITY:
            sidecar = entries.get(name)
            if sidecar is None:
                continue
            try:
                data = sidecar.read_bytes()
            except OSError as exc:
                logger.debug("Sidecar read failed for %s: %s", sidecar, exc)
                continue
            validated = self._validated_cover(data, None, f"sidecar:{sidecar}")
            if validated:
                logger.debug("Cover: sidecar %s for %s", sidecar.name, path)
                return validated
        return None

    def cache_cover(self, album_key: str, data: bytes, mime: str = "image/jpeg") -> bool:
        """Cache validated cover bytes for an album key."""
        if not album_key or not data or self._db is None:
            return False
        validated = self._validated_cover(bytes(data), mime, f"cache-write:{album_key}")
        if not validated:
            return False
        detected_mime, validated_data = validated
        try:
            self._db.conn.execute(
                "INSERT OR REPLACE INTO album_art_cache "
                "(album_hash, mime, data) VALUES (?, ?, ?)",
                (album_key, detected_mime, validated_data),
            )
            self._db.conn.commit()
            return True
        except Exception:
            logger.exception("Failed to cache cover for %s", album_key)
            return False
