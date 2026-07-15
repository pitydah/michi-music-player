<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Full workflow: configure -> generate -> cancel -> generate again -> play.

Tests the complete mix lifecycle:
1. Load mix type
2. Verify songs are returned
3. Cancel generation (verify real call to worker_manager)
4. Load a different mix type
5. Play a track from the results
6. Enqueue all tracks
7. Save as playlist
"""
from __future__ import annotations

=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
"""Workflow test: configure → generate → cancel → regenerate → play via MixBridge."""
import pytest
>>>>>>> Stashed changes
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MixBridge
from core.worker_manager import WorkerManager


@pytest.fixture
def worker_manager():
    wm = MagicMock(spec=WorkerManager)
    wm.cancel_all = MagicMock(return_value=None)
<<<<<<< Updated upstream
    wm.run_task = MagicMock(return_value=MagicMock(cancel=MagicMock(return_value=True)))
=======
    wm.run_task = MagicMock(return_value=MagicMock())
=======
"""Full workflow: configure -> generate -> cancel -> generate again -> play.

Tests the complete mix lifecycle:
1. Load mix type
2. Verify songs are returned
3. Cancel generation (verify real call to worker_manager)
4. Load a different mix type
5. Play a track from the results
6. Enqueue all tracks
7. Save as playlist
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.mix_bridge import MixBridge
from core.worker_manager import WorkerManager


@pytest.fixture
def worker_manager():
    wm = MagicMock(spec=WorkerManager)
    wm.cancel_all = MagicMock(return_value=None)
    wm.run_task = MagicMock(return_value=MagicMock(cancel=MagicMock(return_value=True)))
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
<<<<<<< Updated upstream
<<<<<<< Updated upstream
        {"track_id": i, "title": f"Fav {i}", "artist": f"Artist {chr(65 + (i % 26))}",
         "album": "Album B", "duration": 200, "reason": "Favorito"}
        for i in range(1, 11)
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
        {"track_id": i, "title": f"Fav {i}", "artist": "ArtistA", "album": "AlbumX", "duration": 200 + i}
        for i in range(1, 16)
>>>>>>> Stashed changes
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
<<<<<<< Updated upstream
=======
    mqs.unplayed.return_value = []
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = []
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
=======
        {"track_id": i, "title": f"Fav {i}", "artist": f"Artist {chr(65 + (i % 26))}",
         "album": "Album B", "duration": 200, "reason": "Favorito"}
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
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    return mqs


@pytest.fixture
def mock_tas():
    tas = MagicMock()
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    tas.play_track.return_value = {"ok": True, "track_id": 1}
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    tas.play_track.return_value = {"ok": True}
=======
    tas.play_track.return_value = {"ok": True, "track_id": 1}
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    tas.enqueue_track.return_value = {"ok": True}
    return tas


@pytest.fixture
<<<<<<< Updated upstream
<<<<<<< Updated upstream
def mock_pb():
    pb = MagicMock()
    pb.createPlaylist.return_value = {"ok": True, "id": 42}
    pb.addTrackToPlaylist.return_value = {"ok": True}
    return pb


