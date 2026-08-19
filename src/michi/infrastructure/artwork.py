"""Mutagen-based embedded artwork provider + deterministic disk cache."""

import hashlib
import logging
import os
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.ports import ArtworkCachePort, ArtworkProviderPort
from michi.domain.library import Artwork

logger = logging.getLogger(__name__)

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024

_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
}


class MutagenArtworkProvider(ArtworkProviderPort):
    """Reads embedded cover art from media files via mutagen.

    Contract: artwork absence is NOT an error. Untagged files, unknown
    formats, corrupt files and unreadable/missing files all yield ``None``
    (logged, never raised). Oversized artwork is also discarded (not
    cacheable)."""

    def __init__(self, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        self._max_bytes = max_bytes

    # M6.5: deterministic local artwork fallback — fixed, ordered candidate
    # names (cover.* then folder.* then front.*). No arbitrary directory
    # scanning: only these names are ever considered.
    _LOCAL_ARTWORK_FILES = (
        "cover.jpg",
        "cover.jpeg",
        "cover.png",
        "folder.jpg",
        "folder.png",
        "front.jpg",
        "front.png",
    )
    _LOCAL_ARTWORK_MIME = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    def get_embedded_artwork(self, file_path: Path) -> Artwork | None:
        try:
            audio = MutagenFile(str(file_path))
        except OSError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        except MutagenError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        if audio is None:
            return None

        # MP3/ID3: APIC frames on the tag object. Corrupt MP3s still parse
        # into an MP3 object whose tags attribute is None — guard attribute
        # access instead of assuming tags always exist.
        tags = getattr(audio, "tags", None)
        if tags is not None and hasattr(tags, "getall"):
            frames = tags.getall("APIC")
            if frames:
                # M6.5: prefer the FIRST frame designated as the FRONT COVER
                # (type 3); fall back to the first frame when no front-cover
                # designation exists.
                frame = next(
                    (f for f in frames if getattr(f, "type", None) == 3),
                    frames[0],
                )
                return self._guarded(frame.mime, frame.data)

        # FLAC: pictures list on the audio object.
        pictures = getattr(audio, "pictures", None)
        if pictures:
            # M6.5: same front-cover (type 3) preference as APIC.
            picture = next(
                (p for p in pictures if getattr(p, "type", None) == 3),
                pictures[0],
            )
            return self._guarded(picture.mime, picture.data)

        return None

    def get_embedded_front_artwork(self, file_path: Path) -> Artwork | None:
        """EXPLICIT front-cover artwork only (M6-PRODUCTION-INTEGRATION):
        APIC/picture frames designated type 3 (front cover); anything else
        yields None so the album-level two-pass resolution can prefer a real
        front cover from ANY track before falling back to any embedded art."""
        try:
            audio = MutagenFile(str(file_path))
        except OSError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        except MutagenError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        if audio is None:
            return None
        tags = getattr(audio, "tags", None)
        if tags is not None and hasattr(tags, "getall"):
            frames = tags.getall("APIC")
            frame = next((f for f in frames if getattr(f, "type", None) == 3), None)
            if frame is not None:
                return self._guarded(frame.mime, frame.data)
        pictures = getattr(audio, "pictures", None)
        if pictures:
            picture = next((p for p in pictures if getattr(p, "type", None) == 3), None)
            if picture is not None:
                return self._guarded(picture.mime, picture.data)
        return None

    def get_local_artwork(self, album_dir: Path) -> Artwork | None:
        """Deterministic local artwork fallback (M6.5): cover.* then
        folder.* then front.*, case-insensitive, in the album directory.
        Unreadable/over-max entries are skipped; no arbitrary scanning."""
        for name in self._LOCAL_ARTWORK_FILES:
            candidate = album_dir / name
            if not candidate.is_file():
                # case-insensitive fallback
                lowered = name.lower()
                found = None
                try:
                    for entry in album_dir.iterdir():
                        if entry.is_file() and entry.name.lower() == lowered:
                            found = entry
                            break
                except OSError:
                    continue
                candidate = found
            if candidate is None:
                continue
            try:
                data = candidate.read_bytes()
            except OSError:
                continue
            if len(data) > self._max_bytes:
                continue
            mime = self._LOCAL_ARTWORK_MIME.get(candidate.suffix.lower(), "")
            if not mime:
                continue
            return Artwork(data=data, mime_type=mime)
        return None

    def _guarded(self, mime: str, data: bytes) -> Artwork | None:
        if len(data) > self._max_bytes:
            logger.warning(
                "Artwork in %s exceeds %d bytes; not cacheable",
                mime,
                self._max_bytes,
            )
            return None
        return Artwork(data=data, mime_type=mime)


class ArtworkCache(ArtworkCachePort):
    """Deterministic, idempotent on-disk cache for album artwork.

    Implements :class:`michi.application.ports.ArtworkCachePort` — the
    application layer depends on the port, infrastructure owns the disk."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def store(self, album_key: str, artwork: Artwork) -> Path | None:
        """Deterministic content-digest-aware store (M6.5): the filename
        derives from sha256(album_key + sha256(data)) so CHANGED artwork
        produces a NEW entry (active on rescan) while unchanged content
        keeps the same path — exists -> return, no rewrite. Old entries
        stay on disk (stale-aware; garbage collection is a later phase).

        Returns the cached path, or None when the artwork is empty/oversized
        and therefore not cacheable."""
        if not artwork.data:
            return None
        if len(artwork.data) > _DEFAULT_MAX_BYTES:
            logger.warning(
                "Artwork for %s exceeds %d bytes; not cacheable",
                album_key,
                _DEFAULT_MAX_BYTES,
            )
            return None
        content_digest = hashlib.sha256(artwork.data).hexdigest()
        key_digest = hashlib.sha256(
            (album_key + content_digest).encode("utf-8")
        ).hexdigest()[:16]
        ext = _EXT_BY_MIME.get(artwork.mime_type, "bin")
        target = self._cache_dir / f"{key_digest}.{ext}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                return target  # idempotent: no rewrite for unchanged content
            tmp = target.with_suffix(target.suffix + ".tmp")
            tmp.write_bytes(artwork.data)
            os.replace(tmp, target)  # atomic-ish replace
        except OSError as exc:
            logger.warning("Cannot cache artwork %s: %s", target, exc)
            return None
        return target
