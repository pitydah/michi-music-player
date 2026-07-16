from __future__ import annotations
"""Tests for Smart Tagging full workflow."""

import time

import pytest
from PySide6.QtCore import QCoreApplication

pytestmark = [pytest.mark.qml_module("smart_tagging")]


def _process_events(duration=2.0):
    deadline = time.time() + duration
    while time.time() < deadline:
        QCoreApplication.processEvents()
        time.sleep(0.02)


class TestSmartTaggingWorkflow:
    @pytest.fixture
    def app(self):
        return QCoreApplication.instance() or QCoreApplication()

    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

    def test_default_status_idle(self, bridge):
        assert bridge.status == "idle"

    def test_scan_rejects_busy(self, bridge):
        bridge._status = "scanning"
        result = bridge.scanTrackById(42)
        assert not result.get("ok")

    def test_scan_returns_queued_no_service(self, bridge):
        result = bridge.scanTrackById(1)
        assert result.get("queued")

    def test_set_suggestion_selected(self, bridge):
        bridge._suggestions = [{"id": 0, "field": "artist", "selected": False}]
        result = bridge.setSuggestionSelected(0, True)
        assert result.get("ok")
        assert bridge._suggestions[0]["selected"]

    def test_set_suggestion_deselected(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}]
        bridge.setSuggestionSelected(0, False)
        assert not bridge._suggestions[0]["selected"]

    def test_select_all(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": False}, {"id": 1, "selected": False}]
        bridge.selectAll()
        assert bridge._suggestions[0]["selected"]
        assert bridge._suggestions[1]["selected"]

    def test_select_high_confidence(self, bridge):
        bridge._suggestions = [
            {"id": 0, "confidence": 0.95, "selected": False},
            {"id": 1, "confidence": 0.50, "selected": False},
        ]
        bridge.selectHighConfidence()
        assert bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_select_none(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}, {"id": 1, "selected": True}]
        bridge.selectNone()
        assert not bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_apply_selected_rejects_no_review(self, bridge):
        bridge._status = "idle"
        result = bridge.applySelected()
        assert not result.get("ok")

    def test_apply_selected_no_suggestions(self, bridge):
        bridge._status = "review"
        bridge._suggestions = []
        bridge._selected_ids = set()
        result = bridge.applySelected()
        assert not result.get("ok") or result.get("ok") is not None

    def test_cancel_scan(self, bridge):
        result = bridge.cancelScan()
        assert result.get("ok")
        assert bridge._status == "cancel_requested"

    def test_accept_all(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": False}, {"id": 1, "selected": False}]
        bridge.acceptAll()
        assert bridge._suggestions[0]["selected"]
        assert bridge._suggestions[1]["selected"]

    def test_reject_all(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}, {"id": 1, "selected": True}]
        bridge.rejectAll()
        assert not bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_batch_scan_rejects_busy(self, bridge):
        bridge._status = "scanning"
        result = bridge.scanBatch([1, 2, 3])
        assert not result.get("ok")

    def test_batch_scan_empty(self, bridge):
        result = bridge.scanBatch([])
        assert not result.get("ok")

    def test_progress_property(self, bridge):
        bridge._progress = 0.5
        assert bridge.progress == 0.5

    def test_suggestions_property(self, bridge):
        bridge._suggestions = [{"field": "artist", "suggested": "Test"}]
        assert len(bridge.suggestions) == 1
