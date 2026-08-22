"""M6.9A-R1 — external asset store hardening tests (real temp filesystem).

Coverage (§82 + §99):
- valid JPEG / PNG accepted; WEBP per platform support (fail-closed)
- invalid bytes with image extension: REJECTED
- wrong / disallowed MIME: REJECTED
- oversized payload: REJECTED
- path-traversal asset ids: REJECTED
- atomic replacement; failed store never destroys the old valid asset
- deterministic sha256 checksum; provenance sidecar round-trip
- no partial visible assets; clear() removes everything
"""

import hashlib

import pytest
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage, QImageWriter

from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind
from michi.infrastructure.enrichment_assets import (
    MAX_EXTERNAL_IMAGE_BYTES,
    FilesystemEnrichmentAssetStore,
)

SUPPORTED_FORMATS = {
    bytes(fmt).decode() for fmt in QImageWriter.supportedImageFormats()
}


def make_image_bytes(fmt: str, color: int = 0xFF8844) -> bytes:
    image = QImage(8, 6, QImage.Format_RGB32)
    image.fill(color)
    buffer = QBuffer()
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, fmt)
    return bytes(buffer.data())


def make_png_bytes() -> bytes:
    return make_image_bytes("PNG")


def make_jpeg_bytes() -> bytes:
    return make_image_bytes("JPG")


def asset_record(asset_id: str, mime_type: str) -> EnrichmentAssetRecord:
    return EnrichmentAssetRecord(
        asset_id=asset_id,
        entity_kind=EnrichmentEntityKind.ARTIST,
        external_entity_id="mb-a",
        mime_type=mime_type,
        provider="fake-provider",
        source_url="https://example.org/cover",
    )


@pytest.fixture
def store(tmp_path) -> FilesystemEnrichmentAssetStore:
    return FilesystemEnrichmentAssetStore(tmp_path / "assets")


class TestValidImages:
    def test_valid_png_accepted_with_checksum_and_dimensions(self, store):
        data = make_png_bytes()
        result = store.store(asset_record("cover-1", "image/png"), data)
        assert result is not None
        assert result.checksum == hashlib.sha256(data).hexdigest()
        assert (result.width, result.height) == (8, 6)
        assert store.path_for("cover-1") is not None

    def test_valid_jpeg_accepted(self, store):
        data = make_jpeg_bytes()
        result = store.store(asset_record("cover-2", "image/jpeg"), data)
        assert result is not None
        assert result.checksum == hashlib.sha256(data).hexdigest()

    def test_webp_follows_platform_support(self, store):
        data = make_image_bytes("WEBP")
        result = store.store(asset_record("cover-3", "image/webp"), data)
        if "webp" in SUPPORTED_FORMATS:
            assert result is not None
        else:
            # Platform cannot decode webp: fail-closed.
            assert result is None

    def test_checksum_is_deterministic(self, store):
        data = make_png_bytes()
        first = store.store(asset_record("cover-1", "image/png"), data)
        second = store.store(asset_record("cover-1", "image/png"), data)
        assert first is not None and second is not None
        assert first.checksum == second.checksum == hashlib.sha256(data).hexdigest()

    def test_provenance_sidecar_round_trip(self, store):
        result = store.store(asset_record("cover-1", "image/png"), make_png_bytes())
        assert result is not None
        record = store.record_for("cover-1")
        assert record is not None
        assert record.provider == "fake-provider"
        assert record.source_url == "https://example.org/cover"
        assert record.external_entity_id == "mb-a"
        assert record.checksum == result.checksum


class TestRejections:
    def test_invalid_bytes_with_png_mime_rejected(self, store):
        assert (
            store.store(asset_record("bad-1", "image/png"), b"not an image at all")
            is None
        )
        assert store.path_for("bad-1") is None

    def test_mime_content_mismatch_rejected(self, store):
        # PNG bytes declared as JPEG: reject (sniffed content disagrees).
        assert (
            store.store(asset_record("bad-2", "image/jpeg"), make_png_bytes()) is None
        )

    def test_disallowed_mime_rejected(self, store):
        assert store.store(asset_record("bad-3", "image/gif"), make_png_bytes()) is None

    def test_empty_payload_rejected(self, store):
        assert store.store(asset_record("bad-4", "image/png"), b"") is None

    def test_oversized_payload_rejected(self, store):
        huge = b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_EXTERNAL_IMAGE_BYTES + 1)
        assert store.store(asset_record("bad-5", "image/png"), huge) is None

    def test_path_traversal_asset_id_rejected(self, store):
        for evil in ("../cover", "a/b", "a\\b", "", "..", "a b", "a" * 200):
            assert (
                store.store(asset_record(evil, "image/png"), make_png_bytes()) is None
            )
        assert store.path_for("../cover") is None


class TestAtomicity:
    def test_atomic_replacement_keeps_new_bytes(self, store):
        first = make_image_bytes("PNG", color=0x112233)
        second = make_image_bytes("PNG", color=0x445566)
        store.store(asset_record("cover-1", "image/png"), first)
        store.store(asset_record("cover-1", "image/png"), second)
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == second

    def test_failed_store_preserves_old_valid_asset(self, store):
        good = make_png_bytes()
        store.store(asset_record("cover-1", "image/png"), good)
        # A later invalid store for the same id must not destroy it.
        assert store.store(asset_record("cover-1", "image/png"), b"corrupted") is None
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == good
        record = store.record_for("cover-1")
        assert record is not None
        assert record.checksum == hashlib.sha256(good).hexdigest()

    def test_no_partial_visible_assets_after_failure(self, store):
        store.store(asset_record("bad-6", "image/png"), b"corrupted")
        assert store.path_for("bad-6") is None
        if store._root.exists():
            assert list(store._root.iterdir()) == []

    def test_clear_removes_assets_and_sidecars(self, store):
        store.store(asset_record("cover-1", "image/png"), make_png_bytes())
        store.clear()
        assert store.path_for("cover-1") is None
        assert store.record_for("cover-1") is None
