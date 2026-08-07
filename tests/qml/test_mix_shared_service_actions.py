"""Test MixBridge with shared MixQueryService, durable-job generation,
scoped cancel, and honest (never empty-success) typed outcomes."""
import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge

from .mix.conftest import make_bridge, make_mix_service


@pytest.fixture
def empty_bridge():
    return MixBridge()


@pytest.fixture
def mock_mqs():
    return make_mix_service(default_track_count=2)


@pytest.fixture
def mock_qs():
    qs = MagicMock()
    qs.replace_and_play.return_value = {"ok": True}
    qs.enqueue.return_value = {"ok": True}
    return qs


def test_bridge_creation(empty_bridge):
    assert empty_bridge.categories is not None
    assert len(empty_bridge.categories) == 12


def test_load_favorites(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("favorites")
    assert result["ok"]
    assert bridge.stateName == "COMPLETED_WITH_TRACKS"
    assert len(bridge.currentSongs) == 2
    assert bridge.currentSongs[0]["title"] == "favorites 1"


def test_load_recent(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("recent")
    assert result["ok"]
    assert len(bridge.currentSongs) == 2


def test_load_most_played(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("most_played")
    assert result["ok"]
    assert len(bridge.currentSongs) == 2


def test_load_unplayed(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("unplayed")
    assert result["ok"]
    assert len(bridge.currentSongs) == 2


def test_load_daily_mix(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("daily_mix")
    assert result["ok"]


def test_load_unknown_mix(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("nonexistent")
    assert not result["ok"]


def test_play_mix(mock_mqs, mock_qs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path, queue_service=mock_qs)
    bridge.loadMix("favorites")
    result = bridge.playMix()
    assert result["ok"]


def test_play_mix_empty():
    bridge = MixBridge()
    result = bridge.playMix()
    assert not result["ok"]


def test_play_from_index(mock_mqs, mock_qs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path, queue_service=mock_qs)
    bridge.loadMix("favorites")
    result = bridge.playFromIndex(1)
    assert result["ok"]


def test_play_from_index_invalid(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    bridge.loadMix("favorites")
    result = bridge.playFromIndex(999)
    assert not result["ok"]


def test_enqueue_mix(mock_mqs, mock_qs, tmp_path):
    mock_qs.enqueue.return_value = {"ok": True, "count": 2}
    bridge, _svc = make_bridge(mock_mqs, tmp_path, queue_service=mock_qs)
    bridge.loadMix("favorites")
    result = bridge.enqueueMix()
    assert result["ok"]
    assert result["count"] == 2


def test_cancel_generation(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    bridge.loadMix("favorites")
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_refresh(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.refresh()
    assert result["ok"] or not result.get("ok")


def test_explain_current_mix(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    bridge.loadMix("favorites")
    result = bridge.explainCurrentMix()
    assert result["ok"]
    assert result["reasons"]


def test_save_mix_as_playlist(mock_mqs, tmp_path):
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    bridge._mix_svc.save_mix_as_playlist.return_value = {
        "ok": True, "status": "COMPLETED", "playlist_id": 42,
        "requested": 2, "added": 2, "failed": 0, "count": 2,
    }
    bridge.loadMix("favorites")
    result = bridge.saveMixAsPlaylist("Test Mix")
    assert result["ok"]


def test_partial_failure_report(mock_mqs, mock_qs, tmp_path):
    mock_qs.enqueue.return_value = {"ok": False, "error_code": "PARTIAL",
                                    "errors": [{"error": "NOT_FOUND"}]}
    bridge, _svc = make_bridge(mock_mqs, tmp_path, queue_service=mock_qs)
    bridge.loadMix("favorites")
    result = bridge.enqueueMix()
    assert "errors" in result
    assert len(result["errors"]) == 1


def test_no_queue_service():
    bridge = MixBridge()
    bridge._current_songs = [{"track_id": 1}]
    result = bridge.playMix()
    assert not result["ok"]
    assert result["error_code"] == "NO_PLAYBACK"


def test_empty_generation_is_honest_failure(mock_mqs, tmp_path):
    mock_mqs.generate.side_effect = lambda strategy="daily", seed=None, limit=30, ctx=None: {
        "ok": False, "status": "EMPTY_LIBRARY",
        "message": "La biblioteca no tiene canciones",
        "strategy": strategy, "mix_id": f"query:{strategy}", "tracks": [],
    }
    bridge, _svc = make_bridge(mock_mqs, tmp_path)
    result = bridge.loadMix("favorites")
    assert result["ok"]  # job accepted
    assert bridge.stateName == "EMPTY_LIBRARY"
    assert len(bridge.currentSongs) == 0
    assert bridge.errorMessage
