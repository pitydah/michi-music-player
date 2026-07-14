"""MetadataService — canonical facade for metadata operations in production.

Wraps existing metadata tag_reader/tag_writer/review subsystems behind
a typed API for consumption by MetadataBridge, QML, and future consumers.
"""
from __future__ import annotations

import logging
from pathlib import Path

from metadata.tag_model import TrackTags
from metadata.tag_reader import read_tags
from metadata.tag_writer import write_tags

logger = logging.getLogger("michi.metadata.service")


class MetadataOperationResult:
    def __init__(self, ok: bool = True, code: str = "ok",
                 message: str = "", data: dict | None = None,
                 retryable: bool = False, cancelled: bool = False,
                 partial: bool = False):
        self.ok = ok
        self.code = code
        self.message = message
        self.data = data or {}
        self.retryable = retryable
        self.cancelled = cancelled
        self.partial = partial


class ConfirmationToken:
    def __init__(self, review_id: str, target: str,
                 field_count: int, expiry_s: int = 120):
        self.review_id = review_id
        self.target = target
        self.field_count = field_count
        self.expiry_s = expiry_s
        self.used = False


class MetadataService:
    def __init__(self, library_repo=None, settings_service=None,
                 job_service=None):
        self._library = library_repo
        self._settings = settings_service
        self._jobs = job_service
        self._pending_tokens: dict[str, ConfirmationToken] = {}

    def probe(self, path: str) -> MetadataOperationResult:
        if not path:
            return MetadataOperationResult(ok=False, code="INVALID_PATH")
        p = Path(path)
        if not p.exists():
            return MetadataOperationResult(ok=False, code="FILE_NOT_FOUND")
        if not p.is_file():
            return MetadataOperationResult(ok=False, code="NOT_A_FILE")
        ext = p.suffix.lower().lstrip(".")
        supported = {"mp3", "flac", "ogg", "opus", "m4a", "mp4",
                     "wav", "aiff", "aif", "ape", "wma", "dsf"}
        if ext not in supported:
            return MetadataOperationResult(ok=False, code="UNSUPPORTED_FORMAT")
        return MetadataOperationResult(ok=True, data={"extension": ext})

    def read(self, path: str) -> MetadataOperationResult:
        probe = self.probe(path)
        if not probe.ok:
            return probe
        try:
            tags = read_tags(path)
            if tags is None:
                return MetadataOperationResult(
                    ok=False, code="READ_FAILED",
                    message="Could not read metadata",
                )
            fields = self._tags_to_dict(tags)
            return MetadataOperationResult(
                ok=True, data={"fields": fields, "tags": tags},
            )
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code="READ_FAILED", message=str(e),
            )

    def write(self, path: str, tags: TrackTags) -> MetadataOperationResult:
        if not tags.dirty and not tags.artwork_dirty:
            return MetadataOperationResult(
                ok=False, code="NO_CHANGES",
            )
        try:
            ok = write_tags(tags)
            if not ok:
                return MetadataOperationResult(
                    ok=False, code="WRITE_FAILED",
                    message="Tag writer returned failure",
                    retryable=True,
                )
            verify = self.read(path)
            return MetadataOperationResult(
                ok=True, data={"verify": verify.ok},
            )
        except Exception as e:
            return MetadataOperationResult(
                ok=False, code="WRITE_FAILED", message=str(e),
                retryable=True,
            )

    def create_confirmation_token(self, path: str,
                                  field_count: int) -> str:
        import uuid
        review_id = str(uuid.uuid4())[:8]
        token = ConfirmationToken(
            review_id=review_id, target=path,
            field_count=field_count,
        )
        self._pending_tokens[review_id] = token
        return review_id

    def confirm_and_apply(self, review_id: str,
                          tags: TrackTags) -> MetadataOperationResult:
        token = self._pending_tokens.pop(review_id, None)
        if token is None:
            return MetadataOperationResult(
                ok=False, code="INVALID_TOKEN",
            )
        if token.used:
            return MetadataOperationResult(
                ok=False, code="TOKEN_EXPIRED",
            )
        token.used = True
        return self.write(token.target, tags)

    def inspect_track(self, track_id: int) -> MetadataOperationResult:
        if self._library is None:
            return MetadataOperationResult(
                ok=False, code="LIBRARY_UNAVAILABLE",
            )
        track = self._library.get_track(track_id)
        if track is None:
            return MetadataOperationResult(
                ok=False, code="TRACK_NOT_FOUND",
            )
        filepath = getattr(track, "filepath", "") or getattr(track, "path", "")
        if not filepath:
            return MetadataOperationResult(
                ok=False, code="NO_FILEPATH",
            )
        return self.read(filepath)

    def health(self) -> dict:
        return {
            "available": True,
            "has_library": self._library is not None,
            "has_settings": self._settings is not None,
            "has_job_service": self._jobs is not None,
        }

    def shutdown(self):
        self._pending_tokens.clear()

    @staticmethod
    def _tags_to_dict(tags: TrackTags) -> dict:
        return {
            "title": tags.title,
            "artist": tags.artist,
            "album": tags.album,
            "album_artist": tags.albumartist,
            "genre": tags.genre,
            "year": _parse_year(tags.date),
            "track_number": _parse_int(tags.tracknumber),
            "track_total": _parse_int(tags.tracktotal),
            "disc_number": _parse_int(tags.discnumber),
            "disc_total": _parse_int(tags.disctotal),
            "composer": tags.composer,
            "comment": tags.comment,
            "bpm": _parse_float(tags.bpm),
            "isrc": tags.isrc,
            "lyrics": tags.lyrics,
            "format": tags.kind,
            "bitrate": tags.bitrate,
            "sample_rate": tags.sample_rate,
            "bit_depth": tags.sample_rate,
            "channels": tags.channels,
            "duration": tags.duration,
            "filesize": tags.filesize,
            "has_artwork": tags.has_artwork,
            "musicbrainz_track_id": tags.musicbrainz_trackid,
            "musicbrainz_album_id": tags.musicbrainz_albumid,
            "artwork_mime": tags.artwork_mime,
        }

    @staticmethod
    def _dict_to_tags(data: dict) -> TrackTags:
        tags = TrackTags(filepath=data.get("filepath", ""))
        for key, tag_field in [
            ("title", "title"), ("artist", "artist"),
            ("album", "album"), ("album_artist", "albumartist"),
            ("genre", "genre"), ("year", "date"),
            ("track_number", "tracknumber"), ("track_total", "tracktotal"),
            ("disc_number", "discnumber"), ("disc_total", "disctotal"),
            ("composer", "composer"), ("comment", "comment"),
            ("bpm", "bpm"), ("isrc", "isrc"), ("lyrics", "lyrics"),
            ("musicbrainz_track_id", "musicbrainz_trackid"),
            ("musicbrainz_album_id", "musicbrainz_albumid"),
        ]:
            val = data.get(key)
            if val is not None:
                setattr(tags, tag_field, str(val))
        return tags


def _parse_year(date_str: str) -> int:
    if not date_str:
        return 0
    import re
    m = re.match(r"(\d{4})", date_str)
    return int(m.group(1)) if m else 0


def _parse_int(val: str) -> int:
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


def _parse_float(val: str) -> float:
    try:
        return float(val)
    except (ValueError, TypeError):
        return 0.0
