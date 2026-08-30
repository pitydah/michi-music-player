"""Filesystem store for user-provided playlist cover and hero images."""

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path

from michi.application.ports import PlaylistArtworkStorePort

logger = logging.getLogger(__name__)

_ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}

# KILLCRITIC hardening: a file must be a REAL decodable image, not just a
# filename with an allowed extension. Bounds protect against garbage and
# pathological resolutions.
_COVER_MAX_EDGE = 4096
_COVER_MAX_BYTES = 20 * 1024 * 1024
_COVER_MAX_PIXELS = 20_000_000  # ~20 MP (R2 P1-07 pixel-bomb guard)
_HERO_MAX_EDGE = 5120
_HERO_MAX_BYTES = 30 * 1024 * 1024
_HERO_MAX_PIXELS = 24_000_000  # ~24 MP
_MAX_PIXELS = {
    _COVER_MAX_EDGE: _COVER_MAX_PIXELS,
    _HERO_MAX_EDGE: _HERO_MAX_PIXELS,
}

# R3-01 fail-closed identifier policy: UUIDs and safe names pass; path
# components (/, \, ..) never do.
_SAFE_PLAYLIST_ID_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}")


# Canonical extension per REAL detected format (R2 P1-08): the stored file
# uses the extension of the actual image format, never a misleading suffix.
_CANONICAL_EXTENSION = {
    "png": ".png",
    "jpg": ".jpg",
    "jpeg": ".jpg",
    "webp": ".webp",
}


class _ImageInspection:
    """Outcome of the ordered image inspection (R2 P1-07)."""

    __slots__ = ("ok", "reason", "format", "width", "height", "extension")

    def __init__(self, ok=False, reason="", image_format="", width=0, height=0):
        self.ok = ok
        self.reason = reason
        self.format = image_format
        self.width = width
        self.height = height
        self.extension = _CANONICAL_EXTENSION.get(image_format.lower(), "")


def inspect_image(
    path: Path,
    max_edge: int,
    max_pixels: int,
    check_suffix: bool = True,
    max_bytes: int = 0,
) -> _ImageInspection:
    """ORDERED image validation (R2 P1-07) — every check runs BEFORE the
    framebuffer is allocated:

        1. stat            (zero bytes; byte budget when max_bytes > 0)
        2. allowed suffix   (only for the user-provided SOURCE; the managed
                             temp carries an artificial .tmp suffix and is
                             validated purely by its REAL detected format)
        3. QImageReader + canRead()
        4. reader.format() — REAL detected format
        5. reader.size()   — declared dimensions (no allocation yet)
        6. width/height > 0
        7. max edge
        8. max PIXEL COUNT (pixel-bomb guard)
        9. ONLY NOW reader.read()
       10. !isNull()

    A compressed header declaring gigantic dimensions is rejected at step 8
    — read() is NEVER called for it."""
    if not path.is_file():
        return _ImageInspection(reason="not a file")
    if check_suffix and path.suffix.lower() not in _ALLOWED_EXTENSIONS:
        return _ImageInspection(reason="disallowed extension")
    try:
        size = path.stat().st_size
        if size == 0:
            return _ImageInspection(reason="zero bytes")
        if max_bytes > 0 and size > max_bytes:
            return _ImageInspection(
                reason=f"byte budget exceeded ({size} > {max_bytes})"
            )
    except OSError as exc:
        return _ImageInspection(reason=f"stat failed: {exc}")
    try:
        from PySide6.QtGui import QImageReader

        reader = QImageReader(str(path))
        if not reader.canRead():
            return _ImageInspection(reason="not readable as image")
        image_format = bytes(reader.format()).decode("ascii", "replace").lower()
        canonical = _CANONICAL_EXTENSION.get(image_format)
        if canonical is None:
            return _ImageInspection(
                reason=f"unsupported detected format {image_format}"
            )
        size = reader.size()
        if not size.isValid() or size.width() <= 0 or size.height() <= 0:
            return _ImageInspection(reason="invalid dimensions")
        width, height = size.width(), size.height()
        if max(width, height) > max_edge:
            return _ImageInspection(reason=f"edge {width}x{height} exceeds {max_edge}")
        if width * height > max_pixels:
            return _ImageInspection(
                reason=f"pixel count {width * height} exceeds {max_pixels}"
            )
        image = reader.read()
        if image is None or image.isNull():
            return _ImageInspection(reason="decode produced null image")
    except Exception as exc:  # noqa: BLE001 - validation must never crash
        return _ImageInspection(reason=f"validation error: {exc}")
    return _ImageInspection(
        ok=True,
        image_format=image_format,
        width=width,
        height=height,
    )


