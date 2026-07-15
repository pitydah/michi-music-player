<<<<<<< Updated upstream
"""Test no candidates, missing service, generation failure scenarios."""
=======
<<<<<<< HEAD
"""Negative tests for Mix: null bridge, empty results, invalid inputs, edge cases."""
=======
"""Test no candidates, missing service, generation failure scenarios."""
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

<<<<<<< Updated upstream

@pytest.fixture
def empty_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = []
    mqs.recent.return_value = []
    mqs.most_played.return_value = []
    mqs.unplayed.return_value = []
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = []
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
    return mqs


@pytest.fixture
def failing_mqs():
    mqs = MagicMock()
    mqs.favorites.side_effect = RuntimeError("DB connection failed")
    return mqs
=======
<<<<<<< HEAD
pytestmark = [pytest.mark.qml_module("mix")]
>>>>>>> Stashed changes


class TestMixNegative:
    def test_no_query_service_returns_no_songs(self):
        bridge = MixBridge()
        result = bridge.loadMix("favorites")
        assert result["ok"] is False
        assert len(bridge.currentSongs) == 0

<<<<<<< Updated upstream
=======
    def test_null_bridge_play(self):
=======

@pytest.fixture
def empty_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = []
    mqs.recent.return_value = []
    mqs.most_played.return_value = []
    mqs.unplayed.return_value = []
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = []
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
    return mqs


@pytest.fixture
def failing_mqs():
    mqs = MagicMock()
    mqs.favorites.side_effect = RuntimeError("DB connection failed")
    return mqs


class TestMixNegative:
    def test_no_query_service_returns_no_songs(self):
        bridge = MixBridge()
        result = bridge.loadMix("favorites")
        assert result["ok"] is False
        assert len(bridge.currentSongs) == 0

>>>>>>> Stashed changes
    def test_no_candidates_shows_empty_songs(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("favorites")
        assert result["ok"] is False
        assert result["count"] == 0
        assert bridge.errorMessage != ""

    def test_no_candidates_for_recent(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("recent")
        assert result["ok"] is False
        assert result["count"] == 0

    def test_no_candidates_for_unplayed(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("unplayed")
        assert result["ok"] is False
        assert result["count"] == 0

    def test_no_candidates_for_rediscovery(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("rediscovery")
        assert result["ok"] is False
        assert result["count"] == 0

    def test_db_failure_gracefully_handled(self, failing_mqs):
        bridge = MixBridge(query_service=failing_mqs)
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 0
        assert bridge.errorMessage != ""

    def test_no_track_action_service_play_mix(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test", "artist": "A"}]
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] in ("NO_PLAYBACK", "NO_TRACK_ID")

    def test_no_playlist_bridge_save_as_playlist(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test", "artist": "A"}]
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] == "NO_PLAYLIST_BRIDGE"

    def test_play_empty_mix_returns_false(self):
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        bridge = MixBridge()
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

<<<<<<< Updated upstream
    def test_enqueue_empty_mix_returns_false(self):
=======
<<<<<<< HEAD
    def test_null_bridge_enqueue(self):
=======
    def test_enqueue_empty_mix_returns_false(self):
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        bridge = MixBridge()
        result = bridge.enqueueMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

<<<<<<< Updated upstream
    def test_save_empty_mix_returns_false(self):
=======
<<<<<<< HEAD
    def test_null_bridge_save_playlist(self):
>>>>>>> Stashed changes
        bridge = MixBridge()
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] in ("EMPTY_MIX", "NO_PLAYLIST_BRIDGE")

<<<<<<< Updated upstream
    def test_explain_empty_mix_returns_false(self):
=======
    def test_null_bridge_explain(self):
=======
    def test_save_empty_mix_returns_false(self):
        bridge = MixBridge()
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] in ("EMPTY_MIX", "NO_PLAYLIST_BRIDGE")

    def test_explain_empty_mix_returns_false(self):
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        bridge = MixBridge()
        result = bridge.explainCurrentMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

<<<<<<< Updated upstream
    def test_save_with_empty_name_returns_false(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs, playlist_bridge=MagicMock())
        bridge._current_songs = [{"track_id": 1}]
=======
<<<<<<< HEAD
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
=======
    def test_save_with_empty_name_returns_false(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs, playlist_bridge=MagicMock())
        bridge._current_songs = [{"track_id": 1}]
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
        result = bridge.saveMixAsPlaylist("")
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_NAME"

<<<<<<< Updated upstream
    def test_play_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.playFromIndex(0)
=======
<<<<<<< HEAD
    def test_save_playlist_no_playlist_bridge(self):
        bridge = MixBridge(query_service=MagicMock(), track_action_service=MagicMock())
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Test")
>>>>>>> Stashed changes
        assert result["ok"] is False
        assert result["error_code"] == "NO_TRACK_ID"

    def test_enqueue_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.enqueueTrack(0)
        assert result["ok"] is False
<<<<<<< Updated upstream
        assert result["error_code"] == "NO_TRACK_ID"
=======
=======
    def test_play_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.playFromIndex(0)
        assert result["ok"] is False
        assert result["error_code"] == "NO_TRACK_ID"

    def test_enqueue_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.enqueueTrack(0)
        assert result["ok"] is False
        assert result["error_code"] == "NO_TRACK_ID"
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes

    def test_partial_failure_report_empty(self):
        bridge = MixBridge()
        result = bridge.partialFailureReport()
        assert result["ok"] is True
        assert result["has_failures"] is False
<<<<<<< Updated upstream
=======
<<<<<<< HEAD
=======
>>>>>>> Stashed changes

    def test_unknown_mix_type_returns_empty(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("nonexistent_type")
        assert result["ok"] is False
        assert result["count"] == 0

    def test_loadmix_with_exception_clears_songs(self, failing_mqs):
        bridge = MixBridge(query_service=failing_mqs)
        bridge._current_songs = [{"track_id": 99, "title": "Old"}]
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 0
        assert bridge.errorMessage != ""

    def test_mix_with_no_error_message_on_success(self, empty_mqs):
        bridge = MixBridge(query_service=empty_mqs)
        result = bridge.loadMix("favorites")
        if not result["ok"]:
            assert bridge.errorMessage != ""
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
