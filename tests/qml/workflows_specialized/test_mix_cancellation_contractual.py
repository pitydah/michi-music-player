"""ML: Test MixBridge cancellation contractual — real cancel, full state machine."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge
from core.worker_manager import WorkerManager


@pytest.fixture
def mock_wm():
    wm = MagicMock(spec=WorkerManager)
    wm.cancel_all = MagicMock(return_value=None)
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Fav {i}", "artist": "A", "album": "B", "duration": 200}
        for i in range(1, 6)
    ]
    return mqs


@pytest.fixture
def bridge(mock_mqs, mock_wm):
    tas = MagicMock()
    tas.play_track.return_value = {"ok": True}
    return MixBridge(
        query_service=mock_mqs,
        worker_manager=mock_wm,
        track_action_service=tas,
        playlist_bridge=MagicMock(),
    )


class TestMixCancellationContractual:
    def test_cancel_calls_worker_manager_cancel_all(self, bridge, mock_wm):
        bridge.loadMix("favorites")
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        mock_wm.cancel_all.assert_called_once_with(owner="mix_bridge")

    def test_cancel_increments_generation_counter(self, bridge):
        gen_before = bridge._generation
        bridge.cancelGeneration()
        assert bridge._generation == gen_before + 1

    def test_cancel_returns_previous_generation(self, bridge):
        gen_before = bridge._generation
        result = bridge.cancelGeneration()
        assert result["cancelled"] == gen_before

    def test_cancel_without_worker_manager_still_increments(self, bridge):
        bridge_no_wm = MixBridge(query_service=MagicMock())
        gen_before = bridge_no_wm._generation
        result = bridge_no_wm.cancelGeneration()
        assert result["ok"] is True
        assert bridge_no_wm._generation == gen_before + 1

    def test_cancel_does_not_clear_loaded_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) > 0

    def test_multiple_cancels_each_calls_cancel_all(self, bridge, mock_wm):
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        assert mock_wm.cancel_all.call_count == 2

    def test_state_transition_after_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        assert bridge._generation >= 1

    def test_cancel_then_new_load_resets_counter_stable(self, bridge):
        bridge.cancelGeneration()
        gen_after = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_after

    def test_cancel_not_just_counter(self, bridge, mock_wm):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        mock_wm.cancel_all.assert_called_once()

    def test_cancel_without_worker_manager_does_not_raise(self):
        b = MixBridge(query_service=MagicMock())
        try:
            b.cancelGeneration()
        except Exception:
            pytest.fail("cancelGeneration raised without worker manager")

    def test_cancel_after_songs_play_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.playMix()
        assert result["ok"] is True

    def test_cancel_after_songs_enqueue_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.enqueueMix()
        assert result["ok"] is True

    def test_isolated_cancel_does_not_affect_other_instances(self, bridge):
        bridge2 = MixBridge(query_service=MagicMock())
        bridge.cancelGeneration()
        assert bridge._generation > bridge2._generation

    def test_cancel_all_called_with_correct_owner(self, bridge, mock_wm):
        bridge.cancelGeneration()
        _, kwargs = mock_wm.cancel_all.call_args
        assert kwargs.get("owner") == "mix_bridge"
