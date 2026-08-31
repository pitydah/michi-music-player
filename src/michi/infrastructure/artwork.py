"""Mutagen-based embedded artwork provider + deterministic disk cache."""

import hashlib
import logging
import os
from pathlib import Path

from mutagen import File as MutagenFile
from mutagen import MutagenError

from michi.application.library_artwork_contracts import (
    ArtworkProbeObservation,
    ArtworkProbeVerdict,
    PreparedArtwork,
)
from michi.application.ports import ArtworkCachePort, ArtworkProviderPort
from michi.domain.library import Artwork

logger = logging.getLogger(__name__)

_DEFAULT_MAX_BYTES = 10 * 1024 * 1024

_EXT_BY_MIME = {
    "image/jpeg": "jpg",
    "image/png": "png",
}


class MutagenArtworkProvider(ArtworkProviderPort):
    """Reads embedded cover art from media files via mutagen.

    Contract: artwork absence is NOT an error. Untagged files, unknown
    formats, corrupt files and unreadable/missing files all yield ``None``
    (logged, never raised). Oversized artwork is also discarded (not
    cacheable)."""

    def __init__(self, max_bytes: int = _DEFAULT_MAX_BYTES) -> None:
        self._max_bytes = max_bytes

    # M6.5: deterministic local artwork fallback — fixed, ordered candidate
    # names (cover.* then folder.* then front.*). No arbitrary directory
    # scanning: only these names are ever considered.
    _LOCAL_ARTWORK_FILES = (
        "cover.jpg",
        "cover.jpeg",
        "cover.png",
        "folder.jpg",
        "folder.png",
        "front.jpg",
        "front.png",
    )
    _LOCAL_ARTWORK_MIME = {
        ".jpg": "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png": "image/png",
    }

    def get_embedded_artwork(self, file_path: Path) -> Artwork | None:
        try:
            audio = MutagenFile(str(file_path))
        except OSError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        except MutagenError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        if audio is None:
            return None

        # MP3/ID3: APIC frames on the tag object. Corrupt MP3s still parse
        # into an MP3 object whose tags attribute is None — guard attribute
        # access instead of assuming tags always exist.
        tags = getattr(audio, "tags", None)
        if tags is not None and hasattr(tags, "getall"):
            frames = tags.getall("APIC")
            if frames:
                # M6.5: prefer the FIRST frame designated as the FRONT COVER
                # (type 3); fall back to the first frame when no front-cover
                # designation exists.
                frame = next(
                    (f for f in frames if getattr(f, "type", None) == 3),
                    frames[0],
                )
                return self._guarded(frame.mime, frame.data)

        # FLAC: pictures list on the audio object.
        pictures = getattr(audio, "pictures", None)
        if pictures:
            # M6.5: same front-cover (type 3) preference as APIC.
            picture = next(
                (p for p in pictures if getattr(p, "type", None) == 3),
                pictures[0],
            )
            return self._guarded(picture.mime, picture.data)

        return None

    def get_embedded_front_artwork(self, file_path: Path) -> Artwork | None:
        """EXPLICIT front-cover artwork only (M6-PRODUCTION-INTEGRATION):
        APIC/picture frames designated type 3 (front cover); anything else
        yields None so the album-level two-pass resolution can prefer a real
        front cover from ANY track before falling back to any embedded art."""
        try:
            audio = MutagenFile(str(file_path))
        except OSError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        except MutagenError as exc:
            logger.warning("Cannot read %s for artwork: %s", file_path, exc)
            return None
        if audio is None:
            return None
        tags = getattr(audio, "tags", None)
        if tags is not None and hasattr(tags, "getall"):
            frames = tags.getall("APIC")
            frame = next((f for f in frames if getattr(f, "type", None) == 3), None)
            if frame is not None:
                return self._guarded(frame.mime, frame.data)
        pictures = getattr(audio, "pictures", None)
        if pictures:
            picture = next((p for p in pictures if getattr(p, "type", None) == 3), None)
            if picture is not None:
                return self._guarded(picture.mime, picture.data)
        return None

    def get_local_artwork(self, album_dir: Path) -> Artwork | None:
        """Deterministic local artwork fallback (M6.5): cover.* then
        folder.* then front.*, case-insensitive, in the album directory.
        Unreadable/over-max entries are skipped; no arbitrary scanning."""
        for name in self._LOCAL_ARTWORK_FILES:
            candidate = album_dir / name
            if not candidate.is_file():
                # case-insensitive fallback
                lowered = name.lower()
                found = None
                try:
                    for entry in album_dir.iterdir():
                        if entry.is_file() and entry.name.lower() == lowered:
                            found = entry
                            break
                except OSError:
                    continue
                candidate = found
            if candidate is None:
                continue
            try:
                data = candidate.read_bytes()
            except OSError:
                continue
            if len(data) > self._max_bytes:
                continue
            mime = self._LOCAL_ARTWORK_MIME.get(candidate.suffix.lower(), "")
            if not mime:
                continue
            return Artwork(data=data, mime_type=mime)
        return None

    def _probe_embedded(
        self, file_path: Path, *, front_only: bool
    ) -> ArtworkProbeObservation:
        """Tri-state embedded probe (R4 artwork authority): filesystem or
        Mutagen failure is UNAVAILABLE (not confirmed absence)."""
        try:
            audio = MutagenFile(str(file_path))
        except (OSError, MutagenError) as exc:
            return ArtworkProbeObservation.unavailable(str(exc))
        if audio is None:
            return ArtworkProbeObservation.unavailable(
                "media parser returned no readable object"
            )
        tags = getattr(audio, "tags", None)
        frame = None
        if tags is not None and hasattr(tags, "getall"):
            frames = tags.getall("APIC")
            if front_only:
                frame = next((f for f in frames if getattr(f, "type", None) == 3), None)
            else:
                frame = next(
                    (f for f in frames if getattr(f, "type", None) == 3),
                    frames[0] if frames else None,
                )
            if frame is not None:
                artwork = self._guarded(frame.mime, frame.data)
                if artwork is not None:
                    return ArtworkProbeObservation.found(artwork)
                return ArtworkProbeObservation.unavailable(
                    "embedded artwork unusable/oversized"
                )
        pictures = getattr(audio, "pictures", None)
        if pictures:
            if front_only:
                picture = next(
                    (p for p in pictures if getattr(p, "type", None) == 3),
                    None,
                )
            else:
                picture = next(
                    (p for p in pictures if getattr(p, "type", None) == 3),
                    pictures[0],
                )
            if picture is not None:
                artwork = self._guarded(picture.mime, picture.data)
                if artwork is not None:
                    return ArtworkProbeObservation.found(artwork)
                return ArtworkProbeObservation.unavailable(
                    "embedded artwork unusable/oversized"
                )
        # Tags leídos correctamente y sin artwork → ausencia confirmada.
        return ArtworkProbeObservation.absent()

    def _probe_local_artwork(self, album_dir: Path) -> ArtworkProbeObservation:
        """Tri-state local probe: complete deterministic enumeration;
        unreadable entries or an inaccessible directory are UNAVAILABLE."""
        try:
            entries = list(album_dir.iterdir())
        except OSError as exc:
            return ArtworkProbeObservation.unavailable(str(exc))
        lowered_map = {}
        uncertain = False
        for entry in entries:
            try:
                if not entry.is_file():
                    continue
            except OSError:
                uncertain = True
                continue
            lowered_map[entry.name.lower()] = entry
        for name in self._LOCAL_ARTWORK_FILES:
            candidate = lowered_map.get(name.lower())
            if candidate is None:
                continue
            try:
                data = candidate.read_bytes()
            except OSError as exc:
                return ArtworkProbeObservation.unavailable(str(exc))
            if len(data) > self._max_bytes:
                return ArtworkProbeObservation.unavailable("local artwork oversized")
            mime = self._LOCAL_ARTWORK_MIME.get(candidate.suffix.lower(), "")
            if not mime:
                return ArtworkProbeObservation.unavailable(
                    "local artwork MIME not cacheable"
                )
            return ArtworkProbeObservation.found(Artwork(data=data, mime_type=mime))
        if uncertain:
            return ArtworkProbeObservation.unavailable(
                "local artwork observation incomplete"
            )
        return ArtworkProbeObservation.absent()

    def probe_album_artwork(
        self,
        track_paths: tuple[Path, ...],
        token=None,
    ) -> ArtworkProbeObservation:
        """M6.5 album policy with tri-state truth: front → generic →
        local. Any uncertain observation poisons the album verdict to
        UNAVAILABLE (never destroys last-known cache)."""
        uncertain = False
        for path in track_paths:
            if token is not None and token.cancelled:
                from michi.application.ports import ScanCancelled

                raise ScanCancelled()
            observation = self._probe_embedded(path, front_only=True)
            if observation.verdict is ArtworkProbeVerdict.FOUND:
                return observation
            if observation.verdict is ArtworkProbeVerdict.UNAVAILABLE:
                uncertain = True
        for path in track_paths:
            if token is not None and token.cancelled:
                from michi.application.ports import ScanCancelled

                raise ScanCancelled()
            observation = self._probe_embedded(path, front_only=False)
            if observation.verdict is ArtworkProbeVerdict.FOUND:
                return observation
            if observation.verdict is ArtworkProbeVerdict.UNAVAILABLE:
                uncertain = True
        if track_paths:
            local = self._probe_local_artwork(track_paths[0].parent)
            if local.verdict is ArtworkProbeVerdict.FOUND:
                return local
            if local.verdict is ArtworkProbeVerdict.UNAVAILABLE:
                uncertain = True
        if uncertain:
            return ArtworkProbeObservation.unavailable(
                "album artwork observation incomplete"
            )
        return ArtworkProbeObservation.absent()

    def _guarded(self, mime: str, data: bytes) -> Artwork | None:
        if len(data) > self._max_bytes:
            logger.warning(
                "Artwork in %s exceeds %d bytes; not cacheable",
                mime,
                self._max_bytes,
            )
            return None
        return Artwork(data=data, mime_type=mime)