@pytest.fixture
def bridge(mock_mqs, mock_tas, mock_pb, worker_manager):
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
def bridge(mock_mqs, mock_wm, mock_tas):
>>>>>>> Stashed changes
    return MixBridge(
        query_service=mock_mqs,
        track_action_service=mock_tas,
<<<<<<< Updated upstream
        playlist_bridge=mock_pb,
        worker_manager=worker_manager,
=======
        playlist_bridge=MagicMock(),
=======
def mock_pb():
    pb = MagicMock()
    pb.createPlaylist.return_value = {"ok": True, "id": 42}
    pb.addTrackToPlaylist.return_value = {"ok": True}
    return pb


@pytest.fixture
def bridge(mock_mqs, mock_tas, mock_pb, worker_manager):
    return MixBridge(
        query_service=mock_mqs,
        track_action_service=mock_tas,
        playlist_bridge=mock_pb,
        worker_manager=worker_manager,
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    )


class TestMixWorkflow:
<<<<<<< Updated upstream
<<<<<<< Updated upstream
    def test_configure_and_generate_favorites(self, bridge):
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
    """Complete workflow: configure → generate → cancel → regenerate → play."""

    def test_wf_configure_favorites(self, bridge):
>>>>>>> Stashed changes
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] == 10
        assert len(bridge.currentSongs) == 10

    def test_generate_recent_then_cancel(self, bridge, worker_manager):
        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

        gen_before = bridge._generation
        cancel_result = bridge.cancelGeneration()
        assert cancel_result["ok"] is True
        assert bridge._generation == gen_before + 1
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

    def test_cancel_then_generate_again(self, bridge, worker_manager):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()
        assert bridge._generation == 1
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

    def test_play_track_after_generation(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result["ok"] is True
        mock_tas.play_track.assert_called_once()

    def test_enqueue_all_tracks(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        result = bridge.enqueueMix()
        assert result["ok"] is True
        assert result["count"] == 10
        assert mock_tas.enqueue_track.call_count == 10

    def test_save_as_playlist(self, bridge, mock_pb):
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Mi Mix Favoritos")
        assert result["ok"] is True
        assert result["count"] == 10
        mock_pb.createPlaylist.assert_called_once_with("Mi Mix Favoritos")

    def test_full_workflow_configure_generate_cancel_generate_play(self, bridge, worker_manager, mock_tas):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10
        play1 = bridge.playFromIndex(0)
        assert play1["ok"] is True

        bridge.cancelGeneration()
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10
        play2 = bridge.playFromIndex(0)
        assert play2["ok"] is True

    def test_play_all_tracks_in_mix(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.playFromIndex(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_tas.play_track.call_count == 10

    def test_enqueue_each_track_individually(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.enqueueTrack(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_tas.enqueue_track.call_count == 10

    def test_explain_after_generation(self, bridge):
        bridge.loadMix("favorites")
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert "Favorito" in explanation["reasons"]

    def test_explain_after_generation_and_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert explanation["total"] == 10

    def test_regenerate_from_existing_returns_new_songs(self, bridge):
        bridge.loadMix("favorites")
        first_batch = bridge.currentSongs[:]
        bridge.refresh()
        second_batch = bridge.currentSongs[:]
        assert len(first_batch) == len(second_batch)

    def test_workflow_with_different_mix_type_after_cancel(self, bridge, worker_manager):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()
<<<<<<< Updated upstream
=======
        bridge.cancelGeneration()
        assert bridge._generation == 3
=======
    def test_configure_and_generate_favorites(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] == 10
        assert len(bridge.currentSongs) == 10

    def test_generate_recent_then_cancel(self, bridge, worker_manager):
        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

        gen_before = bridge._generation
        cancel_result = bridge.cancelGeneration()
        assert cancel_result["ok"] is True
        assert bridge._generation == gen_before + 1
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

    def test_cancel_then_generate_again(self, bridge, worker_manager):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()
        assert bridge._generation == 1
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10

    def test_play_track_after_generation(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result["ok"] is True
        mock_tas.play_track.assert_called_once()

    def test_enqueue_all_tracks(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        result = bridge.enqueueMix()
        assert result["ok"] is True
        assert result["count"] == 10
        assert mock_tas.enqueue_track.call_count == 10

    def test_save_as_playlist(self, bridge, mock_pb):
        bridge.loadMix("favorites")
        result = bridge.saveMixAsPlaylist("Mi Mix Favoritos")
        assert result["ok"] is True
        assert result["count"] == 10
        mock_pb.createPlaylist.assert_called_once_with("Mi Mix Favoritos")

    def test_full_workflow_configure_generate_cancel_generate_play(self, bridge, worker_manager, mock_tas):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10
        play1 = bridge.playFromIndex(0)
        assert play1["ok"] is True

        bridge.cancelGeneration()
        worker_manager.cancel_all.assert_called_once_with(owner="mix_bridge")

        bridge.loadMix("recent")
        assert len(bridge.currentSongs) == 10
        play2 = bridge.playFromIndex(0)
        assert play2["ok"] is True

    def test_play_all_tracks_in_mix(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.playFromIndex(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_tas.play_track.call_count == 10

    def test_enqueue_each_track_individually(self, bridge, mock_tas):
        bridge.loadMix("favorites")
        for i in range(10):
            result = bridge.enqueueTrack(i)
            assert result["ok"] is True, f"Failed at index {i}"
        assert mock_tas.enqueue_track.call_count == 10

    def test_explain_after_generation(self, bridge):
        bridge.loadMix("favorites")
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert "Favorito" in explanation["reasons"]

    def test_explain_after_generation_and_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        explanation = bridge.explainCurrentMix()
        assert explanation["ok"] is True
        assert explanation["total"] == 10

    def test_regenerate_from_existing_returns_new_songs(self, bridge):
        bridge.loadMix("favorites")
        first_batch = bridge.currentSongs[:]
        bridge.refresh()
        second_batch = bridge.currentSongs[:]
        assert len(first_batch) == len(second_batch)

    def test_workflow_with_different_mix_type_after_cancel(self, bridge, worker_manager):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 10

        bridge.cancelGeneration()
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes

        bridge.loadMix("unplayed")
        assert len(bridge.currentSongs) == 5
        play = bridge.playFromIndex(0)
        assert play["ok"] is True

    def test_generation_counter_not_incremented_by_load(self, bridge):
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
