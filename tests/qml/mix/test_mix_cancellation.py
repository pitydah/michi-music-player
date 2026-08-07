import pytest

from core.jobs.job_service import DurableJobService, JobState
from ui_qml_bridge.mix_bridge import MixBridge

from .conftest import make_bridge, make_mix_service


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=1)


@pytest.fixture
def bridge(mock_mqs, tmp_path):
    b, _svc = make_bridge(mock_mqs, tmp_path)
    return b


class TestMixCancellation:
    def test_cancel_returns_previous_generation(self, bridge):
        bridge.loadMix("favorites")
        gen_before = bridge._generation
        result = bridge.cancelGeneration()
        assert result["ok"] is True
        assert result["cancelled"] == gen_before
        assert bridge._generation == gen_before + 1

    def test_cancel_without_job_service_still_ok(self):
        bridge = MixBridge()
        result = bridge.cancelGeneration()
        assert result["ok"] is True

    def test_cancel_clears_loaded_songs(self, bridge):
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 1
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == 0

    def test_multiple_cancels_each_ok(self, bridge):
        assert bridge.cancelGeneration()["ok"] is True
        assert bridge.cancelGeneration()["ok"] is True
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) == 1
        bridge.cancelGeneration()
        assert len(bridge.currentSongs) == 0

    def test_cancel_during_generation_new_generation_id(self, bridge):
        bridge.loadMix("favorites")
        gen_before = bridge._generation
        bridge.cancelGeneration()
        assert bridge._generation == gen_before + 1

    def test_state_cancelled_after_cancel(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        assert bridge.stateName == "CANCELLED"

    def test_generation_counter_used_for_stale_result(self, bridge):
        bridge.loadMix("favorites")
        bridge._generation += 1
        bridge.loadMix("favorites")
        assert len(bridge.currentSongs) > 0

    def test_cancel_then_generate_uses_new_generation(self, bridge):
        bridge.cancelGeneration()
        gen_after_cancel = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation > gen_after_cancel

    def test_cancel_twice_second_increment_notified(self, bridge):
        r1 = bridge.cancelGeneration()
        r2 = bridge.cancelGeneration()
        assert r2["cancelled"] > r1["cancelled"]

    def test_cancel_after_songs_loaded_enqueue_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.enqueueMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

    def test_cancel_after_songs_loaded_play_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.playMix()
        assert result["ok"] is False
        assert result["error_code"] == "EMPTY_MIX"

    def test_cancel_after_songs_loaded_explain_still_works(self, bridge):
        bridge.loadMix("favorites")
        bridge.cancelGeneration()
        result = bridge.explainCurrentMix()
        assert result["ok"] is False

    def test_cancel_then_new_load_increments_generation(self, bridge):
        bridge.cancelGeneration()
        gen_after_cancel = bridge._generation
        bridge.loadMix("favorites")
        assert bridge._generation > gen_after_cancel

    def test_cancel_generation_does_not_raise(self, bridge):
        try:
            bridge.cancelGeneration()
        except Exception:
            pytest.fail("cancelGeneration raised exception")

    def test_cancel_only_cancels_own_job(self, mock_mqs, tmp_path):
        """Scoped cancellation: the mix job is cancelled; an unrelated job
        from another domain keeps its state."""
        job_svc = DurableJobService(db_path=str(tmp_path / "jobs.db"))
        job_svc.register_handler("mix_generate",
                                 _noop_mix_handler(mock_mqs))
        job_svc.register_handler("library_scan", _noop_handler)
        other_id = job_svc.create_job("library_scan", owner="job_bridge",
                                      payload={"folder_path": "/music"})
        assert job_svc.start_job(other_id) is True
        assert job_svc.get_job(other_id).state == JobState.SUCCEEDED

        bridge = MixBridge(mix_service=mock_mqs, job_service=job_svc)
        job_id = job_svc.create_job("mix_generate", owner="mix",
                                    payload={"strategy": "favorites"})
        bridge._job_id = job_id

        result = bridge.cancelGeneration()
        assert result["ok"] is True

        # The mix job is gone; the other domain's job is untouched.
        assert job_svc.get_job(job_id).state == JobState.CANCELLED
        assert job_svc.get_job(other_id).state == JobState.SUCCEEDED

    def test_isolated_instance_cancel_does_not_affect_others(self, bridge):
        bridge2 = MixBridge()
        bridge.cancelGeneration()
        gen1 = bridge._generation
        gen2 = bridge2._generation
        assert gen1 > gen2


def _noop_handler(job, ctx):
    return {"ok": True}


def _noop_mix_handler(port):
    def handler(job, ctx):
        return port.generate(job.payload.get("strategy", "daily"),
                             job.payload.get("seed") or {}, 30, ctx)
    return handler
