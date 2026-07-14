"""Test lyrics workflow through LyricsBridge."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.lyrics_bridge import LyricsBridge, _parse_lrc


@pytest.fixture
def mock_nowplaying():
    np = MagicMock()
    np.trackTitle = "Bohemian Rhapsody"
    np.trackArtist = "Queen"
    np.trackAlbum = "A Night at the Opera"
    np.trackDuration = 354
    np.position = 0
    return np


@pytest.fixture
def mock_worker():
    wm = MagicMock()
    wm.run_task.return_value = True
    return wm


def test_initial_state(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    assert bridge.status == "idle"
    assert bridge.lyrics == ""
    assert bridge.hasSyncedLyrics is False


def test_search_returns_dict(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.search("Bohemian Rhapsody", "Queen", "A Night at the Opera", 354)
    assert isinstance(result, dict)


def test_search_sets_searching_status(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge.search("Test", "Artist")
    assert bridge.status == "searching"


def test_cache_hit(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._cache["Test||Artist||Album||300"] = {
        "lyrics": "Cached lyrics", "synced_lyrics": "",
        "source": "cache", "timestamp": 1000,
    }
    bridge.search("Test", "Artist", "Album", 300)
    assert bridge.status == "done"
    assert bridge.lyrics == "Cached lyrics"


def test_cancel_search(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._status = "searching"
    bridge.cancelSearch()
    assert bridge.status == "idle"
    assert bridge._active_search_id == 0


def test_parse_lrc():
    lrc = "[00:01.00]Line 1\n[00:02.50]Line 2\n[00:03.00]Line 3"
    lines = _parse_lrc(lrc)
    assert len(lines) == 3
    assert lines[0]["text"] == "Line 1"
    assert lines[0]["time"] == 1.0
    assert lines[1]["time"] == 2.5


def test_parse_lrc_unparseable():
    lrc = "Invalid line\n[bad]Another"
    lines = _parse_lrc(lrc)
    assert len(lines) == 2


def test_clear_cache_for_current_track(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._current_title = "Test"
    bridge._current_artist = "Artist"
    bridge._cache["Test||Artist||||0"] = {"lyrics": "x"}
    bridge._cache_order.append("Test||Artist||||0")
    result = bridge.clearCacheForCurrentTrack()
    assert result["ok"]
    assert len(bridge._cache) == 0


def test_no_blocking_on_playback_while_searching(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge.search("Test", "Artist")
    assert bridge.status == "searching"
    # Playback is NOT blocked — search is async
    assert mock_worker.run_task.called
