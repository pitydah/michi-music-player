"""Filesystem-based artwork store for user-provided playlist covers."""

import logging
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

    def store_artwork(
        self, playlist_id: str, source_image_path: Path | str
    ) -> str | None:
        """Atomically copies an external image file into managed storage.

        Cleans up any previously stored cover for this playlist with a
        different extension. Returns the string path to the managed copy,
        or None on failure.
        """
        src = Path(source_image_path)
        if not src.is_file():
            return None
        ext = src.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return None

        # Reject zero-byte files
        try:
            if src.stat().st_size == 0:
                return None
        except OSError:
            return None

        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            target_path = self._storage_dir / f"playlist_{playlist_id}{ext}"
            temp_path = self._storage_dir / f"playlist_{playlist_id}.tmp"

            shutil.copyfile(src, temp_path)
            temp_path.replace(target_path)

            # Cleanup candidate files with other extensions
            for other_ext in _ALLOWED_EXTENSIONS:
                if other_ext != ext:
                    old_candidate = (
                        self._storage_dir / f"playlist_{playlist_id}{other_ext}"
                    )
                    if old_candidate.is_file():
                        old_candidate.unlink(missing_ok=True)

            return str(target_path)
        except OSError as exc:
            logger.warning(
                "Failed to store custom cover for playlist %s: %s", playlist_id, exc
            )
            return None

    store_cover = store_artwork

    def delete_cover(self, playlist_id: str) -> None:
        """Removes any stored cover files for the given playlist id."""
        for ext in _ALLOWED_EXTENSIONS:
            candidate = self._storage_dir / f"playlist_{playlist_id}{ext}"
            if candidate.is_file():
                try:
                    candidate.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Failed to delete cover %s: %s", candidate, exc)

    delete_artwork = delete_cover
