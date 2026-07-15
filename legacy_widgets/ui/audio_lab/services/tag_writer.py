"""Tag writer — wrapper around metadata/tag_writer.py for Audio Lab compatibility.

The canonical tag writer is metadata/tag_writer.py.
This module provides a TagWriter class interface for Audio Lab consumers.
"""

from __future__ import annotations

import logging
import os

from metadata.tag_writer import write_tags as _canonical_write

logger = logging.getLogger("michi.tag_writer")
_SUPPORTED = frozenset({".flac", ".mp3", ".ogg", ".oga", ".opus", ".m4a", ".mp4"})


class TagWriter:
    """Tag writer facade for Audio Lab — delegates to metadata/tag_writer.py."""

    def __init__(self):
        self._log = logger

    @property
    def available(self) -> bool:
        return _mutagen_available()

    def read_tags(self, path: str, ext: str | None = None) -> dict:
        ext = ext or os.path.splitext(path)[1].lower()
        if ext not in _SUPPORTED:
            return {}
        result = {}
        try:
            import mutagen
            mf = mutagen.File(path)
            if mf is None or not getattr(mf, 'tags', None):
                return result
            for key, val in mf.tags.items():
                result[key] = str(val[0]) if isinstance(val, list) else str(val)
        except Exception as e:
            logger.warning("Tag read failed for %s: %s", path, e)
        return result

    def write_tags(self, path: str, metadata: dict) -> dict[str, bool | str]:
        if not os.path.isfile(path):
            raise FileNotFoundError("Audio file not found")
        ext = os.path.splitext(path)[1].lower()
        if ext not in _SUPPORTED:
            raise ValueError(f"Unsupported format: {ext}")
        try:
            from metadata.tag_model import TrackTags
            ext = os.path.splitext(path)[1].lower()
            tags = TrackTags(filepath=path, artist=metadata.get("artist", ""),
                             title=metadata.get("title", ""),
                             album=metadata.get("album", ""),
                             albumartist=metadata.get("albumartist", ""),
                             tracknumber=str(metadata.get("tracknumber", metadata.get("track_number", ""))),
                             discnumber=str(metadata.get("discnumber", "")),
                             date=str(metadata.get("year", metadata.get("date", ""))),
                             genre=metadata.get("genre", ""),
                             composer=metadata.get("composer", ""),
                             comment=metadata.get("comment", ""),
                             ext=ext)
            if metadata.get("cover_data"):
                tags.artwork_data = metadata["cover_data"]
                tags.artwork_mime = metadata.get("cover_mime", "image/jpeg")
                tags.has_artwork = True
                tags.artwork_dirty = True
            ok = _canonical_write(tags)
            return {"ok": ok, "error": tags.error if not ok else ""}
        except Exception as e:
            return {"ok": False, "error": str(e)}

    def write_batch(self, paths: list[str], metadata: dict) -> dict:
        """Write metadata to multiple files, returning summary."""
        ok_count = 0
        failed = []
        for path in paths:
            try:
                result = self.write_tags(path, metadata)
                if result.get("ok"):
                    ok_count += 1
                else:
                    failed.append(path)
            except (ValueError, FileNotFoundError):
                failed.append(path)
        return {"ok": ok_count == len(paths), "ok_count": ok_count,
                "failed": failed, "total": len(paths)}

    def embed_cover(self, audio_path: str, cover_path: str) -> dict:
        """Embed a cover art file into an audio file."""
        if not os.path.isfile(audio_path):
            raise FileNotFoundError("Audio file not found")
        ext = os.path.splitext(audio_path)[1].lower()
        if ext not in _SUPPORTED:
            raise ValueError(f"Unsupported format: {ext}")
        if not os.path.isfile(cover_path):
            raise ValueError("Missing cover")
        try:
            with open(cover_path, "rb") as fh:
                data = fh.read()
            mime = "image/jpeg" if cover_path.endswith(".jpg") else "image/png"
            return self.write_tags(audio_path, {"cover_data": data, "cover_mime": mime})
        except OSError as e:
            return {"ok": False, "error": str(e)}

    def refresh_metadata(self, path: str) -> dict:
        ext = os.path.splitext(path)[1].lower()
        return self.read_tags(path, ext)


def _mutagen_available() -> bool:
    try:
        import mutagen  # noqa: F401
        return True
    except ImportError:
        return False
