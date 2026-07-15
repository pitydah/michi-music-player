"""Tests for Smart Tagging v12 — SmartTaggingService."""
from unittest.mock import MagicMock

import pytest


class TestSmartTaggingBridgeCreation:
    def test_requires_service(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        with pytest.raises(Exception):
            SmartTaggingBridge()

    def test_requires_worker_manager(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        with pytest.raises(Exception):
            SmartTaggingBridge(service=MagicMock())

    def test_creation(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert stb is not None

    def test_status_default(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert stb.status == "idle"

    def test_suggestions_default(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert len(stb.suggestions) == 0

    def test_progress_default(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        assert stb.progress == 0.0

    def test_scan_track_by_id(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock(),
                                  query_service=MagicMock())
        result = stb.scanTrackById(1)
        assert isinstance(result, dict)

    def test_set_suggestion_selected(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        result = stb.setSuggestionSelected(0, True)
        assert result.get("ok")

    def test_select_all(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        result = stb.selectAll()
        assert result.get("ok")

    def test_cancel_scan(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        stb = SmartTaggingBridge(service=MagicMock(), worker_manager=MagicMock())
        result = stb.cancelScan()
        assert result.get("ok")
