"""Library importer — copies processed/ripped tracks to the music library and indexes them."""

from __future__ import annotations

import logging
import os
import re
import shutil
import contextlib

logger = logging.getLogger("michi.library_importer")

_UNSAFE_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')
_PATH_SEP = re.compile(r'\.{2,}|[/\\]{2,}')


def sanitize_filename(name: str) -> str:
    """Remove unsafe characters and path traversal from a path component."""
    name = _UNSAFE_CHARS.sub("_", name)
    name = _PATH_SEP.sub("_", name)
    name = name.strip(". ")
    return name or "unknown"


class LibraryImporter:
    """Copies audio files to the library directory and registers them in the DB."""

    def __init__(self, db=None, base_dir: str = ""):
        self._db = db
        self._base_dir = base_dir or self._default_base_dir()

    def set_base_dir(self, path: str):
        self._base_dir = path

    @property
    def base_dir(self) -> str:
        return self._base_dir

    @staticmethod
    def _default_base_dir() -> str:
        home = os.path.expanduser("~")
        for candidate in ("Música", "Music"):
            d = os.path.join(home, candidate)
            if os.path.isdir(d):
                return os.path.join(d, "Michi")
        return os.path.join(home, "MichiMusic")

    # ── Path building ──

    def build_destination_path(self, metadata: dict, profile: str = "") -> str:
        """Build an Artist/Album/Track - Title.ext path from metadata.

        metadata may contain: artist, albumartist, album, title, tracknumber, ext
        Falls back to 'Unknown' for missing fields.
        """
        artist = sanitize_filename(
            metadata.get("albumartist") or metadata.get("artist") or "Unknown Artist")
        album = sanitize_filename(metadata.get("album") or "Unknown Album")
        track_str = ""
        tn = metadata.get("tracknumber")
        if tn is not None:
            with contextlib.suppress(ValueError, TypeError):
                track_str = f"{int(tn):02d} - "
        title = sanitize_filename(metadata.get("title") or "Untitled")
        ext = metadata.get("ext", "flac").lstrip(".")

        filename = f"{track_str}{title}.{ext}"
        return os.path.join(self._base_dir, artist, album, filename)

    # ── Import ──

    def import_tracks(self, track_files: list[str], metadata: dict,
                      destination: str = "") -> dict:
        """Copy track files to the library directory.

        Returns {"ok": [...], "failed": [{"path":..., "error":...}]}.
        Does not stop on individual failures.
        """
        ok = []
        failed = []
        for src in track_files:
            try:
                if not os.path.isfile(src):
                    raise FileNotFoundError(f"Source not found: {src}")

                ext = os.path.splitext(src)[1]
                meta_copy = dict(metadata)
                meta_copy["ext"] = ext.lstrip(".")
                if "title" not in meta_copy and not destination:
                    meta_copy["title"] = os.path.splitext(os.path.basename(src))[0]

                dest = destination or self.build_destination_path(meta_copy)

                # Resolve name conflicts
                dest = self._unique_path(dest)

                os.makedirs(os.path.dirname(dest), exist_ok=True)
                shutil.copy2(src, dest)
                ok.append(dest)
                logger.debug("Imported %s → %s", src, dest)
            except Exception as e:
                logger.warning("Import failed for %s: %s", src, e)
                failed.append({"path": src, "error": str(e)})
        return {"ok": ok, "failed": failed}

    @staticmethod
    def _unique_path(path: str) -> str:
        """If path exists, append a counter suffix to avoid overwrites."""
        if not os.path.exists(path):
            return path
        base, ext = os.path.splitext(path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{ext}"):
            counter += 1
        return f"{base}_{counter}{ext}"

    # ── Library integration ──

    def add_to_library(self, imported_files: list[str]) -> int:
        """Register imported files in the music library DB.

        Returns number of tracks successfully added.
        """
        if self._db is None:
            logger.warning("add_to_library: no DB connected")
            return 0
        added = 0
        for fp in imported_files:
            try:
                result = self._db.add_file(fp)
                if result is not None:
                    added += 1
            except Exception as e:
                logger.warning("add_to_library failed for %s: %s", fp, e)
        return added

    def refresh_library_index(self, callback=None):
        """Request a library index refresh.

        If callback is provided, calls it. Otherwise returns a status dict.
        """
        if callback:
            try:
                callback()
                return {"status": "ok"}
            except Exception as e:
                return {"status": "error", "detail": str(e)}
        return {"status": "pending", "detail": "No refresh callback configured"}
