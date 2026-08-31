"""Filesystem store for user-provided playlist cover and hero images."""

import hashlib
import logging
import os
import re
import uuid
from pathlib import Path

from michi.application.playlist_asset_contract import PreparedPlaylistAsset
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

# R4-06: el filename V2 NUNCA contiene el playlist_id raw — el owner se
# codifica como token hash inequívoco (elimina colisiones tipo
# "abc" vs "abc_hero").
_V2_ASSET_RE = re.compile(
    r"playlist_v2_([0-9a-f]{20})_(cover|hero)_([0-9a-f]{20})\.(png|jpg|webp)"
)

# PL-FINAL-04: sufijo digest de la era legacy digest-era
# (playlist_<id>_<digest20>.<ext>). Un digest exige exactamente 20 hex.
_DIGEST_SUFFIX_RE = re.compile(r"_([0-9a-f]{20})$")


def _owner_token(playlist_id: str) -> str:
    import hashlib

    return hashlib.sha256(playlist_id.encode("utf-8")).hexdigest()[:20]


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
        candidate = self.prepare_candidate(playlist_id, source_image_path, "cover")
        return candidate.path if candidate is not None else None

    def prepare_hero(self, playlist_id: str, source_image_path) -> str | None:
        candidate = self.prepare_candidate(playlist_id, source_image_path, "hero")
        return candidate.path if candidate is not None else None

    def prepare_candidate(
        self, playlist_id: str, source_image_path, role: str
    ) -> PreparedPlaylistAsset | None:
        """PL-FINAL-01: full candidate contract — the returned
        ``created_by_operation`` distinguishes a newly materialized managed
        file from an idempotent REUSE of an identical content-addressed
        file. Only True candidates may enter rollback cleanup ownership."""
        if role not in ("cover", "hero"):
            return None
        suffix = "" if role == "cover" else "_hero"
        return self._prepare_variant(playlist_id, source_image_path, suffix=suffix)

    def _prepare_variant(
        self, playlist_id: str, source_image_path, *, suffix: str
    ) -> PreparedPlaylistAsset | None:
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
        # R4-07: fail-closed CREATE path — un playlist_id unsafe no produce
        # temp, copy ni ningún side effect.
        if not _SAFE_PLAYLIST_ID_RE.fullmatch(playlist_id):
            logger.warning("refusing prepare: unsafe playlist id %r", playlist_id)
            return None
        role = "cover" if suffix == "" else "hero"
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

        # R4-06: V2 — owner token hash + role explícito; el id raw nunca
        # aparece en el nombre (sin ambigüedad de delimitadores).
        stem = (
            f"playlist_v2_{_owner_token(playlist_id)}_{role}_{digest.hexdigest()[:20]}"
        )
        final_path = self._storage_dir / f"{stem}{inspection.extension}"
        try:
            if final_path.is_file():
                temp_path.unlink(missing_ok=True)
                # PL-FINAL-01: idempotent REUSE — the exact bytes already
                # exist as a managed file; this candidate was NOT created
                # by this operation and must never be rollback-cleaned.
                return PreparedPlaylistAsset(
                    path=str(final_path), role=role, created_by_operation=False
                )
            os.replace(temp_path, final_path)
            return PreparedPlaylistAsset(
                path=str(final_path), role=role, created_by_operation=True
            )
        except OSError as exc:
            temp_path.unlink(missing_ok=True)
            logger.warning(
                "Failed to finalize playlist %s asset for %s: %s",
                suffix or "cover",
                playlist_id,
                exc,
            )
            return None

    def collect_orphan_candidates(
        self,
        referenced_paths: set[str],
        live_playlist_ids: set[str],
    ) -> list[Path]:
        """PL-FINAL-C03: production-safe orphan GC (maintenance helper —
        never runs automatically at load).

        Only files that PROVE orphan status are returned:

        - V2 file whose exact path is not referenced by any live playlist
          (the owner token is irrelevant: if nothing references it, the
          mapping is gone and the blob is rebuildable cache debt);
        - legacy stable/digest-era file whose owner playlist_id NO LONGER
          EXISTS (its playlist is gone; the grammar is unambiguous and the
          owner is not alive).

        FAIL CLOSED: any file that does not match a known managed grammar,
        any legacy file whose owner still exists (even if unreferenced),
        and any ambiguous legacy owner are NEVER returned. Deleting a
        wrongly-guessed legacy asset is data loss; leaving an orphan is
        rebuildable debt."""
        try:
            entries = list(self._storage_dir.iterdir())
        except OSError:
            return []
        orphans: list[Path] = []
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                continue
            resolved = entry.resolve()
            if str(resolved) in referenced_paths:
                continue
            name = entry.name
            if _V2_ASSET_RE.fullmatch(name) is not None:
                # Blob no referenciado por ninguna playlist viva.
                orphans.append(resolved)
                continue
            # Gramática legacy: el owner debe ser un playlist YA INEXISTENTE.
            owner = self._legacy_owner(name)
            if owner is None:
                continue  # gramática desconocida o ambigua → nunca tocar
            if owner in live_playlist_ids:
                continue  # el dueño vive → no es un orphan probado
            orphans.append(resolved)
        return orphans

    @staticmethod
    def _legacy_owner(name: str) -> str | None:
        """Owner playlist_id de la gramática legacy (stable + digest-era).
        None cuando la gramática no matchea o es ambigua (fail closed)."""
        suffix = Path(name).suffix.lower()
        if suffix not in _ALLOWED_EXTENSIONS:
            return None
        stem = name[: -len(suffix)]
        digest_match = _DIGEST_SUFFIX_RE.search(stem)
        owner = stem[: digest_match.start()] if digest_match is not None else stem
        # playlist_<owner> o playlist_<owner>_hero
        if not owner.startswith("playlist_"):
            return None
        owner = owner[len("playlist_") :]
        if owner.endswith("_hero"):
            owner = owner[: -len("_hero")]
        if not owner or not _SAFE_PLAYLIST_ID_RE.fullmatch(owner):
            return None
        if owner.endswith("_hero") or _DIGEST_SUFFIX_RE.search(owner) is not None:
            return None  # dueño ambiguo → fail closed
        return owner

    def delete_legacy_managed_asset(
        self, playlist_id: str, role: str, managed_path: str
    ) -> bool:
        """R5-06 + PL-FINAL-04: retirement EXPLÍCITO de assets pre-V2, sin
        relajar la seguridad V2.

        Autoriza SOLO la gramática legacy exacta:

            stable cover:  playlist_<playlist_id>.<ext>
            stable hero:   playlist_<playlist_id>_hero.<ext>
            digest cover:  playlist_<playlist_id>_<digest20>.<ext>
            digest hero:   playlist_<playlist_id>_hero_<digest20>.<ext>

        FAIL CLOSED cuando la ownership es AMBIGUA en estas gramáticas
        (playlist_id que termina en "_hero" o en un patrón de digest): la
        deuda de storage es preferible al cross-owner deletion."""
        storage = self._storage_dir.resolve()
        candidate = Path(managed_path).resolve()
        if candidate.parent != storage:
            logger.warning("refusing legacy delete: non-managed path")
            return False
        if not _SAFE_PLAYLIST_ID_RE.fullmatch(playlist_id):
            logger.warning("refusing legacy delete: unsafe id %r", playlist_id)
            return False
        if playlist_id.endswith("_hero"):
            # Ambiguo en la gramática legacy (cover de "x_hero" vs hero de
            # "x") — fail closed.
            logger.warning("refusing legacy delete: ambiguous owner %r", playlist_id)
            return False
        if re.search(r"_[0-9a-f]{20}$", playlist_id) is not None:
            # El id termina con un patrón de digest: su cover digest
            # ("playlist_<id>_<digest>") podría coincidir con el cover
            # digest de otro id más corto — fail closed.
            logger.warning(
                "refusing legacy delete: digest-ambiguous owner %r", playlist_id
            )
            return False
        if role not in ("cover", "hero"):
            return False
        if candidate.suffix.lower() not in _ALLOWED_EXTENSIONS:
            return False
        name = candidate.name
        stem = name[: -len(candidate.suffix)]
        digest_match = _DIGEST_SUFFIX_RE.search(stem)
        if role == "cover":
            stable_ok = stem == f"playlist_{playlist_id}"
            digest_ok = digest_match is not None and (
                stem[: digest_match.start()] == f"playlist_{playlist_id}"
            )
        else:
            stable_ok = stem == f"playlist_{playlist_id}_hero"
            digest_ok = digest_match is not None and (
                stem[: digest_match.start()] == f"playlist_{playlist_id}_hero"
            )
        if not (stable_ok or digest_ok):
            logger.warning(
                "refusing legacy delete: %r != %r", candidate.name, playlist_id
            )
            return False
        try:
            candidate.unlink(missing_ok=True)
            return True
        except OSError as exc:
            logger.warning("Failed to delete legacy asset %s: %s", candidate, exc)
            return False

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
        # R4-06: el filename V2 se parsea COMPLETO; el owner token (hash)
        # y el role deben coincidir exactamente. Colisiones de
        # delimitadores ("abc" vs "abc_hero") son imposibles.
        match = _V2_ASSET_RE.fullmatch(candidate.name)
        if match is None:
            # Legacy V1 sin token inequívoco → FAIL CLOSED (deuda de
            # cleanup antes que borrar un asset equivocado).
            logger.warning(
                "refusing delete: %r is not a V2 managed asset for %r (%s)",
                candidate.name,
                playlist_id,
                role,
            )
            return False
        token, file_role, digest, _ext = match.groups()
        if token != _owner_token(playlist_id) or file_role != role:
            logger.warning(
                "refusing delete: %r ownership mismatch (%s/%s)",
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
