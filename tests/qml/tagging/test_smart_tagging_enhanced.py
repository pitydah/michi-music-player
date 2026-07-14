"""CL — Smart Tagging enhanced: candidates, confidence, preview, accept/reject, batch, cancel, rollback."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.isolation


class TestSmartTagging:
    @pytest.fixture
    def mock_service(self):
        svc = MagicMock()
        svc.suggest_for_track.return_value = [
            MagicMock(field="artist", current="Unknown", suggested="Real Artist",
                      confidence=0.95, source="MusicBrainz", warning=""),
            MagicMock(field="genre", current="", suggested="Rock",
                      confidence=0.82, source="AcousticBrainz", warning=""),
        ]
        return svc

    @pytest.fixture
    def mock_qs(self):
        qs = MagicMock()
        qs.fetch_track_internal.return_value = {"id": 1, "filepath": "/test.flac",
                                                  "title": "Song", "artist": "Unknown"}
        return qs

    @pytest.fixture
    def bridge(self, mock_service, mock_qs):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge(service=mock_service, query_service=mock_qs)

    def test_initial_state(self, bridge):
        assert bridge.status == "idle"
        assert bridge.suggestions == []
        assert bridge.progress == 0.0

    def test_scan_track_success(self, bridge):
        result = bridge.scanTrackById(1)
        assert result["ok"] is True

    def test_scan_track_no_service(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        result = bridge.scanTrackById(1)
        assert result["ok"] is False

    def test_set_suggestion_selected(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist", "current": "A",
                                 "suggested": "B", "confidence": 0.9, "selected": False}]
        result = bridge.setSuggestionSelected(0, True)
        assert result["ok"] is True
        assert bridge._suggestions[0]["selected"] is True

    def test_set_suggestion_deselected(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist", "current": "A",
                                 "suggested": "B", "confidence": 0.9, "selected": True}]
        result = bridge.setSuggestionSelected(0, False)
        assert result["ok"] is True
        assert bridge._suggestions[0]["selected"] is False

    def test_select_all(self, bridge):
        bridge._suggestions = [
            {"id": 0, "field": "artist", "selected": False},
            {"id": 1, "field": "genre", "selected": False},
        ]
        result = bridge.selectAll()
        assert result["ok"] is True
        assert all(s["selected"] for s in bridge._suggestions)

    def test_select_high_confidence(self, bridge):
        bridge._suggestions = [
            {"id": 0, "field": "artist", "confidence": 0.95, "selected": False},
            {"id": 1, "field": "genre", "confidence": 0.5, "selected": False},
        ]
        result = bridge.selectHighConfidence(0.8)
        assert result["ok"] is True
        assert bridge._suggestions[0]["selected"] is True
        assert bridge._suggestions[1]["selected"] is False

    def test_select_none(self, bridge):
        bridge._suggestions = [
            {"id": 0, "field": "artist", "selected": True},
            {"id": 1, "field": "genre", "selected": True},
        ]
        result = bridge.selectNone()
        assert result["ok"] is True
        assert all(not s["selected"] for s in bridge._suggestions)

    def test_accept_all(self, bridge):
        result = bridge.acceptAll()
        assert result["ok"] is True

    def test_reject_all(self, bridge):
        result = bridge.rejectAll()
        assert result["ok"] is True

    def test_cancel_scan(self, bridge):
        result = bridge.cancelScan()
        assert result["ok"] is True
        assert bridge.status == "cancel_requested"
        assert bridge.suggestions == []

    def test_refresh(self, bridge):
        bridge.refresh()

    def test_apply_selected_no_suggestions(self, bridge):
        result = bridge.applySelected()
        assert result["ok"] is False

    def test_apply_selected_no_selection(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist", "suggested": "B"}]
        bridge._status = "review"
        bridge._current_filepath = "/test.flac"
        result = bridge.applySelected()
        assert result["ok"] is False

    def test_scan_batch_empty(self, bridge):
        result = bridge.scanBatch([])
        assert result["ok"] is False

    def test_set_service(self, bridge, mock_service):
        bridge.set_service(mock_service)
        assert bridge._service is mock_service

    def test_batch_results_empty_initially(self, bridge):
        assert bridge.batchResults == []

    def test_progress_initial(self, bridge):
        assert bridge.progress == 0.0
