import pytest


from .conftest import make_bridge, make_mix_service

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=2)


@pytest.fixture
def bridge(mock_mqs, tmp_path):
    b, _svc = make_bridge(mock_mqs, tmp_path)
    return b


def test_cancel_generation_increments_counter(bridge):
    bridge.loadMix("favorites")
    gen_before = bridge._generation
    bridge.cancelGeneration()
    assert bridge._generation == gen_before + 1


def test_cancel_generation_increments_counter_and_returns_cancelled(bridge):
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["cancelled"] == gen_before


def test_cancel_generation_still_ok_without_wm(bridge):
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_load_after_cancel_increments_generation(bridge):
    bridge.cancelGeneration()
    gen_after_cancel = bridge._generation
    bridge.loadMix("favorites")
    assert bridge._generation > gen_after_cancel


def test_cancel_clears_loaded_songs(bridge):
    bridge.loadMix("favorites")
    assert len(bridge.currentSongs) == 2
    bridge.cancelGeneration()
    assert len(bridge.currentSongs) == 0


def test_cancel_after_load_play_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.playMix()
    assert result["ok"] is False


def test_cancel_after_load_enqueue_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.enqueueMix()
    assert result["ok"] is False


def test_cancel_after_load_explain_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.explainCurrentMix()
    assert result["ok"] is False


def test_bridge_never_uses_cancel_all(mock_mqs, tmp_path):
    bridge, job_svc = make_bridge(mock_mqs, tmp_path)
    bridge.loadMix("favorites")
    result = bridge.cancelGeneration()
    assert result["ok"]
    assert job_svc.list_jobs()  # job registry is untouched by the bridge
