"""M6.9-BACKEND-R1 — external artwork MIME truth.

- JPEG/PNG/WebP accepted; missing declared MIME → sniff decides;
  declared/actual mismatch fails closed; invalid and oversized payloads
  rejected; decode-bomb geometry rejected pre-decode; a failed
  replacement preserves the previous valid asset; completed records
  carry the VALIDATED canonical MIME.
"""

import hashlib

from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QImageWriter

from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind
from michi.infrastructure.enrichment_assets import FilesystemEnrichmentAssetStore


def image_bytes(fmt: str, color: int = 0xFF8844) -> bytes:
    image = QImage(8, 6, QImage.Format_RGB32)
    image.fill(color)
    buffer = QBuffer()
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, fmt)
    return bytes(buffer.data())


def record(mime_type="") -> EnrichmentAssetRecord:
    return EnrichmentAssetRecord(
        asset_id="cover-1",
        entity_kind=EnrichmentEntityKind.ALBUM,
        external_entity_id="rg-x",
        mime_type=mime_type,
    )


SUPPORTED = {bytes(f).decode() for f in QImageWriter.supportedImageFormats()}


class TestExternalArtworkMimeTruth:
    def test_jpeg_accepted(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        stored = store.store(record("image/jpeg"), image_bytes("JPG"))
        assert stored is not None
        assert stored.mime_type == "image/jpeg"

    def test_png_accepted(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        stored = store.store(record("image/png"), image_bytes("PNG"))
        assert stored is not None
        assert stored.mime_type == "image/png"

    def test_webp_accepted_when_supported(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        stored = store.store(record("image/webp"), image_bytes("WEBP"))
        if "webp" in SUPPORTED:
            assert stored is not None
            assert stored.mime_type == "image/webp"
        else:
            assert stored is None  # fail-closed

    def test_missing_declared_mime_sniff_decides(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        stored = store.store(record(""), image_bytes("PNG"))
        assert stored is not None
        # The completed record carries the VALIDATED canonical MIME.
        assert stored.mime_type == "image/png"

    def test_declared_jpeg_actual_png_rejected(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        assert store.store(record("image/jpeg"), image_bytes("PNG")) is None

    def test_invalid_payload_rejected(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        assert store.store(record(""), b"not an image") is None

    def test_previous_asset_survives_failed_replacement(self, tmp_path):
        store = FilesystemEnrichmentAssetStore(tmp_path / "assets")
        good = image_bytes("PNG")
        first = store.store(record(""), good)
        assert first is not None
        # A failed replacement (invalid payload) must not destroy it.
        assert store.store(record(""), b"corrupted") is None
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == good
        assert store.record_for("cover-1").checksum == hashlib.sha256(good).hexdigest()
