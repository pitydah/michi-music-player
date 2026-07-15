"""DS — Lyrics completo: embedded, sidecar, providers, sync/unsync, edit, save, offset, cache, cancel."""
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


def test_embedded_lyrics(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._set_result("done", lyrics="Embedded line 1\nEmbedded line 2", source="embedded")
    assert bridge.lyrics == "Embedded line 1\nEmbedded line 2"
    assert bridge.source == "embedded"
    assert bridge.status == "done"


def test_sidecar_lrc_parsing():
    lrc = "[00:05.00]Sidecar line 1\n[00:10.00]Sidecar line 2"
    lines = _parse_lrc(lrc)
    assert len(lines) == 2
    assert lines[0]["time"] == 5.0
    assert lines[1]["text"] == "Sidecar line 2"


def test_provider_lrclib_search(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.search("Bohemian Rhapsody", "Queen", "A Night at the Opera", 354)
    assert result["ok"]
    assert bridge.status == "searching"
    assert mock_worker.run_task.called


def test_synchronized_lyrics_property(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    lrc = "[00:01.00]Sync A\n[00:03.50]Sync B"
    bridge._synced_lyrics = _parse_lrc(lrc)
    bridge._status = "done"
    assert bridge.hasSyncedLyrics is True
    assert len(bridge.syncedLyrics) == 2


def test_unsynchronized_fallback(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge.saveLocalLyrics("Plain text without timestamps")
    assert bridge.lyrics == "Plain text without timestamps"
    assert bridge.hasSyncedLyrics is False


def test_edit_and_save(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result1 = bridge.saveLocalLyrics("Original text")
    assert result1["ok"]
    bridge.saveLocalLyrics("Edited text")
    assert bridge.lyrics == "Edited text"


def test_offset_affects_get_active_line(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    lrc = "[00:02.00]Line A\n[00:04.00]Line B"
    bridge._synced_lyrics = _parse_lrc(lrc)
    assert bridge.getActiveLine(3000) == 0
    assert bridge.getActiveLine(5000) == 1


def test_cache_stores_and_retrieves(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    key = _make_cache_key("CachedSong", "CachedArtist", "CachedAlbum", 200)
    bridge._cache[key] = {"lyrics": "Cached", "synced_lyrics": "", "source": "LRCLIB", "timestamp": 100}
    bridge._cache_order.append(key)
    bridge.search("CachedSong", "CachedArtist", "CachedAlbum", 200)
    assert bridge.status == "done"
    assert bridge.lyrics == "Cached"


def test_cache_trim(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    for i in range(60):
        key = _make_cache_key(f"Song{i}", "Artist", "", 100)
        bridge._cache[key] = {"lyrics": f"lyrics{i}", "synced_lyrics": "", "source": "LRCLIB", "timestamp": float(i)}
        bridge._cache_order.append(key)
    bridge._trim_cache()
    assert len(bridge._cache) <= 50


def test_cancel_search_during_request(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._status = "searching"
    bridge._active_search_id = 42
    bridge.cancelSearch()
    assert bridge.status == "idle"
    assert bridge._active_search_id == 0
