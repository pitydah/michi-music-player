"""Filesystem enrichment asset store (M6.9A-R1) — EXTERNAL ARTWORK ONLY.

M6.9A ARTWORK FIREWALL: three independent artwork authorities exist
(LOCAL embedded/folder, USER override, EXTERNAL downloaded). This store
owns ONLY the external one, in its own directory. It must never reuse or
mutate the canonical local artwork cache and never write downloaded
artwork into audio files.

R1 production-safety hardening (before any network provider exists):

- one documented size bound (``MAX_EXTERNAL_IMAGE_BYTES``)
- image MIME allowlist (jpeg / png / webp) validated against BOTH the
  declared MIME and the sniffed magic bytes
- decodable-image validation via QImageReader (no Pillow) — a platform
  that cannot decode a format rejects it (fail-closed)
- strict asset-id validation: remote titles NEVER become filesystem
  paths
- atomic write (same-directory temp + os.replace): failures never leave
  a partial visible asset, replacements never destroy a valid old asset
- sha256 checksum + provenance sidecar (``EnrichmentAssetRecord``)
"""

import contextlib
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

# Conservative maximum external image byte size (R1): one constant,
# documented, tested. Never allow unlimited downloaded blobs.
MAX_EXTERNAL_IMAGE_BYTES = 10 * 1024 * 1024

ALLOWED_IMAGE_MIME_TYPES = frozenset({"image/jpeg", "image/png", "image/webp"})

# Declared MIME -> magic-byte format used for content-type verification.
_MIME_MAGIC = {
    "image/jpeg": b"\xff\xd8\xff",
    "image/png": b"\x89PNG\r\n\x1a\n",
    "image/webp": b"RIFF",
}
_MIME_FORMAT_NAME = {
    "image/jpeg": "jpeg",
    "image/png": "png",
    "image/webp": "webp",
}
_ASSET_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")


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
    """Validated, atomic, checksummed external asset persistence."""

    def __init__(self, root_dir: Path) -> None:
        self._root = root_dir

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
            local_path="",
        )
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            target = self._root / record.asset_id
            temp = self._root / f".{record.asset_id}.{uuid4().hex}.tmp"
            temp.write_bytes(data)
            os.replace(temp, target)  # atomic: never a partial visible asset
        except OSError as exc:
            logger.warning("enrichment asset store failed: %s", exc)
            return None
        completed = EnrichmentAssetRecord(
            **{**asdict(completed), "local_path": str(target)}
        )
        if not self._write_sidecar(completed):
            # No provenance record means no visible asset: remove the
            # target so the store never exposes an untracked file.
            with contextlib.suppress(OSError):
                target.unlink()
            return None
        return completed

    def _sidecar_path(self, asset_id: str) -> Path:
        return self._root / f"{asset_id}.json"

    def _write_sidecar(self, record: EnrichmentAssetRecord) -> bool:
        try:
            sidecar = self._sidecar_path(record.asset_id)
            temp = self._root / f".{record.asset_id}.{uuid4().hex}.tmp"
            payload = asdict(record)
            payload["entity_kind"] = record.entity_kind.name
            temp.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
            os.replace(temp, sidecar)
            return True
        except OSError as exc:
            logger.warning("enrichment asset sidecar failed: %s", exc)
            return False

    def path_for(self, asset_id: str) -> Path | None:
        if not _validate_asset_id(asset_id):
            return None
        target = self._root / asset_id
        return target if target.is_file() else None

    def record_for(self, asset_id: str) -> EnrichmentAssetRecord | None:
        if not _validate_asset_id(asset_id):
            return None
        sidecar = self._sidecar_path(asset_id)
        try:
            payload = json.loads(sidecar.read_text(encoding="utf-8"))
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
        return record

    def clear(self) -> None:
        """Delete stored assets and sidecars; temp leftovers are ignored
        (never exposed) and cleaned opportunistically."""
        try:
            for path in self._root.iterdir():
                if path.is_file():
                    path.unlink()
        except OSError as exc:
            logger.warning("enrichment asset clear failed: %s", exc)
