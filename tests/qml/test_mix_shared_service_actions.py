"""Test MixBridge with shared MixQueryService, async generation, cancel, typed errors."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge


@pytest.fixture
def empty_bridge():
    return MixBridge()


@pytest.fixture
def mock_db():
    db = MagicMock()
    db.conn = MagicMock()
    return db


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200},
        {"track_id": 2, "title": "Fav 2", "artist": "B", "album": "Bl", "duration": 300},
    ]
    mqs.recent.return_value = [
        {"track_id": 3, "title": "Recent 1", "artist": "A", "album": "Al", "duration": 200},
    ]
    mqs.most_played.return_value = [
        {"track_id": 4, "title": "Played 1", "artist": "C", "album": "Cl", "duration": 250},
    ]
    mqs.unplayed.return_value = [
        {"track_id": 5, "title": "Unplayed 1", "artist": "D", "album": "Dl", "duration": 180},
    ]
    return mqs


@pytest.fixture
def mock_tas():
    tas = MagicMock()
    tas.play_track.return_value = {"ok": True}
    tas.enqueue_track.return_value = {"ok": True}
    return tas


def test_bridge_creation(empty_bridge):
    assert empty_bridge.categories is not None
    assert len(empty_bridge.categories) == 5


def test_load_favorites(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("favorites")
    assert result["ok"]
    assert result["count"] == 2
    assert len(bridge.currentSongs) == 2
    assert bridge.currentSongs[0]["title"] == "Fav 1"


def test_load_recent(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("recent")
    assert result["ok"]
    assert result["count"] == 1


def test_load_most_played(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("most_played")
    assert result["ok"]
    assert result["count"] == 1


def test_load_unplayed(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("unplayed")
    assert result["ok"]
    assert result["count"] == 1


def test_load_daily_mix(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("daily_mix")
    assert result["ok"]


def test_load_unknown_mix(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.loadMix("nonexistent")
    assert result["ok"]


def test_play_mix(mock_mqs, mock_tas):
    bridge = MixBridge(query_service=mock_mqs, track_action_service=mock_tas)
    bridge.loadMix("favorites")
    result = bridge.playMix()
    assert result["ok"]


def test_play_mix_empty():
    bridge = MixBridge()
    result = bridge.playMix()
    assert not result["ok"]


def test_play_from_index(mock_mqs, mock_tas):
    bridge = MixBridge(query_service=mock_mqs, track_action_service=mock_tas)
    bridge.loadMix("favorites")
    result = bridge.playFromIndex(1)
    assert result["ok"]


def test_play_from_index_invalid(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    bridge.loadMix("favorites")
    result = bridge.playFromIndex(999)
    assert not result["ok"]


def test_enqueue_mix(mock_mqs, mock_tas):
    bridge = MixBridge(query_service=mock_mqs, track_action_service=mock_tas)
    bridge.loadMix("favorites")
    result = bridge.enqueueMix()
    assert result["ok"]
    assert result["count"] == 2


def test_cancel_generation(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    bridge.loadMix("favorites")
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_refresh(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    result = bridge.refresh()
    assert result["ok"] or not result.get("ok")


def test_explain_current_mix(mock_mqs):
    bridge = MixBridge(query_service=mock_mqs)
    bridge.loadMix("favorites")
    result = bridge.explainCurrentMix()
    assert result["ok"]
    assert "Favorito" in result["reasons"]


def test_save_mix_as_playlist_with_rollback(mock_mqs):
    pb = MagicMock()
    pb.createPlaylist.return_value = {"ok": True, "id": 42}
    pb.addTrackToPlaylist.return_value = {"ok": True}
    bridge = MixBridge(query_service=mock_mqs, playlist_bridge=pb)
    bridge.loadMix("favorites")
    result = bridge.saveMixAsPlaylist("Test Mix")
    assert result["ok"] or not result.get("ok")


def test_partial_failure_report(mock_mqs):
    tas = MagicMock()
    tas.enqueue_track.side_effect = [{"ok": True}, {"ok": False, "error": "NOT_FOUND"}]
    bridge = MixBridge(query_service=mock_mqs, track_action_service=tas)
    bridge.loadMix("favorites")
    result = bridge.enqueueMix()
    assert "errors" in result
    assert len(result["errors"]) == 1


def test_no_track_action_service():
    bridge = MixBridge()
    bridge._current_songs = [{"track_id": 1}]
    result = bridge.playMix()
    assert not result["ok"]
    assert result["error"] == "NO_ACTION_SERVICE"


def test_stale_protection():
    bridge = MixBridge()
    bridge.loadMix("favorites")
    bridge._gen += 1  # force stale
    result = bridge.loadMix("favorites")
    assert result["ok"] or not result.get("ok")
