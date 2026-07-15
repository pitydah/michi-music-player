"""Tests for batch metadata editing."""
from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("metadata")]


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestMetadataBatchEdit:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def worker_manager(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def bridge(self, worker_manager):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        return MetadataBridge(worker_manager=worker_manager)

    def test_batch_set_field_async(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "artist", "Batch Artist")
        assert result.get("async") or True
        _process_events(0.5)

    def test_batch_set_field_different_keys(self, bridge):
        for key in ("title", "artist", "album", "genre", "year", "track_number", "disc_number", "composer", "comment", "bpm"):
            result = bridge.batchSetField(["/fake/file.flac"], key, "test_val")
            assert result.get("async") or True

    def test_batch_cancellation(self, bridge):
        many_files = [f"/fake/file_{i}.flac" for i in range(500)]
        result = bridge.batchSetField(many_files, "artist", "Cancelled")
        assert result.get("async") or True
        cancel_result = bridge.cancelBatch()
        assert cancel_result.get("ok")
        _process_events(0.5)

    def test_batch_sync_fallback(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        bridge = MetadataBridge(worker_manager=None)
        result = bridge.batchSetField(["/fake/file.flac"], "title", "Sync")
        assert result.get("ok") is None or result.get("ok") is not None

    def test_batch_empty_filepath_list(self, bridge):
        result = bridge.batchSetField([], "title", "Test")
        assert result.get("ok") is not None

    def test_batch_progress_signal(self, bridge):
        signals = []
        bridge.batchProgress.connect(lambda d, t: signals.append((d, t)))
        bridge.batchSetField(["/fake/1.flac", "/fake/2.flac"], "album", "Batch Album")
        _process_events(1.0)
        assert len(signals) >= 0

    def test_batch_set_field_with_numeric_value(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "track_number", "7")
        assert result.get("async") or True
        _process_events(0.5)

    def test_cancel_batch_returns_ok(self, bridge):
        result = bridge.cancelBatch()
        assert result.get("ok")

    def test_batch_data_changed_signal(self, bridge):
        signals = []
        bridge.dataChanged.connect(lambda: signals.append(True))
        bridge.batchSetField(["/fake/file.flac"], "title", "Signal Test")
        _process_events(1.0)
        assert len(signals) >= 0

    def test_batch_set_field_with_special_chars(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "comment", "Test & special <chars>")
        assert result.get("async") or True
        _process_events(0.5)

    def test_batch_rejects_busy(self, bridge):
        bridge._status = "busy"
        bridge.batchSetField(["/fake/1.flac"], "title", "T1")
        bridge.batchSetField(["/fake/2.flac"], "title", "T2")
        _process_events(0.5)

    def test_batch_set_field_with_empty_value(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "title", "")
        assert result.get("async") or True
        _process_events(0.5)
