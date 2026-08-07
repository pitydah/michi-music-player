"""No false success: an empty mix is NEVER ok end-to-end; the bridge maps
the canonical outcome 1:1 (Fase Mix)."""
import pytest
from unittest.mock import MagicMock


from .conftest import make_bridge, make_mix_service

pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_mix_svc():
    return make_mix_service(default_track_count=2)


@pytest.fixture
def bridge(mock_mix_svc, tmp_path):
    b, _svc = make_bridge(
        mock_mix_svc, tmp_path,
        playback_service=MagicMock(),
        queue_service=MagicMock(),
        playlist_service=MagicMock(),
    )
    return b


def test_favorites_mix_returns_real_tracks(bridge):
    result = bridge.loadMix("favorites")
    assert result["ok"]
    assert bridge.stateName == "COMPLETED_WITH_TRACKS"
    assert len(bridge.currentSongs) == 2


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
    bridge._queue_svc = None
    result = bridge.playFromIndex(0)
    assert not result["ok"]


def test_generated_tracks_have_unique_ids(bridge):
    bridge.loadMix("daily_mix")
    ids = set()
    for s in bridge.currentSongs:
        tid = s.get("track_id") or s.get("id")
        assert tid not in ids or tid == 0
        if tid:
            ids.add(tid)
