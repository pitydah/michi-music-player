"""Filesystem store for user-provided playlist cover and hero images."""

import hashlib
import logging
import shutil
from pathlib import Path

from michi.application.ports import PlaylistArtworkStorePort

logger = logging.getLogger(__name__)


def _content_digest(path: Path) -> str:
    """Deterministic content version for immutable managed filenames."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:20]


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

    # ------------------------------------------------------------------
    # CORRECTIVE SEAL §9 staging protocol: SQLite failure must NEVER alter
    # the previously committed user-visible image.
    #   1. stage: copy NEW bytes to a staging file (committed asset intact)
    #   2. authoritative playlist persist (ref = final stable path)
    #   3. promote: atomically replace the committed asset with the staging
    #      file, then retire superseded old-extension variants
    #   4. discard: remove the staging file on persist failure
    # ------------------------------------------------------------------

    def _stage_variant(
        self, playlist_id: str, source_image_path: Path | str, *, suffix: str
    ) -> str | None:
        """Copies the NEW image to ``{final}.stage``; the committed asset
        is untouched. Returns the FINAL stable path (the durable reference)
        or None on validation failure."""
        src = Path(source_image_path)
        if not src.is_file():
            return None
        ext = src.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return None
        try:
            if src.stat().st_size == 0:
                return None
        except OSError:
            return None
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            stem = f"playlist_{playlist_id}{suffix}"
            final_path = self._storage_dir / f"{stem}{ext}"
            stage_path = self._storage_dir / f"{stem}{ext}.stage"
            shutil.copyfile(src, stage_path)
            return str(final_path)
        except OSError as exc:
            logger.warning(
                "Failed to stage playlist asset for %s: %s", playlist_id, exc
            )
            return None

    def stage_cover(self, playlist_id: str, source_image_path) -> str | None:
        return self._stage_variant(playlist_id, source_image_path, suffix="")

    # ------------------------------------------------------------------
    # P1-06 IMMUTABLE CANDIDATE PROTOCOL: the managed filename embeds a
    # content digest — the candidate file EXISTS (immutable) before any
    # database reference. A crash after commit can only leave an orphaned
    # OLD asset (acceptable cleanup debt); a committed reference can never
    # point to a not-yet-created file.
    # ------------------------------------------------------------------

    def prepare_cover(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="")

    def prepare_hero(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="_hero")

    def _prepare_variant(
        self, playlist_id: str, source_image_path, *, suffix: str
    ) -> str | None:
        src = Path(source_image_path)
        if not src.is_file():
            return None
        ext = src.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return None
        try:
            if src.stat().st_size == 0:
                return None
        except OSError:
            return None
        try:
            self._storage_dir.mkdir(parents=True, exist_ok=True)
            digest = _content_digest(src)
            stem = f"playlist_{playlist_id}{suffix}_{digest}"
            final_path = self._storage_dir / f"{stem}{ext}"
            if final_path.is_file():
                return str(final_path)  # idempotent: same content exists
            temp_path = final_path.with_suffix(final_path.suffix + ".tmp")
            shutil.copyfile(src, temp_path)
            temp_path.replace(final_path)
            return str(final_path)
        except OSError as exc:
            logger.warning(
                "Failed to prepare playlist %s asset for %s: %s",
                suffix or "cover",
                playlist_id,
                exc,
            )
            return None

    def delete_managed_asset(self, managed_path: str) -> None:
        """Fail-closed safe delete: only files inside the managed storage
        directory whose name starts with ``playlist_`` are removed."""
        storage = self._storage_dir.resolve()
        candidate = Path(managed_path).resolve()
        if candidate.parent != storage:
            logger.warning("refusing to delete non-managed asset: %s", managed_path)
            return
        if not candidate.name.startswith("playlist_"):
            logger.warning("refusing to delete non-managed asset: %s", managed_path)
            return
        try:
            candidate.unlink(missing_ok=True)
        except OSError as exc:
            logger.warning("Failed to delete managed asset %s: %s", candidate, exc)

    def stage_hero(self, playlist_id: str, source_image_path) -> str | None:
        return self._stage_variant(playlist_id, source_image_path, suffix="_hero")

    def promote_staged(self, playlist_id: str, *, suffix: str) -> None:
        """Atomically promotes the staged file to the committed asset and
        retires superseded old-extension variants (post-commit only)."""
        stem = f"playlist_{playlist_id}{suffix}"
        promoted_ext = None
        for ext in _ALLOWED_EXTENSIONS:
            stage = self._storage_dir / f"{stem}{ext}.stage"
            final = self._storage_dir / f"{stem}{ext}"
            if stage.is_file():
                try:
                    stage.replace(final)
                except OSError as exc:
                    logger.warning("Promote failed for %s: %s", stage, exc)
                    return
                promoted_ext = ext
                break
        # Retire superseded old-extension variants (post-commit cleanup).
        # ``promoted_ext`` is the EXTENSION THAT WAS PROMOTED — never a
        # re-scan (set iteration order is not an ordering contract).
        if promoted_ext is None:
            return
        for other_ext in _ALLOWED_EXTENSIONS:
            if other_ext == promoted_ext:
                continue
            candidate = self._storage_dir / f"{stem}{other_ext}"
            if candidate.is_file():
                try:
                    candidate.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Post-commit variant cleanup debt: %s", exc)

    def discard_staged(self, playlist_id: str, *, suffix: str) -> None:
        """Removes any staged file (persist failed: committed asset intact)."""
        stem = f"playlist_{playlist_id}{suffix}"
        for ext in _ALLOWED_EXTENSIONS:
            stage = self._storage_dir / f"{stem}{ext}.stage"
            if stage.is_file():
                try:
                    stage.unlink(missing_ok=True)
                except OSError as exc:
                    logger.warning("Discard staged failed for %s: %s", stage, exc)

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
