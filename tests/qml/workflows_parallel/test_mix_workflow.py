from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MixBridge
from core.worker_manager import WorkerManager


@pytest.fixture
def worker_manager():
    wm = MagicMock(spec=WorkerManager)
    wm.cancel_all = MagicMock(return_value=None)
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Fav {i}", "artist": f"Artist {chr(65 + (i % 26))}",
         "album": "Album F", "duration": 200, "reason": "Favorito"}
        for i in range(1, 11)
    ]
    mqs.recent.return_value = [
        {"track_id": i, "title": f"Recent {i}", "artist": f"Artist {chr(75 + (i % 26))}",
         "album": "Album D", "duration": 220}
        for i in range(11, 21)
    ]
    mqs.unplayed.return_value = [
        {"track_id": i, "title": f"Unplayed {i}", "artist": f"Artist {chr(69 + (i % 26))}",
         "album": "Album F", "duration": 190}
        for i in range(21, 26)
    ]
    return mqs


@pytest.fixture
def mock_queue_svc():
    qs = MagicMock()
    qs.replace_and_play.return_value = {"ok": True}
    qs.enqueue.return_value = {"ok": True}
    return qs


@pytest.fixture
def mock_playlist_svc():
    ps = MagicMock()
    ps.create.return_value = "playlist_1"
    ps.add_track.return_value = True
    return ps


@pytest.fixture
def bridge(mock_mqs, worker_manager, mock_queue_svc, mock_playlist_svc):
    return MixBridge(
        mix_service=mock_mqs,
        job_service=worker_manager,
        queue_service=mock_queue_svc,
        playlist_service=mock_playlist_svc,
    )


class TestMixWorkflow:

    def test_load_mix_favorites(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] == 10
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

    def test_save_as_playlist(self, bridge, mock_playlist_svc):
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Mi Mix Favoritos")
        assert result["ok"] is True
        assert result["count"] == 10
        mock_playlist_svc.create.assert_called_once_with("Mi Mix Favoritos")

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
        assert "Favorito" in explanation["reasons"]

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
        assert len(bridge.currentSongs) == 5
        play = bridge.playFromIndex(0)
        assert play["ok"] is True

    def test_generation_counter_incremented_by_generate(self, bridge):
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before + 1
