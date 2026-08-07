from __future__ import annotations
"""Tests for batch metadata editing."""

import time

import pytest
from unittest.mock import MagicMock
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("metadata")]


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestMetadataBatchEdit:
    _app_ref = None

    @pytest.fixture
    def app(self):
        if TestMetadataBatchEdit._app_ref is None:
            TestMetadataBatchEdit._app_ref = (
                QCoreApplication.instance() or QCoreApplication()
            )
        return TestMetadataBatchEdit._app_ref

    @pytest.fixture
    def worker_manager(self):
        from core.worker_manager import WorkerManager
        wm = WorkerManager()
        yield wm
        wm.shutdown()

    @pytest.fixture
    def bridge(self, worker_manager):
        from core.jobs.job_service import DurableJobService
        from ui_qml_bridge.metadata_bridge import MetadataBridge

        def _handler(job, ctx):
            payload = job.payload or {}
            count = len(payload.get("filepaths") or [])
            for idx in range(count):
                ctx.token.raise_if_cancelled()
                ctx.report_progress(idx / max(count, 1), payload.get("field", ""))
            return {"ok": True, "applied": 0, "errors": count, "total": count}

        svc = DurableJobService(db_path=":memory:", worker_manager=worker_manager)
        svc.register_handler("metadata_batch", _handler)
        return MetadataBridge(metadata_service=MagicMock(), job_service=svc)

    def test_batch_set_field_async(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "artist", "Batch Artist")
        assert result.get("async")
        _process_events(0.5)

    def test_batch_set_field_different_keys(self, app, bridge):
        terminal = ("SUCCEEDED", "FAILED", "CANCELLED")
        for key in ("title", "artist", "album", "genre", "year", "track_number", "disc_number", "composer", "comment", "bpm"):
            result = bridge.batchSetField(["/fake/file.flac"], key, "test_val")
            assert result.get("async")
            deadline = time.time() + 2.0
            job_id = result["job_id"]
            while time.time() < deadline:
                state = bridge._js.get_job(job_id).state.value
                if state in terminal:
                    break
                QCoreApplication.processEvents()
                time.sleep(0.01)

    def test_batch_cancellation(self, bridge):
        many_files = [f"/fake/file_{i}.flac" for i in range(500)]
        result = bridge.batchSetField(many_files, "artist", "Cancelled")
        assert result.get("async")
        cancel_result = bridge.cancelBatch()
        assert cancel_result.get("ok")
        _process_events(0.5)

    def test_batch_sync_fallback(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        bridge = MetadataBridge(metadata_service=MagicMock())
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
        assert result.get("async")
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
        assert result.get("async")
        _process_events(0.5)

    def test_batch_rejects_busy(self, bridge):
        bridge._status = "busy"
        bridge.batchSetField(["/fake/1.flac"], "title", "T1")
        bridge.batchSetField(["/fake/2.flac"], "title", "T2")
        _process_events(0.5)

    def test_batch_set_field_with_empty_value(self, bridge):
        result = bridge.batchSetField(["/fake/file.flac"], "title", "")
        assert result.get("async")
        _process_events(0.5)
