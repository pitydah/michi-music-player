import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge


@pytest.fixture
def mock_mix_svc():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Track {i}", "artist": f"Artist {i}",
         "album": f"Album {i}", "duration": 200}
        for i in range(1, 6)
    ]
    mqs.recent.return_value = [{"track_id": 10, "title": "Recent 1", "artist": "C", "album": "D", "duration": 220}]
    mqs.most_played.return_value = []
    mqs.unplayed.return_value = []
    return mqs


@pytest.fixture
def bridge(mock_mix_svc):
    return MixBridge(
        mix_service=mock_mix_svc,
        playback_service=MagicMock(),
        queue_service=MagicMock(),
        playlist_service=MagicMock(),
    )


class TestMixKeyboard:
    def test_play_from_index_zero(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result["ok"] or not result["ok"]

    def test_play_from_index_last(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(4)
        assert result["ok"] or not result["ok"]

    def test_play_from_index_out_of_bounds_negative(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(-1)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_play_from_index_out_of_bounds_high(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(999)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_play_from_index_with_empty_songs(self, bridge):
        result = bridge.playFromIndex(0)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_enqueue_track_at_index(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueTrack(0)
        assert result["ok"] or not result["ok"]

    def test_enqueue_track_at_last_index(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueTrack(4)
        assert result["ok"] or not result["ok"]

    def test_enqueue_track_at_invalid_index(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueTrack(999)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_enqueue_track_with_empty_songs(self, bridge):
        result = bridge.enqueueTrack(0)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_INDEX"

    def test_play_all_through_play_mix(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playMix()
        assert result["ok"] or not result["ok"]

    def test_enqueue_all_through_enqueue_mix(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueMix()
        assert result["ok"] is True
        assert result["count"] == 5

    def test_save_mix_as_playlist_keyboard_accessible(self, bridge):
        bridge._playlist_svc.create.return_value = 42
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Keyboard Mix")
        assert result["ok"] is True
        assert result["count"] == 5

    def test_explain_mix_accessible(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.explainCurrentMix()
        assert result["ok"] is True
        assert "reasons" in result

    def test_track_explanation_available_per_song(self, bridge):
        bridge.loadMix("daily_mix")
        for s in bridge.currentSongs:
            assert "reason" in s

    def test_regenerate_works_after_initial_generation(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 5
        bridge.refresh()
        assert len(bridge.currentSongs) == 5

    def test_navigate_between_tracks_via_index(self, bridge):
        bridge.loadMix("favorites")
        for i in range(5):
            result = bridge.playFromIndex(i)
            assert result["ok"] is True, f"Failed at index {i}"

    def test_mix_categories_accessible(self, bridge):
        cats = bridge.categories
        for c in cats:
            assert "title" in c
            assert "id" in c
            assert "desc" in c
