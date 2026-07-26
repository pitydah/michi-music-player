from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.metadata_bridge import MetadataBridge


pytestmark = pytest.mark.isolation


class TestMetadataBatchWorker:
    @pytest.fixture
    def job_service(self) -> None:
        js = MagicMock()
        js.create.return_value = MagicMock(job_id="metadata_batch")
        js.cancel_all.return_value = True
        return js

    @pytest.fixture
    def bridge(self, job_service) -> None:
        return MetadataBridge(metadata_service=MagicMock(), job_service=job_service)

    def test_batch_set_field_returns_result(self, bridge) -> None:
        result = bridge.batchSetField(["/fake/file.flac"], "title", "New Title")
        assert isinstance(result, dict)

    def test_batch_cancellation(self, bridge, job_service) -> None:
        many_files = [f"/fake/file_{i}.flac" for i in range(5)]
        bridge.batchSetField(many_files, "artist", "Test Artist")
        cancel_result = bridge.cancelBatch()
        assert cancel_result.get("ok")
        job_service.cancel_all.assert_called_once_with(owner="metadata_bridge")

    def test_batch_sync_fallback(self) -> None:
        bridge = MetadataBridge(metadata_service=MagicMock())
        result = bridge.batchSetField(["/fake/file.flac"], "title", "Sync Title")
        assert isinstance(result, dict)

    def test_batch_set_field_with_different_key_types(self, bridge) -> None:
        keys = ["title", "artist", "album", "genre", "year", "track_number"]
        for key in keys:
            result = bridge.batchSetField(["/fake/file.flac"], key, "test_val")
            assert isinstance(result, dict)

    def test_cancel_batch_returns_ok(self, bridge, job_service) -> None:
        result = bridge.cancelBatch()
        assert result.get("ok")

    def test_batch_empty_list(self, bridge) -> None:
        result = bridge.batchSetField([], "title", "Test")
        assert result.get("ok") is not None

    def test_batch_no_metadata_service(self, job_service) -> None:
        bridge = MetadataBridge(job_service=job_service)
        result = bridge.batchSetField(["/fake/file.flac"], "title", "Test")
        assert isinstance(result, dict)
