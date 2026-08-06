import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

from .conftest import make_bridge, make_mix_service

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_mix_svc():
    return make_mix_service(default_track_count=10)


@pytest.fixture
def bridge(mock_mix_svc, tmp_path):
    b, _svc = make_bridge(mock_mix_svc, tmp_path)
    return b


def test_cancel_generation_increments_counter(bridge):
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["ok"]
    assert bridge._generation == gen_before + 1


def test_cancel_after_load_clears_songs(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    assert len(bridge.currentSongs) == 0


def test_cancel_then_new_load_uses_new_generation(bridge):
    bridge.cancelGeneration()
    gen_after_cancel = bridge._generation
    bridge.loadMix("recent")
    assert bridge._generation >= gen_after_cancel


def test_cancel_does_not_affect_other_instances(bridge):
    bridge2 = MixBridge(mix_service=MagicMock())
    bridge.cancelGeneration()
    gen1 = bridge._generation
    gen2 = bridge2._generation
    assert gen1 > gen2


def test_cancel_then_enqueue_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.enqueueMix()
    assert result["ok"] is False
    assert result["error_code"] == "EMPTY_MIX"


def test_cancel_then_play_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.playMix()
    assert result["ok"] is False
    assert result["error_code"] == "EMPTY_MIX"


def test_multiple_cancels_increment_properly(bridge):
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    assert bridge._generation == 3


def test_cancel_returns_previous_generation(bridge):
    result1 = bridge.cancelGeneration()
    result2 = bridge.cancelGeneration()
    assert result2["cancelled"] > result1["cancelled"]
