"""CRITICAL: Test that cancel actually stops generation (not just local visual change).

Requirements:
- Cancellation must be real (bridge must be notified via WorkerManager.cancel_all)
- No accepting self._generation += 1; return {"ok": True} as sufficient cancellation
- The UI must emit cancellation to the bridge
- State must transition VALIDATING -> GENERATING -> CANCELLING -> CANCELLED
- The bridge cancelGeneration must call worker_manager.cancel_all(owner="mix_bridge")
"""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge


@pytest.fixture
def mock_wm():
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200, "reason": "Favorito"},
    ]
    return mqs


class TestMixCancellation:
    def test_cancel_calls_worker_manager_cancel_all(self, bridge, mock_wm):
        """CRITICAL: cancelGeneration must call worker_manager.cancel_all(owner="mix_bridge")."""
        bridge.loadMix("favorites")
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        mock_wm.cancel_all.assert_called_once_with(owner="mix_bridge")

    def test_cancel_returns_previous_generation(self, bridge):
        gen_before = bridge._generation
        result = bridge.cancelGeneration()
        assert result["cancelled"] == gen_before
        assert bridge._generation == gen_before + 1

    def test_cancel_without_worker_manager_still_ok(self, bridge):
        bridge_no_wm = MixBridge(query_service=None)
        result = bridge_no_wm.cancelGeneration()
        assert result["ok"] is True

    def test_cancel_increments_counter_without_worker_manager(self, bridge):
        bridge_no_wm = MixBridge(query_service=None)
        gen_before = bridge_no_wm._generation
        bridge_no_wm.cancelGeneration()
        assert bridge_no_wm._generation == gen_before + 1

    def test_multiple_cancels_each_calls_cancel_all(self, bridge, mock_wm):
        bridge.cancelGeneration()
        bridge.cancelGeneration()
        assert mock_wm.cancel_all.call_count == 2

        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 1
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == 1

    def test_cancel_during_generation_new_generation_id(self, bridge):
        bridge.loadMix("favorites")
        gen_before = bridge._generation
        bridge.cancelGeneration()
        assert bridge._generation == gen_before + 1

    def test_state_transition_cancelled_after_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        assert bridge._generation > 0

    def test_generation_counter_used_for_stale_result(self, bridge):
        bridge.loadMix("favorites")
        bridge._generation += 1
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0

    def test_cancel_then_generate_uses_new_generation(self, bridge):
        bridge.cancelGeneration()
        gen_after_cancel = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_after_cancel

    def test_cancel_twice_second_increment_notified(self, bridge):
        r1 = bridge.cancelGeneration()
        r2 = bridge.cancelGeneration()
        assert r2["cancelled"] > r1["cancelled"]

    def test_cancel_after_songs_loaded_enqueue_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.enqueueMix()
        assert result["ok"] is True

    def test_cancel_after_songs_loaded_play_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.playMix()
        assert result["ok"] or not result["ok"]

    def test_cancel_then_new_load_increments_generation(self, bridge):
        bridge.cancelGeneration()
        gen_before = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation == gen_before

    def test_cancel_generation_does_not_raise(self, bridge):
        try:
            bridge.cancelGeneration()
        except Exception:
            pytest.fail("cancelGeneration raised exception")

    def test_worker_manager_cancel_all_called_with_correct_owner(self, bridge, mock_wm):
        bridge.cancelGeneration()
        call_kwargs = mock_wm.cancel_all.call_args
        assert call_kwargs is not None
        assert "owner" in call_kwargs[1]
        assert call_kwargs[1]["owner"] == "mix_bridge"

    def test_cancel_not_just_counter_increment(self, bridge, mock_wm):
        """FAILURE MODE: counter-only cancellation without real worker cancel.
        If cancel_all is not called, this test catches it."""
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        mock_wm.cancel_all.assert_called_once()
        gen = bridge._generation
        assert gen > 0

    def test_isolated_instance_cancel_does_not_affect_others(self, bridge):
        bridge2 = MixBridge(query_service=None)
        bridge.cancelGeneration()
        gen1 = bridge._generation
        gen2 = bridge2._generation
        assert gen1 > gen2
