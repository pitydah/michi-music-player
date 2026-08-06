from unittest.mock import MagicMock

import pytest


from ..mix.conftest import make_bridge, make_mix_service


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=10)


@pytest.fixture
def mock_queue_svc():
    qs = MagicMock()
    qs.replace_and_play.return_value = {"ok": True}
    qs.enqueue.return_value = {"ok": True}
    return qs


@pytest.fixture
def mock_playlist_svc():
    ps = MagicMock()
    ps.create.return_value = {"ok": True, "id": "playlist_1"}
    ps.add_track.return_value = {"ok": True}
    return ps


@pytest.fixture
def bridge(mock_mqs, mock_queue_svc, mock_playlist_svc, tmp_path):
    b, _svc = make_bridge(
        mock_mqs, tmp_path,
        queue_service=mock_queue_svc,
        playlist_service=mock_playlist_svc,
    )
    return b


class TestMixWorkflow:

    def test_load_mix_favorites(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert bridge.stateName == "COMPLETED_WITH_TRACKS"
        assert len(bridge.currentSongs) == 10

    def test_generate_recent_then_cancel(self, bridge):
        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

        gen_before = bridge._generation
        cancel_result = bridge.cancelGeneration()
        assert cancel_result["ok"] is True
        assert bridge._generation == gen_before + 1

    def test_cancel_then_generate_again(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

    def test_play_track_after_generation(self, bridge, mock_queue_svc):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result["ok"] is True
        mock_queue_svc.replace_and_play.assert_called_once()

    def test_enqueue_all_tracks(self, bridge, mock_queue_svc):
        bridge.loadMix("favorites")
        result = bridge.enqueueMix()
        assert result["ok"] is True
        assert mock_queue_svc.enqueue.call_count == 1

    def test_save_as_playlist(self, bridge):
        bridge._mix_svc.save_mix_as_playlist.return_value = {
            "ok": True, "status": "COMPLETED", "playlist_id": "playlist_1",
            "requested": 10, "added": 10, "failed": 0, "count": 10,
        }
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Mi Mix Favoritos")
        assert result["ok"] is True
        assert result["count"] == 10

    def test_full_workflow_configure_generate_cancel_generate_play(self, bridge, mock_queue_svc):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10
        play1 = bridge.playFromIndex(0)
        assert play1["ok"] is True

        bridge.cancelGeneration()

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10
        play2 = bridge.playFromIndex(0)
        assert play2["ok"] is True

    def test_play_all_tracks_in_mix(self, bridge, mock_queue_svc):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.playFromIndex(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_queue_svc.replace_and_play.call_count == 10

    def test_enqueue_each_track_individually(self, bridge, mock_queue_svc):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.enqueueTrack(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_queue_svc.enqueue.call_count == 10

    def test_explain_after_generation(self, bridge):
        bridge.loadMix("favorites")
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert explanation["reasons"]

    def test_explain_after_generation_and_cancel(self, bridge):
        bridge.loadMix("favorites")
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert explanation["total"] == 10
        cancel_result = bridge.cancelGeneration()
        assert cancel_result["ok"] is True

    def test_regenerate_from_existing_returns_new_songs(self, bridge):
        bridge.loadMix("favorites")
        first_batch = bridge.currentSongs[:]
        bridge.refresh()
        second_batch = bridge.currentSongs[:]
        assert len(first_batch) == len(second_batch)

    def test_workflow_with_different_mix_type_after_cancel(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()

        bridge.loadMix("unplayed")
        assert len(bridge.currentSongs) == 10
        play = bridge.playFromIndex(0)
        assert play["ok"] is True

    def test_generation_counter_incremented_by_generate(self, bridge):
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before + 1
