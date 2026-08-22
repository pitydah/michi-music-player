"""Filesystem-based artwork store for user-provided playlist covers."""

import logging
import os
import shutil
from pathlib import Path

from michi.application.ports import PlaylistArtworkStorePort

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FilesystemPlaylistArtworkStore(PlaylistArtworkStorePort):
    """Manages custom cover files copied into the app's managed storage directory.

    Guarantees atomic file copy and safe cleanup.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def store_cover(self, playlist_id: str, source_path: Path | str) -> str | None:
        """Atomically copies an external image file into managed storage.

        Cleans up any previously stored cover for this playlist with a different extension.
        Returns the string path to the managed copy, or None on failure.
        """
        src = Path(source_path)
        if not src.is_file():
            logger.warning("Playlist cover source does not exist: %s", src)
            return None
        ext = src.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            logger.warning("Unsupported playlist cover extension: %s", ext)
            return None

        # Check that file is non-empty
        try:
            if src.stat().st_size == 0:
                logger.warning("Playlist cover source is empty: %s", src)
                return None
        except OSError as exc:
            logger.warning("Could not read playlist cover stat %s: %s", src, exc)
            return None

        target = self._storage_dir / f"playlist_{playlist_id}{ext}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            tmp = target.with_suffix(target.suffix + ".tmp")
            shutil.copyfile(src, tmp)
            os.replace(tmp, target)

            # Clean up other extensions for this playlist
            for other_ext in _ALLOWED_EXTENSIONS:
                if other_ext != ext:
                    old_candidate = self._storage_dir / f"playlist_{playlist_id}{other_ext}"
                    if old_candidate.is_file():
                        old_candidate.unlink(missing_ok=True)

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
