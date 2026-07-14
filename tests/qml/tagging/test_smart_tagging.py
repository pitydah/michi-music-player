"""Tests for SmartTaggingBridge detectFormat and service handling."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

pytestmark = pytest.mark.isolation


class TestSmartTaggingDetectFormat:
    @pytest.fixture
    def bridge(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        return SmartTaggingBridge()

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

    def test_no_worker_manager(self):
        from ui_qml_bridge.smart_tagging_bridge import SmartTaggingBridge
        bridge = SmartTaggingBridge(service=MagicMock())
        assert bridge._wm is None
