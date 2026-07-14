"""Test MixBridge cancelGeneration cancels real WorkerManager task, not just counter increment."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge


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
    ]
    mqs.recent.return_value = []
    mqs.most_played.return_value = []
    mqs.unplayed.return_value = []
    return mqs


def test_cancel_generation_calls_worker_manager_cancel(mock_wm, mock_mqs):
    bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
    bridge.loadMix("favorites")
    result = bridge.cancelGeneration()
    assert result["ok"]
    mock_wm.cancel_all.assert_called_with(owner="mix_bridge")


def test_cancel_generation_increments_counter(mock_wm, mock_mqs):
    bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
    bridge.loadMix("favorites")
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["cancelled"] == gen_before
    assert bridge._generation == gen_before + 1


def test_generation_counter_used_in_load_stale_check(mock_wm, mock_mqs):
    bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
    bridge.loadMix("favorites")
    old_gen = bridge._generation
    bridge.cancelGeneration()
    bridge.loadMix("favorites")
    assert bridge._generation > old_gen


def test_custom_mix_with_seed(mock_wm):
    bridge = MixBridge(worker_manager=mock_wm)
    result = bridge.loadMix("custom", seed='{"artist": "Genesis", "limit": 5}')
    assert result["ok"]


def test_custom_mix_with_rules_empty(mock_wm, mock_mqs):
    bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
    result = bridge.loadMix("custom")
    assert result["ok"]


def test_cancel_generation_still_ok_without_wm():
    bridge = MixBridge()
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_cancel_twice_still_ok(mock_wm, mock_mqs):
    bridge = MixBridge(query_service=mock_mqs, worker_manager=mock_wm)
    bridge.cancelGeneration()
    result = bridge.cancelGeneration()
    assert result["ok"]