class ArtworkCache(ArtworkCachePort):
    """Deterministic, idempotent on-disk cache for album artwork.

    Implements :class:`michi.application.ports.ArtworkCachePort` — the
    application layer depends on the port, infrastructure owns the disk.

    M6-EXT-R4-M: a rebuildable MANIFEST (``manifest.json``) persists the
    album_key → cached-file mapping so a restart can resolve cached artwork
    while its source is offline. The manifest is CACHE, not user authority:
    an entry pointing to a missing/corrupt file is invalid (None), never a
    crash, never a network repair."""

    _MANIFEST_NAME = "manifest.json"

    def __init__(self, cache_dir: Path) -> None:
        self._cache_dir = cache_dir
        self._manifest_path = cache_dir / self._MANIFEST_NAME
        self._manifest: dict[str, str] = self._load_manifest()

    # ------------------------------------------------------------- manifest

    def _load_manifest(self) -> dict[str, str]:
        try:
            raw = self._manifest_path.read_text(encoding="utf-8")
        except OSError:
            return {}
        import json

        try:
            parsed = json.loads(raw)
        except (TypeError, ValueError):
            return {}
        if not isinstance(parsed, dict):
            return {}
        return {
            k: v for k, v in parsed.items() if isinstance(k, str) and isinstance(v, str)
        }

    def _persist_manifest(self) -> None:
        import json

        try:
            self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self._manifest_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(self._manifest, sort_keys=True), encoding="utf-8")
            os.replace(tmp, self._manifest_path)
        except OSError as exc:
            logger.warning("artwork manifest persist failed (cache only): %s", exc)

    # ------------------------------------------------------------- port API

    def invalidate(self, album_key: str) -> None:
        """P2-HIGH: persist a CONFIRMED negative verdict. The blob is NOT
        deleted synchronously — content-addressed orphan cleanup is cache
        GC outside this fix."""
        self.commit_manifest_batch(upserts=(), removals=(album_key,))

    def prepare_artwork(
        self, album_key: str, artwork: Artwork
    ) -> PreparedArtwork | None:
        """WORKER-SAFE: escribe el blob content-addressed pero NUNCA muta
        el manifest (un worker stale puede dejar un blob huérfano —
        rebuildable — pero jamás un mapping obsoleto)."""
        if not artwork.data:
            return None
        if len(artwork.data) > _DEFAULT_MAX_BYTES:
            return None

        content_digest = hashlib.sha256(artwork.data).hexdigest()
        key_digest = hashlib.sha256(
            (album_key + content_digest).encode("utf-8")
        ).hexdigest()[:16]
        ext = _EXT_BY_MIME.get(artwork.mime_type)
        if ext is None:
            return None
        target = self._cache_dir / f"{key_digest}.{ext}"
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                tmp = target.with_suffix(target.suffix + ".tmp")
                tmp.write_bytes(artwork.data)
                os.replace(tmp, target)
        except OSError as exc:
            logger.warning("Cannot prepare artwork %s: %s", target, exc)
            return None
        return PreparedArtwork(
            album_key=album_key,
            filename=target.name,
            path=target,
        )

    def commit_manifest_batch(
        self,
        *,
        upserts: tuple[PreparedArtwork, ...],
        removals: tuple[str, ...],
    ) -> dict[str, Path]:
        """OWNER: UNA transacción de manifest por lote (N albums → <= 1
        persist). Fail-closed: solo filenames dentro del cache dir."""
        changed = False
        published: dict[str, Path] = {}
        for album_key in removals:
            if album_key in self._manifest:
                self._manifest.pop(album_key, None)
                changed = True
        for prepared in upserts:
            if Path(prepared.filename).name != prepared.filename:
                logger.warning(
                    "rejecting unsafe artwork cache filename: %s",
                    prepared.filename,
                )
                continue
            expected = self._cache_dir / prepared.filename
            if expected != prepared.path:
                logger.warning(
                    "rejecting artwork path outside prepared contract: %s",
                    prepared.path,
                )
                continue
            try:
                exists = expected.is_file()
            except OSError:
                exists = False
            if not exists:
                continue
            if self._manifest.get(prepared.album_key) != prepared.filename:
                self._manifest[prepared.album_key] = prepared.filename
                changed = True
            published[prepared.album_key] = expected
        if changed:
            self._persist_manifest()
        return published

    def lookup(self, album_key: str) -> Path | None:
        """Persisted album_key → cached file, validated against the disk.

        A manifest entry whose file is missing is invalid: the entry is
        dropped from the in-memory manifest (never persisted eagerly) and
        None is returned — no crash, no fabrication, no network."""
        name = self._manifest.get(album_key)
        if not name:
            return None
        target = self._cache_dir / name
        if not target.is_file():
            self._manifest.pop(album_key, None)
            return None
        return target

    def store(self, album_key: str, artwork: Artwork) -> Path | None:
        """Deterministic content-digest-aware store (M6.5): the filename
        derives from sha256(album_key + sha256(data)) so CHANGED artwork
        produces a NEW entry (active on rescan) while unchanged content
        keeps the same path — exists -> return, no rewrite. Old entries
        stay on disk (stale-aware; garbage collection is a later phase).

        Returns the cached path, or None when the artwork is empty/oversized
        and therefore not cacheable."""
        if not artwork.data:
            return None
        if len(artwork.data) > _DEFAULT_MAX_BYTES:
            logger.warning(
                "Artwork for %s exceeds %d bytes; not cacheable",
                album_key,
                _DEFAULT_MAX_BYTES,
            )
            return None
        prepared = self.prepare_artwork(album_key, artwork)
        if prepared is None:
            return None
        published = self.commit_manifest_batch(upserts=(prepared,), removals=())
        return published.get(album_key)
