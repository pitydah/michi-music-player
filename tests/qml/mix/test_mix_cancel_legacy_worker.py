import pytest

from ui_qml_bridge.mix_bridge import MixBridge

from .conftest import make_bridge, make_mix_service

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=1)


@pytest.fixture
def bridge(mock_mqs, tmp_path):
    b, _svc = make_bridge(mock_mqs, tmp_path)
    return b


def test_cancel_generation_increments_counter(bridge):
    bridge.loadMix("favorites")
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["ok"]
    assert result["cancelled"] == gen_before
    assert bridge._generation == gen_before + 1


def test_generation_counter_used_in_load_stale_check(bridge):
    bridge.loadMix("favorites")
    old_gen = bridge._generation
    bridge.cancelGeneration()
    bridge.loadMix("favorites")
    assert bridge._generation > old_gen


def test_custom_mix_with_seed(bridge):
    result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 5}')
    assert result["ok"]


def test_custom_mix_with_rules_empty(bridge):
    result = bridge.loadMix("custom")
    assert result["ok"]


def test_cancel_generation_still_ok_without_wm():
    bridge = MixBridge()
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_cancel_twice_still_ok(bridge):
    bridge.cancelGeneration()
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_cancel_does_not_call_cancel_all(bridge):
    """Scoped cancellation: no cancel_all() anywhere in the mix path."""
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    from pathlib import Path
    source = (Path(__file__).resolve().parent.parent.parent.parent
              / "ui_qml_bridge" / "mix_bridge.py").read_text(encoding="utf-8")
    assert "cancel_all(" not in source
