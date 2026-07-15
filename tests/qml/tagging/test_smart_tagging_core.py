from __future__ import annotations
"""DY — Smart Tagging Core: candidates, confidence, preview, accept/reject, batch, cancellation, backup, verify, rollback."""

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


class TestSmartTaggingCore:
    @pytest.fixture
    def mock_service(self):
        svc = MagicMock()
        svc.suggest_for_track.return_value = [
            MagicMock(field="artist", current="Unknown", suggested="Real Artist",
                      confidence=0.95, source="MusicBrainz", warning=""),
            MagicMock(field="album", current="", suggested="Real Album",
                      confidence=0.88, source="MusicBrainz", warning=""),
            MagicMock(field="genre", current="", suggested="Rock",
                      confidence=0.72, source="AcousticBrainz", warning=""),
        ]
        return svc

    @pytest.fixture
    def mock_qs(self):
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/test.flac",
                                                  "title": "Song", "artist": "Unknown"}
        return qs

    @pytest.fixture
    def mock_wm(self):
        wm = MagicMock()
        def run_task(name, task, **kw):
            on_done = kw.get("on_done")
            try:
                result = task(FakeCtx())
                if on_done:
                    on_done(result)
            except Exception as e:
                on_error = kw.get("on_error")
                if on_error:
                    on_error("ERROR", str(e))
            return True
        wm.run_task.side_effect = run_task
        return wm

    @pytest.fixture
    def bridge(self, mock_service, mock_qs, mock_wm):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge(service=mock_service, query_service=mock_qs, worker_manager=mock_wm)

    def test_candidates_have_confidence(self, bridge):
        bridge.scanTrackById(1)
        for s in bridge.suggestions:
            assert "confidence" in s
            assert isinstance(s["confidence"], (int, float))

    def test_preview_before_apply(self, bridge):
        bridge.scanTrackById(1)
        assert bridge.status == "review"
        assert len(bridge.suggestions) == 3

    def test_accept_all_selects_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "field": "artist", "selected": False},
            {"id": 1, "field": "album", "selected": False},
        ]
        bridge.acceptAll()
        assert all(s["selected"] for s in bridge._suggestions)

    def test_reject_all_deselects_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "selected": True},
            {"id": 1, "selected": True},
        ]
        bridge.rejectAll()
        assert not any(s["selected"] for s in bridge._suggestions)

    def test_batch_scan_happy_path(self, bridge, mock_qs):
        mock_qs.fetch_track_internal.side_effect = [
            {"id": 1, "filepath": "/a.flac", "title": "A", "artist": "X"},
            {"id": 2, "filepath": "/b.flac", "title": "B", "artist": "Y"},
        ]
        result = bridge.scanBatch([1, 2])
        assert result["ok"] is True

    def test_cancellation_during_scan(self, bridge):
        bridge._status = "scanning"
        bridge._suggestions = [{"id": 0, "field": "artist"}]
        result = bridge.cancelScan()
        assert result["ok"] is True
        assert bridge.status == "cancel_requested"
        assert bridge.suggestions == []

    def test_backup_created_on_apply(self, bridge):
        bridge._current_filepath = "/test.flac"
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "New Artist"}]
        bridge._selected_ids = {0}
        bridge._status = "review"
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/backup/test.flac.bak"
            write.return_value = {"ok": True}
            verify.return_value = {"ok": True}
            result = bridge.applySelected()
            assert result["ok"] is True
            backup.assert_called_once_with("/test.flac")

    def test_rollback_on_write_failure(self, bridge):
        bridge._current_filepath = "/test.flac"
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "New"}]
        bridge._selected_ids = {0}
        bridge._status = "review"
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/backup/test.flac.bak"
            write.return_value = {"ok": False, "error_code": "WRITE_FAILED"}
            verify.return_value = {"ok": True}
            bridge.applySelected()
            assert bridge.status == "error"
            roll.assert_called_once()

    def test_rollback_on_verify_failure(self, bridge):
        bridge._current_filepath = "/test.flac"
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "New"}]
        bridge._selected_ids = {0}
        bridge._status = "review"
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.rollback_tags") as roll, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/backup/test.flac.bak"
            write.return_value = {"ok": True}
            verify.return_value = {"ok": False}
            bridge.applySelected()
            assert bridge.status == "error"
            roll.assert_called_once()

    def test_verify_after_successful_apply(self, bridge):
        bridge._current_filepath = "/test.flac"
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "New"}]
        bridge._selected_ids = {0}
        bridge._status = "review"
        with patch("ui_qml_bridge.smart_tagging_bridge.load_tags") as load, \
             patch("ui_qml_bridge.smart_tagging_bridge.apply_patch") as patch_tags, \
             patch("ui_qml_bridge.smart_tagging_bridge.create_backup") as backup, \
             patch("ui_qml_bridge.smart_tagging_bridge.write_tags_safe") as write, \
             patch("ui_qml_bridge.smart_tagging_bridge.verify_changes") as verify:
            load.return_value = MagicMock()
            patch_tags.return_value = MagicMock(dirty=True)
            backup.return_value = "/backup/test.flac.bak"
            write.return_value = {"ok": True}
            verify.return_value = {"ok": True}
            bridge.applySelected()
            verify.assert_called_once()

    def test_batch_scan_rejects_when_busy(self, bridge):
        bridge._status = "scanning"
        result = bridge.scanBatch([1, 2, 3])
        assert result["ok"] is False

    def test_single_scan_rejects_when_applying(self, bridge):
        bridge._status = "applying"
        result = bridge.scanTrackById(1)
        assert result["ok"] is False

    def test_confidence_threshold_selection(self, bridge):
        bridge._suggestions = [
            {"id": 0, "confidence": 0.95, "selected": False},
            {"id": 1, "confidence": 0.65, "selected": False},
            {"id": 2, "confidence": 0.80, "selected": False},
        ]
        bridge.selectHighConfidence(0.8)
        assert bridge._suggestions[0]["selected"] is True
        assert bridge._suggestions[1]["selected"] is False
        assert bridge._suggestions[2]["selected"] is True

    def test_status_transitions_on_scan(self, bridge):
        assert bridge.status == "idle"
        bridge.scanTrackById(1)
        assert bridge.status in ("scanning", "queued", "review")
