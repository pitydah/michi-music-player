"""Filesystem store for user-provided playlist cover and hero images."""

import logging
import shutil
from pathlib import Path

from michi.application.ports import PlaylistArtworkStorePort

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}


class FilesystemPlaylistArtworkStore(PlaylistArtworkStorePort):
    """Manages custom visual files inside the application data directory.

    Existing cover filenames remain unchanged for backward compatibility.
    Hero assets use a separate ``_hero`` suffix so the two user choices
    cannot overwrite each other.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def _store_variant(
        self,
        playlist_id: str,
        source_image_path: Path | str,
        *,
        suffix: str,
    ) -> str | None:
        """Atomically copies an external image file into managed storage.

        Cleans up any previously stored variant for this playlist with a
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
            stem = f"playlist_{playlist_id}{suffix}"
            target_path = self._storage_dir / f"{stem}{ext}"
            temp_path = self._storage_dir / f"{stem}.tmp"

            shutil.copyfile(src, temp_path)
            temp_path.replace(target_path)

            # Cleanup candidate files with other extensions
            for other_ext in _ALLOWED_EXTENSIONS:
                if other_ext != ext:
                    old_candidate = self._storage_dir / f"{stem}{other_ext}"
                    if old_candidate.is_file():
                        old_candidate.unlink(missing_ok=True)

            return str(target_path)
        except OSError as exc:
            logger.warning(
                "Failed to store playlist %s asset for %s: %s",
                suffix or "cover",
                playlist_id,
                exc,
            )
            return None

    def store_cover(
        self, playlist_id: str, source_image_path: Path | str
    ) -> str | None:
        return self._store_variant(playlist_id, source_image_path, suffix="")

    # Compatibility alias retained for the pre-appearance API.
    store_artwork = store_cover

    def store_hero(self, playlist_id: str, source_image_path: Path | str) -> str | None:
        return self._store_variant(playlist_id, source_image_path, suffix="_hero")

    def _delete_variant(self, playlist_id: str, *, suffix: str) -> None:
        stem = f"playlist_{playlist_id}{suffix}"
        for ext in _ALLOWED_EXTENSIONS:
            candidate = self._storage_dir / f"{stem}{ext}"
            if candidate.is_file():
                try:
                    candidate.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Failed to delete artwork %s: %s", candidate, exc)

    def delete_cover(self, playlist_id: str) -> None:
        """Removes any stored cover files for the given playlist id."""
        self._delete_variant(playlist_id, suffix="")

    def delete_hero(self, playlist_id: str) -> None:
        """Removes any stored hero files for the given playlist id."""
        self._delete_variant(playlist_id, suffix="_hero")

    delete_artwork = delete_cover
