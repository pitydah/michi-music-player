"""Filesystem-based artwork store for user-provided playlist covers."""

import logging
import os
import shutil
from pathlib import Path

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FilesystemPlaylistArtworkStore:
    """Manages custom cover files copied into the app's managed storage directory.

    Guarantees atomic file copy and safe cleanup.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def store_cover(self, playlist_id: str, source_path: Path) -> str | None:
        """Atomically copies an external image file into managed storage.

        Returns the string path to the managed copy, or None on failure.
        """
        if not source_path.is_file():
            logger.warning("Playlist cover source does not exist: %s", source_path)
            return None
        ext = source_path.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            logger.warning("Unsupported playlist cover extension: %s", ext)
            return None

        target = self._storage_dir / f"playlist_{playlist_id}{ext}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(source_path, tmp)
            os.replace(tmp, target)
            return str(target)
        except OSError as exc:
            logger.warning(
                "Failed to store custom cover for playlist %s: %s", playlist_id, exc
            )
            return None

    def delete_cover(self, playlist_id: str) -> None:
        """Removes any stored cover files for the given playlist id."""
        for ext in _ALLOWED_EXTENSIONS:
            candidate = self._storage_dir / f"playlist_{playlist_id}{ext}"
            if candidate.is_file():
                try:
                    candidate.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Failed to delete cover %s: %s", candidate, exc)
