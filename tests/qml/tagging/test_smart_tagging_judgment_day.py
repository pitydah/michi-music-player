from __future__ import annotations
"""Judgment Day fixes — service error propagation, canonical states, exact cancel, batch verify/rollback."""

from unittest.mock import MagicMock, patch

import pytest

pytestmark = pytest.mark.isolation


class FakeCtx:
    class Token:
        def raise_if_cancelled(self):
            pass

    token = Token()

    def report_progress(self, *a):
        pass


def _sync_wm():
    """Worker manager mock that runs tasks synchronously on the calling thread."""
    wm = MagicMock()

    def run_task(name, task, **kw):
        on_done = kw.get("on_done")
        on_error = kw.get("on_error")
        try:
            result = task(FakeCtx())
            if on_done:
                on_done(result)
        except Exception as e:  # pragma: no cover - defensive
            if on_error:
                on_error("ERROR", str(e))
        return True

    wm.run_task.side_effect = run_task
    return wm


def _capturing_wm():
    """Worker manager mock that captures the task/callbacks without running them."""
    wm = MagicMock()
    captured: dict = {}

    def run_task(name, task, **kw):
        captured["name"] = name
        captured["task"] = task
        captured["on_done"] = kw.get("on_done")
        captured["on_error"] = kw.get("on_error")
        return True

    wm.run_task.side_effect = run_task
    wm.captured = captured
    return wm


# --------------------------------------------------------------------------- #
# A. Service must not convert recognition failures into success.
# --------------------------------------------------------------------------- #
class TestServicePropagatesRecognitionFailure:
    def test_suggest_for_track_returns_error_when_identify_fails(self):
        from core.smart_tagging_service import SmartTaggingService
        qs = MagicMock()
        qs.get_track.return_value = {"filepath": "/song.flac"}
        # recognition_service=None -> identify() returns ok=False, SERVICE_UNAVAILABLE
        svc = SmartTaggingService(library_query_service=qs, recognition_service=None)

        result = svc.suggest_for_track(1)

        assert result["ok"] is False
        assert result["error"] == "SERVICE_UNAVAILABLE"
        assert result["suggestions"] == []

    def test_suggest_for_track_returns_error_when_recognition_raises(self):
        from core.smart_tagging_service import SmartTaggingService
        qs = MagicMock()
        qs.get_track.return_value = {"filepath": "/song.flac"}
        recog = MagicMock()
        recog.identify.side_effect = RuntimeError("network down")
        svc = SmartTaggingService(library_query_service=qs, recognition_service=recog)

        result = svc.suggest_for_track(1)

        assert result["ok"] is False
        assert "network down" in result["error"]
        assert result["suggestions"] == []

    def test_suggest_for_track_success_when_identify_ok(self):
        from core.smart_tagging_service import SmartTaggingService
        qs = MagicMock()
        qs.get_track.return_value = {"filepath": "/song.flac"}
        recog = MagicMock()
        # recognition.identify returns raw recognized fields; identify() wraps them.
        recog.identify.return_value = {
            "artist": "Real Artist",
            "confidence": 0.9,
            "source": "shazam",
        }
        svc = SmartTaggingService(library_query_service=qs, recognition_service=recog)

        with patch("metadata.tag_reader.read_tags", return_value=None):
            result = svc.suggest_for_track(1)

        assert result["ok"] is True
        assert len(result["suggestions"]) == 1
        assert result["suggestions"][0]["field"] == "artist"
        assert result["suggestions"][0]["proposed_value"] == "Real Artist"


# --------------------------------------------------------------------------- #
# B. Bridge must propagate the service error (single + batch).
# --------------------------------------------------------------------------- #
class TestBridgePropagatesServiceError:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        svc.suggest_for_track.return_value = {
            "ok": False, "error": "RECOGNITION_FAILED", "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/a.flac"}
        return SmartTaggingBridge(service=svc, query_service=qs, worker_manager=_sync_wm())

    def test_single_scan_sets_error_status(self, bridge):
        bridge.scanTrackById(1)
        assert bridge.status == "error"
        assert bridge.suggestions == []

    def test_batch_scan_records_per_track_error(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        svc.suggest_for_track.return_value = {
            "ok": False, "error": "RECOGNITION_FAILED", "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/a.flac"}
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=_sync_wm())

        bridge.scanBatch([1, 2])

        assert bridge.status == "review"
        results = bridge.batchResults
        assert len(results) == 2
        for r in results:
            assert r["ok"] is False
            assert r["error"] == "RECOGNITION_FAILED"
            assert r["suggestions"] == []


