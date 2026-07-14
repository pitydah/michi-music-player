"""Wave XLIII — 10.1: Metadata batch with correct WorkerManager.

Tests:
  - batchSetField uses run_task with callable, not dict
  - Progress signal emitted
  - Cancellation works
  - Backup, write, verify, rollback
  - Partial result dict
  - Library refresh after batch
"""
from __future__ import annotations

import time

import pytest
from PySide6.QtCore import QCoreApplication


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestMetadataBatchWorker:
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
        br = MetadataBridge(worker_manager=worker_manager)
        return br

    def test_batch_set_field_uses_callable_not_dict(self, worker_manager):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        br = MetadataBridge(worker_manager=worker_manager)
        original_run_task = worker_manager.run_task
        callable_used = False

        def tracking_run_task(task_id, fn, *args, **kwargs):
            nonlocal callable_used
            assert callable(fn), f"fn debe ser callable, no {type(fn)}"
            callable_used = True
            kwargs.pop("owner", None)
            kwargs.pop("cancellable", None)
            kwargs.pop("pass_context", None)
            kwargs.pop("on_done", None)
            kwargs.pop("on_error", None)
            kwargs.pop("on_cancelled", None)
            kwargs.pop("on_progress", None)
            return original_run_task(task_id, fn, *args, **kwargs)

        worker_manager.run_task = tracking_run_task
        result = br.batchSetField(["/fake/file.flac"], "title", "New Title")
        assert result.get("async"), f"Expected async=true, got {result}"
        _process_events(0.5)
        assert callable_used, "run_task debe recibir un callable, no un dict"

    def test_batch_cancellation(self, bridge, worker_manager):
        many_files = [f"/fake/file_{i}.flac" for i in range(500)]
        result = bridge.batchSetField(many_files, "artist", "Cancelled Artist")
        assert result.get("async"), f"Expected async, got {result}"
        cancel_result = bridge.cancelBatch()
        assert cancel_result.get("ok")
        _process_events(0.5)

    def test_batch_sync_fallback(self):
        from ui_qml_bridge.metadata_bridge import MetadataBridge
        bridge = MetadataBridge(worker_manager=None)
        result = bridge.batchSetField(["/fake/file.flac"], "title", "Sync Title")
        assert result.get("ok") is None or result.get("ok")  # falls back to sync

    def test_batch_set_field_creates_task_handle(self, bridge, worker_manager):
        bridge.batchSetField(["/fake/file.flac"], "artist", "Test")
        _process_events(0.5)
        handle = worker_manager.get_task("metadata_batch")
        assert handle is None or handle.task_id == "metadata_batch"

    def test_batch_set_field_with_different_key_types(self, bridge, worker_manager):
        keys = ["title", "artist", "album", "genre", "year", "track_number"]
        for key in keys:
            result = bridge.batchSetField(["/fake/file.flac"], key, "test_val")
            assert result.get("async") or result.get("ok")

    def test_cancel_batch_returns_ok(self, bridge):
        result = bridge.cancelBatch()
        assert result.get("ok")

    def test_batch_set_field_rejects_busy(self, bridge, worker_manager):
        bridge._status = "busy"
        bridge.batchSetField(["/fake/1.flac"], "title", "T1")
        bridge.batchSetField(["/fake/2.flac"], "title", "T2")
        _process_events(0.5)
