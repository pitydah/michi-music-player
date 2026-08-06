"""MixBridge cancellation contractual — REAL scoped cancel (no cancel_all),
full job lifecycle: cancelling only the bridge's own job id, clearing the
loaded mix, and never touching other domains' jobs."""
import pytest
from unittest.mock import MagicMock

from core.jobs.job_service import JobState
from ui_qml_bridge.mix_bridge import MixBridge

from ..mix.conftest import make_bridge, make_mix_service


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=5)


@pytest.fixture
def bridge(mock_mqs, tmp_path):
    b, _svc = make_bridge(mock_mqs, tmp_path)
    return b


class TestMixCancellationContractual:
    def test_cancel_increments_generation_counter(self, bridge):
        gen_before = bridge._generation
        bridge.cancelGeneration()
        assert bridge._generation == gen_before + 1

    def test_cancel_returns_previous_generation(self, bridge):
        gen_before = bridge._generation
        result = bridge.cancelGeneration()
        assert result["cancelled"] == gen_before

    def test_cancel_without_job_service_still_increments(self, bridge):
        bridge_no_wm = MixBridge(mix_service=MagicMock())
        gen_before = bridge_no_wm._generation
        result = bridge_no_wm.cancelGeneration()
        assert result["ok"] is True
        assert bridge_no_wm._generation == gen_before + 1

    def test_cancel_clears_loaded_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == 0

    def test_multiple_cancels_each_ok(self, bridge):
        assert bridge.cancelGeneration()["ok"] is True
        assert bridge.cancelGeneration()["ok"] is True

    def test_state_transition_after_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        assert bridge.stateName == "CANCELLED"
        assert bridge._generation >= 1

    def test_cancel_then_new_load_increments(self, bridge):
        bridge.cancelGeneration()
        gen_after = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation > gen_after

    def test_cancel_is_not_just_counter(self, bridge, tmp_path):
        """The durable job itself is really cancelled (scoped to own id)."""
        mock_mqs = make_mix_service(default_track_count=5)
        b, job_svc = make_bridge(mock_mqs, tmp_path)
        job_id = job_svc.create_job("mix_generate", owner="mix",
                                    payload={"strategy": "favorites"})
        b._job_id = job_id
        result = b.cancelGeneration()
        assert result["ok"] is True
        assert job_svc.get_job(job_id).state == JobState.CANCELLED

    def test_cancel_without_job_service_does_not_raise(self):
        b = MixBridge(mix_service=MagicMock())
        try:
            b.cancelGeneration()
        except Exception:
            pytest.fail("cancelGeneration raised without job service")

    def test_cancel_after_songs_play_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.playMix()
        assert result["ok"] is False  # mix was cleared by the cancel

    def test_cancel_after_songs_enqueue_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.enqueueMix()
        assert result["ok"] is False

    def test_isolated_cancel_does_not_affect_other_instances(self, bridge):
        bridge2 = MixBridge(mix_service=MagicMock())
        bridge.cancelGeneration()
        assert bridge._generation > bridge2._generation

    def test_no_cancel_all_anywhere(self, bridge):
        """Contractual: cancel_all / broadcast cancel is banned in the bridge."""
        from pathlib import Path
        source = (Path(__file__).resolve().parent.parent.parent.parent
                  / "ui_qml_bridge" / "mix_bridge.py").read_text(encoding="utf-8")
        assert "cancel_all(" not in source
        assert "cancel_owner(" not in source
        assert "cancel_scope(" not in source
