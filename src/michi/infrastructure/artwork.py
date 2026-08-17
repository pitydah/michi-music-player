"""Mutagen-based embedded artwork provider + deterministic disk cache."""

import hashlib
import logging
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.ports import ArtworkProviderPort
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
                frame = frames[0]
                return self._guarded(frame.mime, frame.data)

        # FLAC: pictures list on the audio object.
        pictures = getattr(audio, "pictures", None)
        if pictures:
            picture = pictures[0]
            return self._guarded(picture.mime, picture.data)

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


class ArtworkCache:
    """Deterministic, idempotent on-disk cache for album artwork."""

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir

    def store(self, album_key: str, artwork: Artwork) -> Path | None:
        """Persist artwork under a deterministic filename derived from the key.

        Returns the cached path, or None when the artwork is empty/oversized
        and therefore not cacheable. Existing files are returned without
        rewriting (idempotent)."""
        if not artwork.data:
            return None
        if len(artwork.data) > _DEFAULT_MAX_BYTES:
            logger.warning(
                "Artwork for %s exceeds %d bytes; not cacheable",
                album_key,
                _DEFAULT_MAX_BYTES,
            )
            return None
        ext = _EXT_BY_MIME.get(artwork.mime_type, "bin")
        digest = hashlib.sha256(album_key.encode("utf-8")).hexdigest()[:16]
        path = self._cache_dir / f"{digest}.{ext}"
        if path.exists():
            return path
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(artwork.data)
        except OSError as exc:
            logger.warning("Cannot cache artwork %s: %s", path, exc)
            return None
        return path
