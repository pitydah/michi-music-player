"""Mutagen-based metadata extractor — infrastructure adapter."""

import logging
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.ports import (
    MetadataExtractionError,
    MetadataExtractorPort,
)
from michi.domain.library import TrackMetadata

logger = logging.getLogger(__name__)


class InfrastructureMetadataExtractor(MetadataExtractorPort):
    """Reads title/artist/album/duration from audio tags (Mutagen).

    Fallback contract: untagged/corrupt-tag files yield stem-title, empty
    artist/album and the technical duration when the stream is readable;
    filesystem-level failures (missing/unreadable) raise the typed
    MetadataExtractionError. Never swallows exceptions broadly."""

    def extract(self, file_path: Path) -> TrackMetadata:
        try:
            audio = MutagenFile(str(file_path), easy=True)
        except OSError as exc:
            raise MetadataExtractionError(file_path, str(exc)) from exc
        except MutagenError as exc:
            # mutagen wraps missing-file OSErrors into MutagenError with the
            # original OSError in __context__ — those are filesystem failures.
            if isinstance(exc.__context__, OSError):
                raise MetadataExtractionError(file_path, str(exc)) from exc
            return self._fallback(file_path, duration_ms=0)
        if audio is None:
            return self._fallback(file_path, duration_ms=0)

        tags = audio.tags
        title = self._first(tags, "title") if tags is not None else ""
        artist = self._first(tags, "artist") if tags is not None else ""
        album = self._first(tags, "album") if tags is not None else ""
        genre = self._first(tags, "genre") if tags is not None else ""
        duration_ms = int(audio.info.length * 1000) if audio.info is not None else 0
        return TrackMetadata(
            title=title or file_path.stem,
            artist=artist or "",
            album=album or "",
            duration_ms=duration_ms,
            genre=genre,
        )

    @staticmethod
    def _first(tags, key: str) -> str:
        value = tags.get(key)
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value) if value is not None else ""

    @staticmethod
    def _fallback(file_path: Path, duration_ms: int = 0) -> TrackMetadata:
        return TrackMetadata(title=file_path.stem, duration_ms=duration_ms)
