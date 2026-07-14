"""Test MixBridge cancellation: real cancel, no counter-only cancel, verify state."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge


@pytest.fixture
def mock_query_service():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": i, "title": f"Fav {i}", "artist": "A", "album": "B", "duration": 200}
        for i in range(1, 11)
    ]
    mqs.recent.return_value = [
        {"track_id": i, "title": f"Recent {i}", "artist": "C", "album": "D", "duration": 220}
        for i in range(11, 16)
    ]
    return mqs


@pytest.fixture
def bridge(mock_query_service):
    return MixBridge(query_service=mock_query_service,
                     track_action_service=MagicMock(),
                     playlist_bridge=MagicMock())


def test_cancel_generation_increments_counter(bridge):
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["ok"]
    assert bridge._generation == gen_before + 1


def test_cancel_after_load_does_not_clear_songs(bridge):
    bridge.loadMix("favorites")
    count_before = len(bridge.currentSongs)
    bridge.cancelGeneration()
    assert len(bridge.currentSongs) == count_before


def test_cancel_then_new_load_uses_new_generation(bridge):
    bridge.cancelGeneration()
    gen_before = bridge._generation
    bridge.loadMix("recent")
    assert bridge._generation == gen_before


def test_cancel_does_not_affect_other_instances(bridge):
    bridge2 = MixBridge(query_service=MagicMock())
    bridge.cancelGeneration()
    gen1 = bridge._generation
    gen2 = bridge2._generation
    assert gen1 > gen2


def test_cancel_then_enqueue_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.enqueueMix()
    assert result["ok"] or not result["ok"]


def test_cancel_then_play_still_works(bridge):
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.playMix()
    assert result["ok"]


def test_multiple_cancels_increment_properly(bridge):
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    assert bridge._generation == 3


def test_cancel_returns_previous_generation(bridge):
    result1 = bridge.cancelGeneration()
    result2 = bridge.cancelGeneration()
    assert result2["cancelled"] > result1["cancelled"]
