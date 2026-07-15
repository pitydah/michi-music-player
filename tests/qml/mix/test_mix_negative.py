from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MixBridge


@pytest.fixture
def empty_mqs():
    svc = MagicMock()
    svc.favorites.return_value = []
    svc.recent.return_value = []
    svc.unplayed.return_value = []
    svc.rediscovery.return_value = []
    svc.most_played.return_value = []
    svc.by_field.return_value = []
    svc.by_decade.return_value = []
    svc.by_year.return_value = []
    svc.high_quality.return_value = []
    return svc


@pytest.fixture
def failing_mqs():
    svc = MagicMock()
    svc.favorites.side_effect = RuntimeError("DB fail")
    svc.recent.side_effect = RuntimeError("DB fail")
    svc.unplayed.side_effect = RuntimeError("DB fail")
    svc.rediscovery.side_effect = RuntimeError("DB fail")
    svc.most_played.side_effect = RuntimeError("DB fail")
    svc.by_field.side_effect = RuntimeError("DB fail")
    svc.by_decade.side_effect = RuntimeError("DB fail")
    svc.by_year.side_effect = RuntimeError("DB fail")
    svc.high_quality.side_effect = RuntimeError("DB fail")
    return svc


class TestMixNegative:
    def test_no_query_service_returns_no_songs(self):
        bridge = MixBridge()
        result = bridge.loadMix("favorites")
        assert result["ok"] is False
        assert len(bridge.currentSongs) == 0

    def test_no_candidates_shows_empty_songs(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result.get("count") == 0

    def test_no_candidates_for_recent(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert result.get("count") == 0

    def test_no_candidates_for_unplayed(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        result = bridge.loadMix("unplayed")
        assert result["ok"] is True

    def test_no_candidates_for_rediscovery(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        result = bridge.loadMix("rediscovery")
        assert result["ok"] is True

    def test_db_failure_gracefully_handled(self, failing_mqs):
        bridge = MixBridge(mix_service=failing_mqs)
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 0

    def test_no_playback_service_play_mix(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test", "artist": "A"}]
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] in ("NO_PLAYBACK", "NO_TRACK_ID")

    def test_no_playlist_service_save_as_playlist(self):
        bridge = MixBridge()
        bridge._current_songs = [{"track_id": 1, "title": "Test", "artist": "A"}]
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] == "NO_PLAYLIST_SERVICE"

    def test_play_empty_mix_returns_false(self):
        bridge = MixBridge()
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

        bridge = MixBridge()
        result = bridge.enqueueMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

        bridge = MixBridge()
        result = bridge.saveMixAsPlaylist("Test")
        assert result["ok"] is False
        assert result["error_code"] in ("EMPTY_MIX", "NO_PLAYLIST_SERVICE")

        bridge = MixBridge()
        result = bridge.explainCurrentMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

        result = bridge.saveMixAsPlaylist("")
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_NAME"

    def test_enqueue_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.enqueueTrack(0)
        assert result["ok"] is False

    def test_play_from_index_with_no_track_id(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.playFromIndex(0)
        assert result["ok"] is False
        assert result["error_code"] == "NO_TRACK_ID"

    def test_enqueue_from_index_with_no_track_id_again(self):
        bridge = MixBridge()
        bridge._current_songs = [{"title": "No ID"}]
        result = bridge.enqueueTrack(0)
        assert result["ok"] is False
        assert result["error_code"] == "NO_TRACK_ID"

    def test_partial_failure_report_empty(self):
        bridge = MixBridge()
        result = bridge.partialFailureReport()
        assert result["ok"] is True
        assert result["has_failures"] is False

    def test_unknown_mix_type_returns_error(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        result = bridge.loadMix("nonexistent_type")
        assert result["ok"] is False
        assert result.get("error_code") == "UNKNOWN_CATEGORY"

    def test_loadmix_with_exception_clears_songs(self, failing_mqs):
        bridge = MixBridge(mix_service=failing_mqs)
        bridge._current_songs = [{"track_id": 99, "title": "Old"}]
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 0

    def test_mix_with_no_error_message_on_success(self, empty_mqs):
        bridge = MixBridge(mix_service=empty_mqs)
        bridge.loadMix("favorites")
        assert bridge.errorMessage == ""
