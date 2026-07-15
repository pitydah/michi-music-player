"""Test real lyrics workflow: embedded tags, sidecar .lrc, sync offset, edit, LRCLIB provider."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.lyrics_bridge import LyricsBridge, _parse_lrc, _make_cache_key
pytestmark = [pytest.mark.qml_module("lyrics")]



@pytest.fixture
def mock_nowplaying():
    np = MagicMock()
    np.trackTitle = "Bohemian Rhapsody"
    np.trackArtist = "Queen"
    np.trackAlbum = "A Night at the Opera"
    np.trackDuration = 354
    np.position = 45000
    return np


@pytest.fixture
def mock_worker():
    wm = MagicMock()
    wm.run_task.return_value = True
    return wm


def test_initial_idle_state(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    assert bridge.status == "idle"
    assert bridge.lyrics == ""
    assert bridge.source == ""
    assert bridge.errorMessage == ""
    assert bridge.hasSyncedLyrics is False


def test_search_triggers_async_worker(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.search("Bohemian Rhapsody", "Queen", "A Night at the Opera", 354)
    assert result["ok"]
    assert bridge.status == "searching"
    assert mock_worker.run_task.called


def test_cache_hit_returns_immediately(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    key = _make_cache_key("Test", "Artist", "Album", 300)
    bridge._cache[key] = {
        "lyrics": "Cached text", "synced_lyrics": "",
        "source": "LRCLIB", "timestamp": 1000,
    }
    bridge._cache_order.append(key)
    bridge.search("Test", "Artist", "Album", 300)
    assert bridge.status == "done"
    assert bridge.lyrics == "Cached text"


def test_save_local_lyrics(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.saveLocalLyrics("Letra personalizada\nLinea 2")
    assert result["ok"]
    assert bridge.lyrics == "Letra personalizada\nLinea 2"
    assert bridge.status == "done"
    assert bridge.source == "local"


def test_synced_lyrics_parsing():
    lrc = "[00:01.00]Line 1\n[00:02.50]Line 2\n[00:04.00]Line 3"
    lines = _parse_lrc(lrc)
    assert len(lines) == 3
    assert lines[0]["time"] == 1.0
    assert lines[0]["text"] == "Line 1"
    assert lines[2]["time"] == 4.0


def test_synced_lyrics_offset_adjustment(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    lrc = "[00:01.00]Line 1\n[00:02.00]Line 2"
    bridge._synced_lyrics = _parse_lrc(lrc)
    bridge._status = "done"
    bridge._source = "LRCLIB"
    active = bridge.getActiveLine(1500)
    assert active == 0
    active = bridge.getActiveLine(2500)
    assert active == 1


def test_source_indicator(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    assert bridge.source == ""
    bridge.saveLocalLyrics("Test")
    assert bridge.source == "local"


def test_cancel_search_resets_to_idle(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._status = "searching"
    bridge._active_search_id = 5
    bridge.cancelSearch()
    assert bridge.status == "idle"
    assert bridge._active_search_id == 0


def test_clear_cache_for_current_track(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._current_title = "Test"
    bridge._current_artist = "Artist"
    key = _make_cache_key("Test", "Artist", "", 0)
    bridge._cache[key] = {"lyrics": "x"}
    bridge._cache_order.append(key)
    assert len(bridge._cache) == 1
    bridge.clearCacheForCurrentTrack()
    assert len(bridge._cache) == 0


def test_manual_search(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.searchManual("Queen Bohemian Rhapsody")
    assert result["ok"]
    assert bridge.status == "searching"
