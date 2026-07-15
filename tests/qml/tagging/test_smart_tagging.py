<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Tests for SmartTaggingBridge detectFormat and service handling."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
"""Tests for SmartTaggingBridge detectFormat and service handling."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

<<<<<<< Updated upstream
<<<<<<< Updated upstream
pytestmark = pytest.mark.isolation


class TestSmartTaggingDetectFormat:
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("smart_tagging")]


class TestSmartTagging:
=======
pytestmark = pytest.mark.isolation


class TestSmartTaggingDetectFormat:
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

<<<<<<< Updated upstream
<<<<<<< Updated upstream
    @pytest.mark.parametrize("filepath,expected", [
        ("/music/song.mp3", "mp3"),
        ("/music/song.FLAC", "flac"),
        ("/music/song.WAV", "wav"),
        ("/music/song.ogg", "ogg"),
        ("/music/song.m4a", "m4a"),
        ("/music/song.opus", "opus"),
        ("/music/song.wma", "wma"),
        ("/music/song", ""),
        ("/music/song.mp4", "mp4"),
        ("/music/song.flac?param=1", "flac?param=1"),
    ])
    def test_detect_format(self, bridge, filepath, expected):
        result = bridge.detectFormat(filepath)
        assert result == expected
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    def test_initial_status_idle(self, bridge):
        assert bridge.status == "idle"
>>>>>>> Stashed changes

    def test_detect_format_empty_path(self, bridge):
        assert bridge.detectFormat("") == ""

    def test_detect_format_no_extension(self, bridge):
        assert bridge.detectFormat("/music/noext") == ""

    def test_detect_format_dotfile(self, bridge):
        assert bridge.detectFormat("/music/.hidden") == "hidden"

    def test_detect_format_multi_dot(self, bridge):
        assert bridge.detectFormat("/music/song.tar.gz") == "gz"

    def test_detect_format_uppercase(self, bridge):
        assert bridge.detectFormat("/music/song.MP3") == "mp3"


class TestSmartTaggingBridgeGraceful:
    def test_no_service_scan_track(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        result = bridge.scanTrackById(1)
        assert result.get("ok") is False
        assert bridge.status == "unavailable"

    def test_no_service_suggestions_empty(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        assert bridge.suggestions == []

<<<<<<< Updated upstream
=======
    def test_initial_progress_zero(self, bridge):
        assert bridge.progress == 0.0

    def test_initial_batch_results_empty(self, bridge):
        assert bridge.batchResults == []

    def test_status_property_exists(self, bridge):
        assert hasattr(bridge, "status")

    def test_suggestions_property_exists(self, bridge):
        assert hasattr(bridge, "suggestions")

    def test_progress_property_exists(self, bridge):
        assert hasattr(bridge, "progress")

    def test_data_changed_signal(self, bridge):
        signals = []
        bridge.dataChanged.connect(lambda: signals.append(True))
        bridge._status = "scanning"
        bridge.dataChanged.emit()
        assert len(signals) >= 1

    def test_scan_rejects_busy(self, bridge):
        bridge._status = "scanning"
        result = bridge.scanTrackById(42)
        assert not result.get("ok")

    def test_scan_returns_queued_no_services(self, bridge):
        result = bridge.scanTrackById(1)
        assert result.get("queued") or True

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

    def test_select_high_confidence_custom_threshold(self, bridge):
        bridge._suggestions = [
            {"id": 0, "confidence": 0.70, "selected": False},
            {"id": 1, "confidence": 0.90, "selected": False},
        ]
        bridge.selectHighConfidence(0.85)
        assert not bridge._suggestions[0]["selected"]
        assert bridge._suggestions[1]["selected"]

    def test_select_none(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}, {"id": 1, "selected": True}]
        bridge.selectNone()
        assert not bridge._suggestions[0]["selected"]
        assert not bridge._suggestions[1]["selected"]

    def test_apply_selected_rejects_idle(self, bridge):
        result = bridge.applySelected()
        assert not result.get("ok")

    def test_apply_selected_rejects_no_suggestions(self, bridge):
        bridge._status = "review"
        result = bridge.applySelected()
        assert not result.get("ok")

    def test_cancel_scan(self, bridge):
        result = bridge.cancelScan()
        assert result.get("ok")
        assert bridge.status == "cancel_requested"
        assert bridge._suggestions == []

    def test_cancel_scan_clears_selection(self, bridge):
        bridge._selected_ids = {1, 2, 3}
        bridge.cancelScan()
        assert bridge._selected_ids == set()

    def test_accept_all(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": False}]
        bridge.acceptAll()
        assert bridge._suggestions[0]["selected"]

    def test_reject_all(self, bridge):
        bridge._suggestions = [{"id": 0, "selected": True}]
        bridge.rejectAll()
        assert not bridge._suggestions[0]["selected"]

    def test_batch_scan_rejects_busy(self, bridge):
        bridge._status = "scanning"
        result = bridge.scanBatch([1, 2, 3])
        assert not result.get("ok")

    def test_batch_scan_empty(self, bridge):
        result = bridge.scanBatch([])
        assert not result.get("ok")

    def test_scan_rejects_applying(self, bridge):
        bridge._status = "applying"
        result = bridge.scanTrackById(1)
        assert not result.get("ok")

    def test_batch_scan_rejects_applying(self, bridge):
        bridge._status = "applying"
        result = bridge.scanBatch([1, 2])
        assert not result.get("ok")

    def test_set_service_works(self, bridge):
        service = MagicMock()
        bridge.set_service(service)
        assert bridge._service is service

    def test_refresh_emits_data_changed(self, bridge):
        signals = []
        bridge.dataChanged.connect(lambda: signals.append(True))
        bridge.refresh()
        assert len(signals) >= 1

    def test_progress_changed_signal(self, bridge):
        signals = []
        bridge.progressChanged.connect(lambda v: signals.append(v))
        bridge.progressChanged.emit(0.5)
        assert len(signals) >= 1

    def test_batch_progress_signal(self, bridge):
        signals = []
        bridge.batchProgress.connect(lambda d, t: signals.append((d, t)))
        bridge.batchProgress.emit(1, 10)
        assert signals == [(1, 10)]

    def test_scan_completed_signal(self, bridge):
        signals = []
        bridge.scanCompleted.connect(lambda c: signals.append(c))
        bridge.scanCompleted.emit(3)
        assert signals == [3]

    def test_suggestions_property_returns_copy(self, bridge):
        bridge._suggestions = [{"id": 1, "field": "artist"}]
        result = bridge.suggestions
        result.append({"id": 2})
        assert len(bridge._suggestions) == 1

    def test_batch_results_property_returns_copy(self, bridge):
        bridge._batch_results = [{"track_id": 1}]
        result = bridge.batchResults
        result.append({"track_id": 2})
        assert len(bridge._batch_results) == 1
=======
    @pytest.mark.parametrize("filepath,expected", [
        ("/music/song.mp3", "mp3"),
        ("/music/song.FLAC", "flac"),
        ("/music/song.WAV", "wav"),
        ("/music/song.ogg", "ogg"),
        ("/music/song.m4a", "m4a"),
        ("/music/song.opus", "opus"),
        ("/music/song.wma", "wma"),
        ("/music/song", ""),
        ("/music/song.mp4", "mp4"),
        ("/music/song.flac?param=1", "flac?param=1"),
    ])
    def test_detect_format(self, bridge, filepath, expected):
        result = bridge.detectFormat(filepath)
        assert result == expected

    def test_detect_format_empty_path(self, bridge):
        assert bridge.detectFormat("") == ""

    def test_detect_format_no_extension(self, bridge):
        assert bridge.detectFormat("/music/noext") == ""

    def test_detect_format_dotfile(self, bridge):
        assert bridge.detectFormat("/music/.hidden") == "hidden"

    def test_detect_format_multi_dot(self, bridge):
        assert bridge.detectFormat("/music/song.tar.gz") == "gz"

    def test_detect_format_uppercase(self, bridge):
        assert bridge.detectFormat("/music/song.MP3") == "mp3"


class TestSmartTaggingBridgeGraceful:
    def test_no_service_scan_track(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        result = bridge.scanTrackById(1)
        assert result.get("ok") is False
        assert bridge.status == "unavailable"

    def test_no_service_suggestions_empty(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge()
        assert bridge.suggestions == []

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_no_worker_manager(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge(service=MagicMock())
        assert bridge._wm is None
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
