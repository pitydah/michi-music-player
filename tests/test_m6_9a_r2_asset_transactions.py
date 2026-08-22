"""M6.9A-R2 — asset transaction safety (manifest-as-commit-point).

Failure-injection tests for the content-addressed asset store:
- manifest write failure preserves the previous valid asset (both bytes
  AND provenance)
- object write failure preserves the previous asset
- orphan objects without a manifest are never visible
- malformed/tampered manifests are rejected (no path traversal, checksum
  authority: managed object name must equal the content-addressed name)
- only RELATIVE managed paths are persisted
- MIME validation, decode validation, size bound, safe ids (kept from R1)
"""

import hashlib
import json
from pathlib import Path

import pytest
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QImage

from michi.domain.enrichment import EnrichmentAssetRecord, EnrichmentEntityKind
from michi.infrastructure.enrichment_assets import (
    MAX_EXTERNAL_IMAGE_BYTES,
    FilesystemEnrichmentAssetStore,
)


def make_png_bytes(color: int = 0xFF8844) -> bytes:
    image = QImage(8, 6, QImage.Format_RGB32)
    image.fill(color)
    buffer = QBuffer()
    assert buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert image.save(buffer, "PNG")
    return bytes(buffer.data())


def asset_record(asset_id: str, mime_type: str = "image/png") -> EnrichmentAssetRecord:
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


class TestManifestCommitPoint:
    def test_manifest_failure_preserves_previous_asset(self, store, monkeypatch):
        data_a = make_png_bytes(color=0x112233)
        data_b = make_png_bytes(color=0x445566)
        first = store.store(asset_record("cover-1"), data_a)
        assert first is not None

        def fail_manifest(_record):
            return False

        monkeypatch.setattr(store, "_write_manifest", fail_manifest)
        assert store.store(asset_record("cover-1"), data_b) is None

        # Old asset AND old provenance remain fully visible.
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == data_a
        record = store.record_for("cover-1")
        assert record is not None
        assert record.checksum == hashlib.sha256(data_a).hexdigest()
        assert record.provider == "fake-provider"

    def test_object_failure_preserves_previous_asset(self, store, monkeypatch):
        data_a = make_png_bytes(color=0x112233)
        data_b = make_png_bytes(color=0x445566)
        first = store.store(asset_record("cover-1"), data_a)
        assert first is not None

        def fail_object(_name, _data):
            return False

        monkeypatch.setattr(store, "_write_object", fail_object)
        assert store.store(asset_record("cover-1"), data_b) is None
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == data_a

    def test_successful_replacement_swaps_visibility(self, store):
        data_a = make_png_bytes(color=0x112233)
        data_b = make_png_bytes(color=0x445566)
        store.store(asset_record("cover-1"), data_a)
        second = store.store(asset_record("cover-1"), data_b)
        assert second is not None
        path = store.path_for("cover-1")
        assert path is not None
        assert path.read_bytes() == data_b
        assert second.checksum == hashlib.sha256(data_b).hexdigest()


class TestOrphansAndManifestAuthority:
    def test_orphan_object_never_visible(self, store):
        data = make_png_bytes()
        checksum = hashlib.sha256(data).hexdigest()
        store._objects.mkdir(parents=True, exist_ok=True)
        (store._objects / f"{checksum}.png").write_bytes(data)
        # No manifest references it: invisible through every public API.
        assert store.path_for("cover-1") is None
        assert store.record_for("cover-1") is None

    def test_tampered_manifest_rejected_path_traversal(self, store):
        data = make_png_bytes()
        store.store(asset_record("cover-1"), data)
        manifest = store._records / "cover-1.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["managed_object"] = "../../objects/evil.png"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        assert store.record_for("cover-1") is None
        assert store.path_for("cover-1") is None

    def test_checksum_authority_rejects_mismatched_manifest(self, store):
        data_a = make_png_bytes(color=0x112233)
        data_b = make_png_bytes(color=0x445566)
        store.store(asset_record("cover-1"), data_a)
        manifest = store._records / "cover-1.json"
        payload = json.loads(manifest.read_text(encoding="utf-8"))
        payload["managed_object"] = f"objects/{hashlib.sha256(data_b).hexdigest()}.png"
        manifest.write_text(json.dumps(payload), encoding="utf-8")
        assert store.record_for("cover-1") is None

    def test_malformed_manifest_rejected(self, store):
        data = make_png_bytes()
        store.store(asset_record("cover-1"), data)
        manifest = store._records / "cover-1.json"
        manifest.write_text("{not json", encoding="utf-8")
        assert store.record_for("cover-1") is None


class TestRelativeManagedPaths:
    def test_no_absolute_path_field_persisted(self):
        fields = set(EnrichmentAssetRecord.__dataclass_fields__)
        assert "local_path" not in fields
        assert "managed_object" in fields

    def test_managed_object_is_relative_content_addressed(self, store):
        data = make_png_bytes()
        result = store.store(asset_record("cover-1"), data)
        assert result is not None
        assert result.managed_object.startswith("objects/")
        assert not Path(result.managed_object).is_absolute()
        assert result.managed_object == (
            f"objects/{hashlib.sha256(data).hexdigest()}.png"
        )


class TestR1ValidationStillHolds:
    def test_invalid_bytes_rejected(self, store):
        assert store.store(asset_record("bad-1"), b"not an image") is None

    def test_mime_mismatch_rejected(self, store):
        assert (
            store.store(asset_record("bad-2", "image/jpeg"), make_png_bytes()) is None
        )

    def test_size_bound(self, store):
        huge = b"\x89PNG\r\n\x1a\n" + b"0" * (MAX_EXTERNAL_IMAGE_BYTES + 1)
        assert store.store(asset_record("bad-3"), huge) is None

    def test_unsafe_ids_rejected(self, store):
        for evil in ("../cover", "a/b", "a\\b", "", ".."):
            assert store.store(asset_record(evil), make_png_bytes()) is None
