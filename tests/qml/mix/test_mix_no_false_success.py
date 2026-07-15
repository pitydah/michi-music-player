"""Test MixBridge: no fake tracks, no false success on empty mix/queue, no AI without backend."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge
pytestmark = [pytest.mark.qml_module("mix")]



@pytest.fixture
def mock_query_service():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "B", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "A", "album": "B", "duration": 180, "reason": "Favorito"},
    ]
    mqs.recent.return_value = [
        {"track_id": 3, "title": "Recent 1", "artist": "C", "album": "D", "duration": 220},
    ]
    mqs.unplayed.return_value = [
        {"track_id": 4, "title": "Unplayed 1", "artist": "D", "album": "E", "duration": 190},
    ]
    mqs.most_played.return_value = [
        {"track_id": 5, "title": "Top 1", "artist": "E", "album": "F", "duration": 210},
    ]
    mqs.rediscovery.return_value = []
    mqs.by_field.return_value = []
    mqs.by_decade.return_value = []
    mqs.by_year.return_value = []
    mqs.high_quality.return_value = []
    return mqs


@pytest.fixture
def bridge(mock_query_service):
    return MixBridge(query_service=mock_query_service,
                     track_action_service=MagicMock(),
                     playlist_bridge=MagicMock())


def test_favorites_mix_returns_real_tracks(bridge):
    result = bridge.loadMix("favorites")
    assert result["ok"]
    assert result["count"] == 2


def test_empty_mix_play_returns_error(bridge):
    bridge._current_songs = []
    result = bridge.playMix()
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_MIX"


def test_empty_mix_enqueue_returns_error(bridge):
    bridge._current_songs = []
    result = bridge.enqueueMix()
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_MIX"


def test_save_empty_mix_as_playlist_returns_error(bridge):
    bridge._current_songs = []
    result = bridge.saveMixAsPlaylist("Test")
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_MIX"


def test_save_empty_name_returns_error(bridge):
    bridge.loadMix("favorites")
    result = bridge.saveMixAsPlaylist("")
    assert not result["ok"]
    assert result["error_code"] == "EMPTY_NAME"


def test_no_fake_tracks_in_favorites(bridge):
    bridge.loadMix("favorites")
    for song in bridge.currentSongs:
        assert song.get("track_id", 0) != 0


def test_explain_empty_mix_returns_error(bridge):
    bridge._current_songs = []
    result = bridge.explainCurrentMix()
    assert not result["ok"]


def test_explain_populated_mix_returns_reasons(bridge):
    bridge.loadMix("favorites")
    result = bridge.explainCurrentMix()
    assert result["ok"]


def test_cancel_generation(bridge):
    result = bridge.cancelGeneration()
    assert result["ok"]
    assert "cancelled" in result


def test_play_from_index_invalid(bridge):
    result = bridge.playFromIndex(999)
    assert not result["ok"]
    assert result["error_code"] == "INVALID_INDEX"


def test_play_from_index_no_track_id(bridge):
    bridge._current_songs = [{"id": 0, "title": "No ID"}]
    result = bridge.playFromIndex(0)
    assert not result["ok"]


def test_daily_mix_deduplicates(bridge):
    bridge.loadMix("daily_mix")
    ids = set()
    for s in bridge.currentSongs:
        tid = s.get("track_id") or s.get("id")
        assert tid not in ids or tid == 0
        if tid:
            ids.add(tid)
