"""Filesystem store for user-provided playlist cover and hero images."""

import hashlib
import logging
import shutil
from pathlib import Path

from michi.application.ports import PlaylistArtworkStorePort

logger = logging.getLogger(__name__)


def _is_decodable_image(path: Path) -> bool:
    """True only when the file REALLY decodes as an image (KILLCRITIC P1)."""
    try:
        from PySide6.QtGui import QImageReader

        reader = QImageReader(str(path))
        image = reader.read()
        return image is not None and not image.isNull()
    except Exception:  # noqa: BLE001 - validation must never crash
        return False


def _image_edge_exceeds(path: Path, max_edge: int) -> bool:
    try:
        from PySide6.QtGui import QImageReader

        reader = QImageReader(str(path))
        size = reader.size()
        if not size.isValid():
            return False
        return max(size.width(), size.height()) > max_edge
    except Exception:  # noqa: BLE001
        return False


def _content_digest(path: Path) -> str:
    """Deterministic content version for immutable managed filenames."""
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()[:20]


_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# KILLCRITIC hardening: a file must be a REAL decodable image, not just a
# filename with an allowed extension. Bounds protect against garbage and
# pathological resolutions (cover ~4k, hero generous but bounded).
_COVER_MAX_EDGE = 4096
_COVER_MAX_BYTES = 20 * 1024 * 1024
_HERO_MAX_EDGE = 5120
_HERO_MAX_BYTES = 30 * 1024 * 1024


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

    def prepare_cover(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="")

    def prepare_hero(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="_hero")

    def _prepare_variant(
        self, playlist_id: str, source_image_path, *, suffix: str
    ) -> str | None:
        """IMMUTABLE CANDIDATE PROTOCOL:
        1. prepare_* writes a content-versioned FINAL managed file.
        2. only after the file exists may SQLite reference it.
        3. DB failure deletes the new candidate best-effort and keeps old.
        4. DB success makes the new reference authoritative.
        5. old managed asset cleanup is best-effort after commit.
        There is NO post-DB promotion step."""
        src = Path(source_image_path)
        if not src.is_file():
            return None
        ext = src.suffix.lower()
        if ext not in _ALLOWED_EXTENSIONS:
            return None
        max_edge = _COVER_MAX_EDGE if suffix == "" else _HERO_MAX_EDGE
        max_bytes = _COVER_MAX_BYTES if suffix == "" else _HERO_MAX_BYTES
        try:
            if src.stat().st_size == 0:
                return None
            if src.stat().st_size > max_bytes:
                logger.warning(
                    "rejecting oversized playlist asset (%d bytes)", src.stat().st_size
                )
                return None
            # REAL decode validation (KILLCRITIC P1): garbage.jpg must never
            # become a managed cover/hero.
            if not _is_decodable_image(src):
                logger.warning("rejecting non-decodable playlist asset: %s", src)
                return None
            if _image_edge_exceeds(src, max_edge):
                logger.warning("rejecting over-resolution playlist asset: %s", src)
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
