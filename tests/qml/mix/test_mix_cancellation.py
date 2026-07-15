"""CRITICAL: Verify Mix cancellation is REAL (WorkerManager cancel_all, not just counter)."""
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
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "B", "album": "Bl", "duration": 180, "reason": "Favorito"},
    ]
    return mqs


class TestMixCancellation:
    def test_cancel_calls_worker_manager(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.loadMix("favorites")
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        mock_wm.cancel_all.assert_called_with(owner="mix_bridge")

    def test_cancel_increments_counter(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        gen_before = bridge._generation
        bridge.cancelGeneration()
        assert bridge._generation == gen_before + 1

    def test_cancel_returns_previous_generation(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        gen_before = bridge._generation
        result = bridge.cancelGeneration()
        assert result["cancelled"] == gen_before

    def test_cancel_twice_calls_wm_twice(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        assert mock_wm.cancel_all.call_count == 2

    def test_cancel_without_wm_still_ok(self, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=None)
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        assert "cancelled" in result

    def test_cancel_does_not_clear_songs(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.loadMix("favorites")
        count_before = len(bridge.currentSongs)
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == count_before

    def test_cancel_then_play_still_works(self, mock_wm, mock_mqs):
        tas = MagicMock()
        tas.play_track.return_value = {"ok": True}
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm, track_action_service=tas)
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.playMix()
        assert result["ok"] is True

    def test_cancel_then_enqueue_still_works(self, mock_wm, mock_mqs):
        tas = MagicMock()
        tas.enqueue_track.return_value = {"ok": True}
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm, track_action_service=tas)
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.enqueueMix()
        assert result["ok"] is True
        assert result["count"] == 2

    def test_cancel_then_explain_still_works(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.explainCurrentMix()
        assert result["ok"] is True

    def test_multiple_cancels_increment(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        assert bridge._generation == 3

    def test_cancel_after_load_does_not_affect_load(self, mock_wm, mock_mqs):
        bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
        bridge.cancelGeneration()
        gen_after = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_after

    def test_cancel_with_query_executor(self, mock_mqs):
        qe = MagicMock()
        qe.cancel_owner = MagicMock()
        bridge = MixBridge(query_service=mock_mqs, query_executor=qe)
        result = bridge.cancelGeneration()
        assert result["ok"] is True
