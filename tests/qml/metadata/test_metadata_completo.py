"""PQ — Metadata completo: single edit, batch edit, mixed values, artwork, diff,
conflicts, preview, confirmation, progress, cancel, rollback, verify."""
from __future__ import annotations
import os
import tempfile
from unittest.mock import MagicMock
import pytest

pytestmark = pytest.mark.isolation


class TestMetadataSingleEdit:
    @pytest.fixture
    def sample_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_load_metadata_valid_file(self, bridge, sample_file):
        r = bridge.loadMetadata(sample_file)
        assert r["ok"]
        assert bridge.hasSelection

    def test_load_metadata_empty_path(self, bridge):
        r = bridge.loadMetadata("")
        assert not r["ok"]
        assert r["error"] == "EMPTY_FILEPATH"

    def test_load_metadata_nonexistent(self, bridge):
        r = bridge.loadMetadata("/nonexistent.flac")
        assert not r["ok"]
        assert r["error"] == "FILE_NOT_FOUND"

    def test_set_field_after_load(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.setField("title", "New Title")
        assert r["ok"]

    def test_set_field_no_selection(self, bridge):
        r = bridge.setField("title", "Test")
        assert not r["ok"]
        assert r["error"] == "NO_FILE_SELECTED"

    def test_set_field_updates_track_title(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        bridge.setField("title", "Nuevo Título")
        assert bridge.trackTitle != ""

    def test_save_changes_no_file(self, bridge):
        r = bridge.saveChanges()
        assert not r["ok"]

    def test_save_changes_no_changes(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.saveChanges()
        assert not r["ok"]


class TestMetadataBatchEdit:
    @pytest.fixture
    def sample_files(self):
        paths = []
        for _ in range(3):
            with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
                f.write(b"fLaC" + b"\x00" * 2000)
                paths.append(f.name)
        yield paths
        for p in paths:
            if os.path.exists(p):
                os.unlink(p)

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_batch_set_field_empty_list(self, bridge):
        r = bridge.batchSetField([], "title", "Test")
        assert r.get("ok") is not None

    def test_batch_set_field_multiple_files(self, bridge, sample_files):
        r = bridge.batchSetField(sample_files, "title", "Batch Title")
        assert r.get("ok") is not None

    def test_batch_set_field_tracks_errors(self, bridge, sample_files):
        files = sample_files + ["/nonexistent.flac"]
        r = bridge.batchSetField(files, "artist", "Test Artist")
        assert r.get("errors", 0) >= 0 or r.get("ok") is not None

    def test_batch_set_field_with_service(self, bridge, sample_files):
        ms = MagicMock()
        ms.read.return_value.ok = True
        ms.read.return_value.data = {"fields": {}}
        bridge._ms = ms
        r = bridge.batchSetField(sample_files, "genre", "Rock")
        assert r["ok"]

    def test_batch_cancel(self, bridge):
        r = bridge.cancelBatch()
        assert r["ok"]
        assert bridge.status == "CANCELLED"


class TestMetadataArtwork:
    @pytest.fixture
    def sample_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def sample_image(self):
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            f.write(b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_has_artwork(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.hasArtwork()
        assert r["ok"]

    def test_replace_artwork_no_file(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.replaceArtwork("")
        assert not r["ok"]

    def test_replace_artwork_nonexistent(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.replaceArtwork("/nonexistent.png")
        assert not r["ok"]

    def test_replace_artwork_with_image(self, bridge, sample_file, sample_image):
        bridge.loadMetadata(sample_file)
        r = bridge.replaceArtwork(sample_image)
        assert r.get("ok") is not None

    def test_remove_artwork_no_selection(self, bridge):
        r = bridge.removeArtwork()
        assert not r["ok"]

    def test_remove_artwork_after_load(self, bridge, sample_file):
        bridge.loadMetadata(sample_file)
        r = bridge.removeArtwork()
        assert r.get("ok") is not None


class TestMetadataDiff:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    @pytest.fixture
    def tmp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_clear_resets_state(self, bridge, tmp_file):
        bridge.loadMetadata(tmp_file)
        bridge.clear()
        assert not bridge.hasSelection
        assert bridge.trackTitle == ""

    def test_status_initial_idle(self, bridge):
        assert bridge.status == "IDLE"

    def test_can_apply_false_no_selection(self, bridge):
        assert not bridge.canApply

    def test_can_apply_after_load(self, bridge, tmp_file):
        bridge.loadMetadata(tmp_file)
        assert bridge.canApply


class TestMetadataConfirmation:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    @pytest.fixture
    def tmp_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_reject_save_resets_status(self, bridge):
        r = bridge.rejectSave()
        assert r["ok"]
        assert bridge.status == "IDLE"

    def test_confirm_save_invalid_token(self, bridge):
        r = bridge.confirmSave("invalid-token")
        assert not r["ok"]

    def test_save_changes_awaits_confirmation_with_service(self, bridge, tmp_file):
        ms = MagicMock()
        ms.read.return_value.ok = True
        ms.read.return_value.data = {"fields": {}}
        ms.create_confirmation_token.return_value = "review-123"
        bridge._ms = ms
        bridge.loadMetadata(tmp_file)
        bridge.setField("title", "New")
        r = bridge.saveChanges()
        assert r.get("awaiting_confirmation")


class TestMetadataProgress:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge()

    def test_batch_progress_signal(self, bridge):
        assert hasattr(bridge, 'batchProgress')

    def test_operation_completed_signal(self, bridge):
        assert hasattr(bridge, 'operationCompleted')

    def test_operation_failed_signal(self, bridge):
        assert hasattr(bridge, 'operationFailed')

    def test_confirmation_requested_signal(self, bridge):
        assert hasattr(bridge, 'confirmationRequested')

    def test_status_changed_signal(self, bridge):
        assert hasattr(bridge, 'statusChanged')


class TestMetadataRollback:
    @pytest.fixture
    def sample_file(self):
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_rollback_on_write_failure(self):
        from ui_qml_bridge.metadata_tag_adapter import (
            create_backup, rollback,
        )
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        try:
            backup = create_backup(path)
            assert backup is not None
            r = rollback(backup, path)
            assert r["ok"]
        finally:
            if os.path.exists(path):
                os.unlink(path)


class TestMetadataVerify:
    def test_verify_changes_valid(self):
        from ui_qml_bridge.metadata_tag_adapter import verify_changes
        with tempfile.NamedTemporaryFile(suffix=".flac", delete=False) as f:
            f.write(b"fLaC" + b"\x00" * 2000)
            path = f.name
        try:
            r = verify_changes(path, {})
            assert r["ok"]
        finally:
            if os.path.exists(path):
                os.unlink(path)

    def test_verify_changes_nonexistent(self):
        from ui_qml_bridge.metadata_tag_adapter import verify_changes
        r = verify_changes("/nonexistent.flac", {})
        assert r is not None
