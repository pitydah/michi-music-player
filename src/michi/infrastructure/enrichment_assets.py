"""Filesystem enrichment asset store (M6.9A-R2) — EXTERNAL ARTWORK ONLY.

M6.9A ARTWORK FIREWALL: three independent artwork authorities exist
(LOCAL embedded/folder, USER override, EXTERNAL downloaded). This store
owns ONLY the external one, in its own directory. It must never reuse or
mutate the canonical local artwork cache and never write downloaded
artwork into audio files.

R2 MANIFEST-AS-COMMIT-POINT STORAGE (failure-atomic):

    <root>/
        objects/
            <sha256>.jpg | .png | .webp      (immutable, content-addressed)
        records/
            <asset_id>.json                   (the manifest — visibility
                                               COMMIT POINT)

A new asset is visible ONLY after its manifest replaces the old one with
a single atomic os.replace. If any step fails, the previous valid asset
(and its manifest) remain fully visible; orphaned immutable objects are
harmless and garbage-collected by clear(). Never store absolute paths:
``managed_object`` is a RELATIVE content-addressed key.

Validation pipeline: asset-id -> size bound -> image MIME allowlist ->
magic-byte content check -> QImageReader decode -> sha256 -> object write
-> manifest swap. MIME/dimensions/checksum authority lives in the
manifest.
"""

import hashlib
import json
import logging
import os
import re
from dataclasses import asdict
from pathlib import Path
from uuid import uuid4

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QImageReader

from michi.application.enrichment_ports import EnrichmentAssetStorePort
from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind

logger = logging.getLogger(__name__)

# Conservative maximum external image byte size (R2): one constant,
# documented, tested. Never allow unlimited downloaded blobs.
MAX_EXTERNAL_IMAGE_BYTES = 10 * 1024 * 1024

ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Declared MIME -> magic-byte format used for content-type verification.
_MIME_MAGIC = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",
}
# Declared MIME -> safe object extension (NEVER derived from URLs/names).
_MIME_EXTENSION = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
}
_ASSET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
_OBJECT_NAME_PATTERN = re.compile(r"^objects/[a-f0-9]{64}\.(?:jpg|png|webp)$")
_OBJECTS_DIR = "objects"
_RECORDS_DIR = "records"


def _validate_asset_id(asset_id: str) -> bool:
    """Strict asset id: 1-128 chars of [A-Za-z0-9._-], never path
    separators, never '..', never empty. Remote titles must be hashed by
    the caller — they never reach the filesystem here."""
    return bool(_ASSET_ID_PATTERN.fullmatch(asset_id))


def _sniff_mime(data: bytes) -> str | None:
    """Content-type detection from magic bytes (independent of the
    declared MIME and of any filename extension)."""
    if data.startswith(_MIME_MAGIC["image/jpeg"]):
        return "image/jpeg"
    if data.startswith(_MIME_MAGIC["image/png"]):
        return "image/png"
    if data.startswith(_MIME_MAGIC["image/webp"]) and data[8:12] == b"WEBP":
        return "image/webp"
    return None