# --------------------------------------------------------------------------- #
# C. cancelScan must target the real scheduled task id.
# --------------------------------------------------------------------------- #
class TestCancelUsesActiveTaskId:
    def test_cancel_uses_active_task_id(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        wm = _sync_wm()
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=wm)
        # Simulate a scheduled scan task with its canonical id.
        bridge._active_task_id = "st_42"

        result = bridge.cancelScan()

        assert result["ok"] is True
        wm.cancel_task.assert_called_once_with("st_42")
        assert bridge._active_task_id is None
        assert bridge.status == "cancelled"

    def test_cancel_after_single_scan_targets_st_trackid(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        svc.suggest_for_track.return_value = {"ok": True, "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 7, "filepath": "/x.flac"}
        wm = _sync_wm()
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=wm)

        bridge.scanTrackById(7)
        assert bridge._active_task_id == "st_7"
        bridge.cancelScan()
        wm.cancel_task.assert_called_once_with("st_7")

    def test_cancel_after_batch_scan_targets_st_batch_gen(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        svc.suggest_for_track.return_value = {"ok": True, "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/x.flac"}
        wm = _sync_wm()
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=wm)

        bridge.scanBatch([1])
        assert bridge._active_task_id == "st_batch_1"
        bridge.cancelScan()
        wm.cancel_task.assert_called_once_with("st_batch_1")

    def test_cancel_without_active_task_does_not_call_cancel_task(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        wm = _sync_wm()
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=wm)
        assert bridge._active_task_id is None

        bridge.cancelScan()

        wm.cancel_task.assert_not_called()
        assert bridge._active_task_id is None


# --------------------------------------------------------------------------- #
# D. Canonical states — stale/cancel unify to "cancelled".
# --------------------------------------------------------------------------- #
class TestCanonicalStates:
    def test_cancel_requested_state_is_cancelled(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge, ST_CANCELLED
        bridge = SmartTaggingBridge(service=MagicMock(), worker_manager=_sync_wm())
        bridge.cancelScan()
        assert bridge.status == "cancelled"
        assert ST_CANCELLED == "cancelled"

    def test_stale_done_sets_cancelled(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        svc.suggest_for_track.return_value = {"ok": True, "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/x.flac"}
        wm = _capturing_wm()
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=wm)

        bridge.scanTrackById(1)  # schedules task; _done captured, not yet run
        # Bump the generation so the captured _done sees a stale gen.
        bridge._scan_counter += 1
        on_done = wm.captured["on_done"]
        on_done({"results": [], "filepath": "/x.flac"})

        assert bridge.status == "cancelled"

    def test_batch_review_unified_into_review(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge, ST_REVIEW
        svc = MagicMock()
        svc.suggest_for_track.return_value = {"ok": True, "suggestions": []}
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/x.flac"}
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=_sync_wm())

        bridge.scanBatch([1])

        # Batch no longer uses a separate "batch_review" state — it shares ST_REVIEW.
        assert bridge.status == "review"
        assert ST_REVIEW == "review"


# --------------------------------------------------------------------------- #
# E. Batch apply: backup -> write -> verify -> rollback per track.
# --------------------------------------------------------------------------- #
class TestBatchApplyLifecycle:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        svc = MagicMock()
        qs = MagicMock()
        bridge = SmartTaggingBridge(service=svc, query_service=qs, worker_manager=_sync_wm())
        bridge._status = "review"
        bridge._batch_mode = True
        bridge._batch_results = [
            {"track_id": 1, "filepath": "/a.flac",
             "suggestions": [{"field": "artist", "proposed_value": "New Artist"}]},
            {"track_id": 2, "filepath": "/b.flac",
             "suggestions": [{"field": "album", "proposed_value": "New Album"}]},
        ]
        return bridge

    def test_success_path_calls_verify(self, bridge):
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/bak/a.flac.bak"
            write.return_value = {"ok": True}
            verify.return_value = {"ok": True}

            bridge.applySelected()

            assert verify.call_count == 2
            roll.assert_not_called()
            results = bridge.batchResults
            assert all(r["ok"] for r in results)
            assert results[0]["applied"] == 1
            assert bridge.status == "completed"

    def test_rollback_on_write_failure(self, bridge):
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/bak/a.flac.bak"
            write.return_value = {"ok": False, "error_code": "WRITE_FAILED"}

            bridge.applySelected()

            assert roll.call_count == 2  # both tracks rolled back
            verify.assert_not_called()  # never reach verify when write fails
            results = bridge.batchResults
            assert all(not r["ok"] for r in results)
            assert all(r["error"] == "WRITE_FAILED" for r in results)

    def test_rollback_on_verify_failure(self, bridge):
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/bak/a.flac.bak"
            write.return_value = {"ok": True}
            verify.return_value = {"ok": False, "error_code": "VERIFY_FAILED"}

            bridge.applySelected()

            assert verify.call_count == 2
            assert roll.call_count == 2  # verify failed -> rollback each track
            results = bridge.batchResults
            assert all(not r["ok"] for r in results)
            assert all(r["error"] == "VERIFY_FAILED" for r in results)

    def test_per_track_partial_failure(self, bridge):
        """One track verifies, the other fails verify -> mixed per-track results."""
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/bak.flac.bak"
            write.return_value = {"ok": True}
            verify.side_effect = [{"ok": True}, {"ok": False}]

            bridge.applySelected()

            results = bridge.batchResults
            assert results[0]["ok"] is True
            assert results[1]["ok"] is False
            assert results[1]["error"] == "VERIFY_FAILED"
            # Only the failing track was rolled back.
            assert roll.call_count == 1
