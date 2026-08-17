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
    """Rich canonical metadata (LOCAL-META-02): musical + technical fields with
    per-field fallbacks; 0/'' = UNKNOWN.

    Fallback contract: untagged/corrupt-tag files yield stem-title, empty
    artist/album and the technical duration when the stream is readable;
    filesystem-level failures (missing/unreadable) raise the typed
    MetadataExtractionError. Never swallows exceptions broadly."""

    def extract(self, file_path: Path) -> TrackMetadata:
        try:
            audio = MutagenFile(str(file_path), easy=True)
            if audio is None:
                return self._fallback(file_path, duration_ms=0)

            tags = audio.tags
            title = self._first(tags, "title") if tags is not None else ""
            artist = self._first(tags, "artist") if tags is not None else ""
            album = self._first(tags, "album") if tags is not None else ""
            genre = self._first(tags, "genre") if tags is not None else ""
            date = self._first(tags, "date") if tags is not None else ""
            year = self._parse_year(date)
            duration_ms = int(audio.info.length * 1000) if audio.info is not None else 0
            album_artist = self._first(tags, "albumartist") if tags is not None else ""
            track_number, track_total = self._parse_track_field(
                self._first(tags, "tracknumber") if tags is not None else ""
            )
            disc_number, disc_total = self._parse_track_field(
                self._first(tags, "discnumber") if tags is not None else ""
            )
            composer = self._first(tags, "composer") if tags is not None else ""
            compilation = self._parse_compilation(
                self._first(tags, "compilation") if tags is not None else ""
            )
            sort_title = self._first(tags, "titlesort") if tags is not None else ""
            sort_artist = self._first(tags, "artistsort") if tags is not None else ""
            sort_album = self._first(tags, "albumsort") if tags is not None else ""
            sort_album_artist = (
                self._first(tags, "albumartistsort") if tags is not None else ""
            )
            info = audio.info
            codec = type(audio).__name__.removeprefix("Easy")
            container = file_path.suffix.lower().lstrip(".")
            sample_rate_hz = info.sample_rate if info is not None else 0
            bit_depth = getattr(info, "bits_per_sample", 0) if info is not None else 0
            channels = info.channels if info is not None else 0
            bitrate_bps = int(info.bitrate or 0) if info is not None else 0
            file_size = file_path.stat().st_size
            return TrackMetadata(
                title=title or file_path.stem,
                artist=artist or "",
                album=album or "",
                duration_ms=duration_ms,
                genre=genre,
                year=year,
                album_artist=album_artist,
                track_number=track_number,
                track_total=track_total,
                disc_number=disc_number,
                disc_total=disc_total,
                composer=composer,
                date=date,
                compilation=compilation,
                sort_title=sort_title,
                sort_artist=sort_artist,
                sort_album=sort_album,
                sort_album_artist=sort_album_artist,
                codec=codec,
                container=container,
                sample_rate_hz=sample_rate_hz,
                bit_depth=bit_depth,
                channels=channels,
                bitrate_bps=bitrate_bps,
                file_size=file_size,
            )
        except OSError as exc:
            raise MetadataExtractionError(file_path, str(exc)) from exc
        except MutagenError as exc:
            # mutagen wraps missing-file OSErrors into MutagenError with the
            # original OSError in __context__ — those are filesystem failures.
            if isinstance(exc.__context__, OSError):
                raise MetadataExtractionError(file_path, str(exc)) from exc
            return self._fallback(file_path, duration_ms=0)

    @staticmethod
    def _first(tags, key: str) -> str:
        value = tags.get(key)
        if isinstance(value, list):
            return str(value[0]) if value else ""
        return str(value) if value is not None else ""

    @staticmethod
    def _parse_year(raw: str) -> int:
        digits = "".join(ch for ch in raw if ch.isdigit())[:4]
        try:
            return int(digits) if len(digits) == 4 else 0
        except ValueError:
            return 0

    @staticmethod
    def _parse_track_field(raw: str) -> tuple[int, int]:
        """'3/12' → (3, 12); '3' → (3, 0); garbage/empty → (0, 0)."""
        raw = raw.strip()
        if not raw:
            return 0, 0
        parts = raw.split("/", 1)
        try:
            number = int(parts[0].strip())
        except ValueError:
            return 0, 0
        total = 0
        if len(parts) == 2:
            try:
                total = int(parts[1].strip())
            except ValueError:
                total = 0
        return number, total

    @staticmethod
    def _parse_compilation(raw: str) -> bool:
        return raw.strip().lower() in {"1", "true", "yes"}

    @staticmethod
    def _fallback(file_path: Path, duration_ms: int = 0) -> TrackMetadata:
        return TrackMetadata(title=file_path.stem, duration_ms=duration_ms)