def _decode_dimensions(data: bytes) -> tuple[int, int] | None:
    """Decodable-image validation (narrow, no Pillow): QImageReader must
    actually read the payload. Unsupported/corrupt images -> None
    (fail-closed)."""
    reader = QImageReader()
    reader.setDecideFormatFromContent(True)
    buffer = QBuffer()
    buffer.setData(QByteArray(data))
    if not buffer.open(QIODevice.OpenModeFlag.ReadOnly):
        return None
    reader.setDevice(buffer)
    if not reader.canRead():
        return None
    image = reader.read()
    if image.isNull():
        return None
    return image.width(), image.height()


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FilesystemEnrichmentAssetStore(EnrichmentAssetStorePort):
    """Validated, atomic, checksummed, manifest-controlled external
    asset persistence (R2)."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

    # -- layout -------------------------------------------------------------

    @property
    def _objects(self) -> Path:
        return self._root / _OBJECTS_DIR

    @property
    def _records(self) -> Path:
        return self._root / _RECORDS_DIR

    # -- validation ---------------------------------------------------------

    @staticmethod
    def validate(record: EnrichmentAssetRecord, data: bytes) -> tuple[int, int] | None:
        """Shared validation pipeline: id -> size -> MIME -> magic ->
        decode. Returns (width, height) or None (reject)."""
        if not _validate_asset_id(record.asset_id):
            return None
        if not data:
            return None
        if len(data) > MAX_EXTERNAL_IMAGE_BYTES:
            return None
        if record.mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            return None
        sniffed = _sniff_mime(data)
        if sniffed is None or sniffed != record.mime_type:
            # Declared MIME and actual content disagree: reject.
            return None
        return _decode_dimensions(data)

    # -- persistence --------------------------------------------------------

    def store(
        self, record: EnrichmentAssetRecord, data: bytes
    ) -> EnrichmentAssetRecord | None:
        dimensions = self.validate(record, data)
        if dimensions is None:
            logger.warning(
                "enrichment asset %r rejected by validation", record.asset_id
            )
            return None
        width, height = dimensions
        checksum = _sha256(data)
        object_name = f"{checksum}.{_MIME_EXTENSION[record.mime_type]}"
        completed = EnrichmentAssetRecord(
            asset_id=record.asset_id,
            entity_kind=record.entity_kind,
            external_entity_id=record.external_entity_id,
            mime_type=record.mime_type,
            checksum=checksum,
            provider=record.provider,
            source_url=record.source_url,
            creator=record.creator,
            license=record.license,
            license_url=record.license_url,
            attribution=record.attribution,
            width=width,
            height=height,
            managed_object=f"{_OBJECTS_DIR}/{object_name}",
        )
        # 1. Immutable object write (content-addressed; skip if present).
        if not self._write_object(object_name, data):
            return None
        # 2. Manifest swap = the visibility COMMIT POINT.
        if not self._write_manifest(completed):
            # Old manifest (if any) is untouched: the previous asset
            # remains fully visible. The new object is an invisible orphan
            # and may be garbage-collected later.
            return None
        return completed

    def _write_object(self, object_name: str, data: bytes) -> bool:
        """Content-addressed object write. R3: an EXISTING object is
        verified against its content hash — a corrupted file is replaced
        atomically from the validated new payload; the filename alone is
        never trusted."""
        try:
            self._objects.mkdir(parents=True, exist_ok=True)
            target = self._objects / object_name
            if target.exists() and (
                _sha256(target.read_bytes()) == object_name.split(".", 1)[0]
            ):
                return True  # verified immutable object: reuse
            # Corrupted content: rewrite atomically (old bytes are
            # already invalid; the replacement is the validated data).
            temp = self._objects / f".{object_name}.{uuid4().hex}.tmp"
            temp.write_bytes(data)
            os.replace(temp, target)
            return True
        except OSError as exc:
            logger.warning("enrichment asset object write failed: %s", exc)
            return False

    def _write_manifest(self, record: EnrichmentAssetRecord) -> bool:
        try:
            self._records.mkdir(parents=True, exist_ok=True)
            target = self._records / f"{record.asset_id}.json"
            temp = self._records / f".{record.asset_id}.{uuid4().hex}.tmp"
            payload = asdict(record)
            payload["entity_kind"] = record.entity_kind.name
            temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            os.replace(temp, target)  # atomic commit point
            return True
        except OSError as exc:
            logger.warning("enrichment asset manifest write failed: %s", exc)
            return False

    # -- reads (manifest is the authority) -----------------------------------

    def record_for(self, asset_id: str) -> EnrichmentAssetRecord | None:
        if not _validate_asset_id(asset_id):
            return None
        manifest = self._records / f"{asset_id}.json"
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return None
        if not isinstance(payload, dict):
            return None
        try:
            entity_kind = EnrichmentEntityKind[payload["entity_kind"]]
            record = EnrichmentAssetRecord(**{**payload, "entity_kind": entity_kind})
        except (KeyError, TypeError):
            return None
        if record.asset_id != asset_id:
            return None
        if record.mime_type not in ALLOWED_IMAGE_MIME_TYPES:
            return None
        if not re.fullmatch(r"[a-f0-9]{64}", record.checksum):
            return None
        # Checksum authority: the managed object name MUST be the
        # content-addressed name of exactly this checksum + MIME.
        expected = (
            f"{_OBJECTS_DIR}/{record.checksum}.{_MIME_EXTENSION[record.mime_type]}"
        )
        if record.managed_object != expected:
            return None
        return record

    def path_for(self, asset_id: str) -> Path | None:
        """Resolve through the MANIFEST only: a file merely existing on
        disk is never enough. Returns the managed object path when the
        manifest is valid AND the referenced object exists."""
        if not _validate_asset_id(asset_id):
            return None
        record = self.record_for(asset_id)
        if record is None:
            return None
        if not _OBJECT_NAME_PATTERN.fullmatch(record.managed_object):
            return None
        target = self._root / record.managed_object
        return target if target.is_file() else None

    def clear(self) -> None:
        """Delete manifests AND objects (including unreferenced orphans);
        temp leftovers are ignored (never exposed)."""
        for directory in (self._records, self._objects):
            try:
                for path in directory.iterdir():
                    if path.is_file():
                        path.unlink()
            except OSError as exc:
                if directory.exists():
                    logger.warning("enrichment asset clear failed: %s", exc)
