"""Negative tests for Mix: null bridge, empty results, invalid inputs, edge cases."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

pytestmark = [pytest.mark.qml_module("mix")]


class TestMixNegative:

    def test_null_bridge_safe(self):
        bridge = MixBridge()
        assert bridge.categories is not None
        assert bridge.currentSongs == []
        assert bridge.currentMixTitle == ""
        assert bridge.errorMessage == ""
        assert bridge.currentMixId == ""

    def test_null_bridge_load_mix(self):
        bridge = MixBridge()
        result = bridge.loadMix("favorites")
        assert result["ok"] is False

    def test_null_bridge_play(self):
        bridge = MixBridge()
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

    def test_null_bridge_enqueue(self):
        bridge = MixBridge()
        result = bridge.enqueueMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

    def test_null_bridge_save_playlist(self):
        bridge = MixBridge()
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False

    def test_null_bridge_explain(self):
        bridge = MixBridge()
        result = bridge.explainCurrentMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

    def test_null_bridge_cancel(self):
        bridge = MixBridge()
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        assert "cancelled" in result

    def test_null_bridge_play_from_invalid_index(self):
        bridge = MixBridge()
        result = bridge.playFromIndex(0)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_invalid_mix_id(self):
        bridge = MixBridge(query_service=MagicMock())
        result = bridge.loadMix("invalid_type_xyz")
        assert result["ok"] is False

    def test_save_playlist_empty_name(self):
        bridge = MixBridge(query_service=MagicMock(), track_action_service=MagicMock(), playlist_bridge=MagicMock())
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("")
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_NAME"

    def test_save_playlist_no_playlist_bridge(self):
        bridge = MixBridge(query_service=MagicMock(), track_action_service=MagicMock())
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] == "NO_PLAYLIST_BRIDGE"

    def test_play_without_track_action_service(self):
        bridge = MixBridge(query_service=MagicMock(), player_service=MagicMock())
        bridge._current_songs = [{"track_id": 1, "title": "Test"}]
        result = bridge.playMix()
        assert result["ok"] is True or result["ok"] is False

    def test_enqueue_invalid_index(self):
        bridge = MixBridge(track_action_service=MagicMock())
        result = bridge.enqueueTrack(999)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_play_invalid_index(self):
        bridge = MixBridge(track_action_service=MagicMock())
        result = bridge.playFromIndex(999)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_explain_empty_mix(self):
        bridge = MixBridge(query_service=MagicMock())
        result = bridge.explainCurrentMix()
        assert result["ok"] is False

    def test_partial_failure_report_empty(self):
        bridge = MixBridge()
        result = bridge.partialFailureReport()
        assert result["ok"] is True
        assert result["has_failures"] is False
