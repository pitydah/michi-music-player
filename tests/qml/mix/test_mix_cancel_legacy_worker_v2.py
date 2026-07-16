import pytest
from unittest.mock import MagicMock

from ui_qml_bridge.mix_bridge import MixBridge
from ui_qml_bridge.query_executor import QueryExecutor
from core.worker_manager import WorkerManager
pytestmark = [pytest.mark.qml_module("mix")]


@pytest.fixture
def mock_wm():
    wm = MagicMock(spec=WorkerManager)
    wm.cancel_all = MagicMock(return_value=None)
    wm.run_task = MagicMock(return_value=MagicMock())
    return wm


@pytest.fixture
def mock_mqs():
    mqs = MagicMock()
    mqs.favorites.return_value = [
        {"track_id": 1, "title": "Fav 1", "artist": "A", "album": "Al", "duration": 200, "reason": "Favorito"},
        {"track_id": 2, "title": "Fav 2", "artist": "B", "album": "Bl", "duration": 180, "reason": "Favorito"},
    ]
    mqs.recent.return_value = []
    mqs.most_played.return_value = []
    mqs.unplayed.return_value = []
    return mqs


def test_cancel_generation_calls_worker_manager_cancel_all(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    bridge.loadMix("favorites")
    result = bridge.cancelGeneration()
    assert result["ok"]
    mock_wm.cancel_all.assert_called_with(owner="mix_bridge")


def test_cancel_generation_increments_counter(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    gen_before = bridge._generation
    bridge.cancelGeneration()
    assert bridge._generation == gen_before + 1


def test_cancel_generation_increments_counter_and_returns_cancelled(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    gen_before = bridge._generation
    result = bridge.cancelGeneration()
    assert result["cancelled"] == gen_before


def test_cancel_generation_still_ok_without_wm(mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs)
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_cancel_twice_calls_wm_twice(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    bridge.cancelGeneration()
    bridge.cancelGeneration()
    assert mock_wm.cancel_all.call_count == 2


def test_load_after_cancel_increments_generation(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    bridge.cancelGeneration()
    gen_after_cancel = bridge._generation
    bridge.loadMix("favorites")
    assert bridge._generation > gen_after_cancel


def test_cancel_with_query_executor(mock_mqs):
    qe = MagicMock(spec=QueryExecutor)
    qe.cancel_owner = MagicMock()
    bridge = MixBridge(mix_service=mock_mqs, query_executor=qe)
    result = bridge.cancelGeneration()
    assert result["ok"]


def test_cancel_clears_loaded_songs(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    bridge.loadMix("favorites")
    assert len(bridge.currentSongs) == 2
    bridge.cancelGeneration()
    assert len(bridge.currentSongs) == 0


def test_cancel_after_load_play_still_works(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm,
                       playback_service=MagicMock())
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.playMix()
    assert result["ok"] is False


def test_cancel_after_load_enqueue_still_works(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm,
                       queue_service=MagicMock())
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.enqueueMix()
    assert result["ok"] is False


def test_cancel_after_load_explain_still_works(mock_wm, mock_mqs):
    bridge = MixBridge(mix_service=mock_mqs, job_service=mock_wm)
    bridge.loadMix("favorites")
    bridge.cancelGeneration()
    result = bridge.explainCurrentMix()
    assert result["ok"] is False