class FilesystemPlaylistArtworkStore(PlaylistArtworkStorePort):
    """Manages custom visual files inside the application data directory.

    R2 P2-02: managed assets are IMMUTABLE CONTENT-ADDRESSED candidates —
    ``playlist_<id><role>_<digest><canonical-ext>``. Content changes ⇒
    filename changes ⇒ cache-safe. The legacy deterministic API remains
    only as LEGACY COMPATIBILITY for pinned historical tests.
    """

    def __init__(self, storage_dir: Path) -> None:
        self._storage_dir = storage_dir

    def prepare_cover(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="")

    def prepare_hero(self, playlist_id: str, source_image_path) -> str | None:
        return self._prepare_variant(playlist_id, source_image_path, suffix="_hero")

    def _prepare_variant(
        self, playlist_id: str, source_image_path, *, suffix: str
    ) -> str | None:
        """IMMUTABLE CANDIDATE PROTOCOL (P0-03) with the R2 copy-once-hash
        pipeline (P1-08):

            SOURCE
              → copy ONCE into a unique managed temp WHILE hashing bytes
              → inspect/validate the TEMP (the bytes that will really be
                stored — no TOCTOU on the external source)
              → canonical extension from the REAL detected format
              → os.replace(temp, final)
              → return the immutable candidate

        Digest == the bytes that were actually saved. Any failure removes
        the temp (missing_ok) and NEVER touches the old asset."""
        src = Path(source_image_path)
        if not src.is_file():
            return None
        if src.suffix.lower() not in _ALLOWED_EXTENSIONS:
            return None
        max_edge = _COVER_MAX_EDGE if suffix == "" else _HERO_MAX_EDGE
        max_bytes = _COVER_MAX_BYTES if suffix == "" else _HERO_MAX_BYTES
        try:
            if src.stat().st_size > max_bytes:
                logger.warning(
                    "rejecting oversized playlist asset (%d bytes)",
                    src.stat().st_size,
                )
                return None
            self._storage_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None

        # Copy once into a unique temp while hashing THE STORED BYTES.
        temp_path = (
            self._storage_dir / f".import_{playlist_id}{suffix}_{uuid.uuid4().hex}.tmp"
        )
        digest = hashlib.sha256()
        try:
            with src.open("rb") as source_stream, temp_path.open("wb") as out:
                while True:
                    chunk = source_stream.read(1024 * 1024)
                    if not chunk:
                        break
                    digest.update(chunk)
                    out.write(chunk)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            logger.warning(
                "Failed to copy playlist %s asset for %s: %s",
                suffix or "cover",
                playlist_id,
                exc,
            )
            return None

        # Inspect the TEMP — the exact bytes that will be stored; its
        # artificial .tmp suffix is irrelevant: the REAL detected format
        # decides the canonical stored extension, and the byte budget is
        # enforced on THE STORED BYTES (no source-stat TOCTOU).
        inspection = inspect_image(
            temp_path,
            max_edge,
            _MAX_PIXELS[max_edge],
            check_suffix=False,
            max_bytes=max_bytes,
        )
        if not inspection.ok:
            temp_path.unlink(missing_ok=True)
            logger.warning(
                "rejecting playlist %s asset (%s): %s",
                suffix or "cover",
                src,
                inspection.reason,
            )
            return None

        stem = f"playlist_{playlist_id}{suffix}_{digest.hexdigest()[:20]}"
        final_path = self._storage_dir / f"{stem}{inspection.extension}"
        try:
            if final_path.is_file():
                temp_path.unlink(missing_ok=True)
                return str(final_path)  # idempotent: same content exists
            os.replace(temp_path, final_path)
            return str(final_path)
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            logger.warning(
                "Failed to finalize playlist %s asset for %s: %s",
                suffix or "cover",
                playlist_id,
                exc,
            )
            return None

    def delete_managed_asset(
        self, playlist_id: str, role: str, managed_path: str
    ) -> bool:
        """R3-01 OWNERSHIP-VERIFIED safe delete. Authorizes unlink ONLY
        when EVERY structural fact matches:

            1. path inside the managed storage directory;
            2. playlist_id is a safe identifier (fail-closed policy);
            3. filename belongs EXACTLY to playlist_id;
            4. filename belongs EXACTLY to the requested role
               (cover vs hero are distinguishable);
            5. digest has the canonical 20-hex shape;
            6. extension belongs to the managed format set.

        Returns True when the asset was actually removed. A persisted
        record pointing at ANOTHER playlist's asset (corrupt/tampered DB)
        can never authorize an unlink."""
        storage = self._storage_dir.resolve()
        candidate = Path(managed_path).resolve()
        if candidate.parent != storage:
            logger.warning("refusing to delete non-managed asset: %s", managed_path)
            return False
        if not _SAFE_PLAYLIST_ID_RE.fullmatch(playlist_id):
            logger.warning("refusing delete: unsafe playlist id %r", playlist_id)
            return False
        if role not in ("cover", "hero"):
            logger.warning("refusing delete: unknown role %r", role)
            return False
        suffix = "" if role == "cover" else "_hero"
        # Ownership exacta: prefix = playlist_<id><suffix>_ seguido
        # INMEDIATAMENTE del digest canónico. Un id que contenga "_" o un
        # hero tratado como cover nunca matchean (el digest es inmediato).
        prefix = f"playlist_{playlist_id}{suffix}_"
        if not candidate.name.startswith(prefix):
            logger.warning(
                "refusing delete: %r does not belong to playlist %r (%s)",
                candidate.name,
                playlist_id,
                role,
            )
            return False
        rest = candidate.name[len(prefix) :]
        if re.fullmatch(r"[0-9a-f]{20}\.(png|jpg|webp)", rest) is None:
            logger.warning(
                "refusing delete: filename %r does not match %s ownership "
                "for playlist %r",
                candidate.name,
                role,
                playlist_id,
            )
            return False
        try:
            candidate.unlink(missing_ok=True)
            return True
        except OSError as exc:
            logger.warning("Failed to delete managed asset %s: %s", candidate, exc)
            return False
