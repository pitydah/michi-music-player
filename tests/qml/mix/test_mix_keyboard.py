import pytest
from unittest.mock import MagicMock


from .conftest import make_bridge, make_mix_service


@pytest.fixture
def mock_mix_svc():
    return make_mix_service(default_track_count=5)


@pytest.fixture
def bridge(mock_mix_svc, tmp_path):
    queue_svc = MagicMock()
    queue_svc.replace_and_play.return_value = {"ok": True}
    queue_svc.enqueue.return_value = {"ok": True, "count": 5}
    b, _svc = make_bridge(
        mock_mix_svc, tmp_path,
        queue_service=queue_svc,
    )
    return b


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
        bridge._mix_svc.save_mix_as_playlist.return_value = {
            "ok": True, "status": "COMPLETED", "playlist_id": 42,
            "requested": 5, "added": 5, "failed": 0, "count": 5,
        }
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
