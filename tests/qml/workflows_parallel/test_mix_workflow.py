"""Workflow test: configure → generate → cancel → regenerate → play via MixBridge."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_wm():
    wm = MagicMock()
    wm.cancel_all = MagicMock(return_value=None)
    wm.run_task = MagicMock(return_value=MagicMock())
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Fav {i}", "artist": "ArtistA", "album": "AlbumX", "duration": 200 + i}
        for i in range(1, 16)
    ]
    mqs.recent.return_value = [
        {"track_id": i, "title": f"Recent {i}", "artist": "ArtistB", "album": "AlbumY", "duration": 210}
        for i in range(16, 26)
    ]
    mqs.most_played.return_value = [
        {"track_id": i, "title": f"Top {i}", "artist": "ArtistC", "album": "AlbumZ", "duration": 180}
        for i in range(26, 36)
    ]
    mqs.unplayed.return_value = []
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = []
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
    return mqs


@pytest.fixture
def mock_tas():
    tas = MagicMock()
    tas.play_track.return_value = {"ok": True}
    tas.enqueue_track.return_value = {"ok": True}
    return tas


@pytest.fixture
def bridge(mock_mqs, mock_wm, mock_tas):
    return MixBridge(
        query_service=mock_mqs,
        worker_manager=mock_wm,
        track_action_service=mock_tas,
        playlist_bridge=MagicMock(),
    )


class TestMixWorkflow:
    """Complete workflow: configure → generate → cancel → regenerate → play."""

    def test_wf_configure_favorites(self, bridge):
        result = bridge.loadMix("favorites")
        assert result["ok"] is True
        assert result["count"] > 0
        assert bridge.currentMixTitle == "Favoritos"

    def test_wf_configure_recent(self, bridge):
        result = bridge.loadMix("recent")
        assert result["ok"] is True
        assert bridge.currentMixTitle == "Escuchadas recientemente"

    def test_wf_generate_and_play(self, bridge):
        bridge.loadMix("favorites")
        play_result = bridge.playMix()
        assert play_result["ok"] is True
        assert bridge._tas.play_track.called

    def test_wf_generate_and_enqueue(self, bridge):
        bridge.loadMix("favorites")
        enq_result = bridge.enqueueMix()
        assert enq_result["ok"] is True
        assert enq_result["count"] > 0

    def test_wf_cancel_generation(self, bridge, mock_wm):
        bridge.loadMix("favorites")
        cancel_result = bridge.cancelGeneration()
        assert cancel_result["ok"] is True
        mock_wm.cancel_all.assert_called_with(owner="mix_bridge")

    def test_wf_regenerate_after_cancel(self, bridge, mock_wm):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.loadMix("favorites")
        assert result["ok"] is True

    def test_wf_cancel_then_play(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        play_result = bridge.playMix()
        assert play_result["ok"] is True

    def test_wf_cancel_then_enqueue(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        enq_result = bridge.enqueueMix()
        assert enq_result["ok"] is True
        assert enq_result["count"] > 0

    def test_wf_explain_after_generate(self, bridge):
        bridge.loadMix("favorites")
        exp_result = bridge.explainCurrentMix()
        assert exp_result["ok"] is True
        assert "reasons" in exp_result

    def test_wf_save_as_playlist(self, bridge):
        mock_pb = MagicMock()
        mock_pb.createPlaylist.return_value = {"ok": True, "id": 42}
        mock_pb.addTrackToPlaylist.return_value = {"ok": True}
        bridge._pb = mock_pb
        bridge.loadMix("favorites")
        save_result = bridge.saveMixAsPlaylist("My Mix Playlist")
        assert save_result["ok"] is True
        assert save_result["id"] == 42

    def test_wf_generate_play_from_index(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.playFromIndex(0)
        assert result["ok"] is True
        assert result["track_id"] is not None

    def test_wf_generate_enqueue_track(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.enqueueTrack(0)
        assert result["ok"] is True

    def test_wf_generate_then_refresh(self, bridge):
        bridge.loadMix("favorites")
        result = bridge.refresh()
        assert result["ok"] is True
        assert len(bridge.currentSongs) > 0

    def test_wf_multiple_generations(self, bridge):
        bridge.loadMix("favorites")
        bridge.loadMix("recent")
        bridge.loadMix("most_played")
        assert bridge.currentMixTitle == "Más escuchadas"
        assert len(bridge.currentSongs) > 0

    def test_wf_cancel_multiple(self, bridge):
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        assert bridge._generation == 3
