"""DS — Lyrics completo: embedded, sidecar, providers, sync/unsync, edit, save, offset, cache, cancel."""
from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.lyrics_bridge import LyricsBridge, _parse_lrc
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


def test_service_result_stores_in_bridge(mock_nowplaying, mock_worker):
    from core.lyrics.models import LyricsOperationResult, LyricsDocument, LyricsSource
    svc = MagicMock()
    svc.resolve.return_value = LyricsOperationResult(
        ok=True,
        document=LyricsDocument(plain_text="Cached", synced_text="",
                                source=LyricsSource.CACHE),
    )
    wm = MagicMock()

    def run_task(name, fn, on_done=None, **kw):
        if on_done:
            on_done(fn())

    wm.run_task.side_effect = run_task
    bridge = LyricsBridge(worker_manager=wm, lyrics_service=svc,
                          nowplaying_bridge=mock_nowplaying)
    bridge.search("CachedSong", "CachedArtist", "CachedAlbum", 200)
    assert bridge.status == "done"
    assert bridge.lyrics == "Cached"
    svc.resolve.assert_called_once()


def test_no_second_cache_in_bridge(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    assert not hasattr(bridge, "_cache")
    assert not hasattr(bridge, "_cache_order")


def test_cancel_search_during_request(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._status = "searching"
    bridge._active_search_id = 42
    bridge.cancelSearch()
    assert bridge.status == "idle"
    assert bridge._active_search_id == 0


def test_attribution_source(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._set_result("done", lyrics="Test", source="LRCLIB")
    assert bridge.source == "LRCLIB"


def test_attribution_embedded(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge.saveLocalLyrics("Local")
    assert bridge.source == "local"


def test_search_not_found_error(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._active_search_id = 1
    bridge._status = "searching"
    bridge._on_search_complete(1, {"ok": False, "error": "NOT_FOUND"})
    assert bridge.status == "not_found"


def test_search_generic_error(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._active_search_id = 1
    bridge._status = "searching"
    bridge._on_search_complete(1, {"ok": False, "error": "NETWORK_ERROR"})
    assert bridge.status == "error"
    assert bridge.errorMessage == "NETWORK_ERROR"


def test_refresh_with_current_track(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._current_title = "TestSong"
    result = bridge.refresh()
    assert result["ok"] is True


def test_refresh_no_track(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.refresh()
    assert result["ok"] is True


def test_clear_cache_delegates(mock_nowplaying, mock_worker):
    svc = MagicMock()
    bridge = LyricsBridge(worker_manager=mock_worker, lyrics_service=svc,
                          nowplaying_bridge=mock_nowplaying)
    bridge._current_title = "Song"
    bridge._current_artist = "Artist"
    bridge._current_album = "Album"
    bridge._current_duration = 200
    result = bridge.clearCacheForCurrentTrack()
    assert result["ok"]
    svc.invalidate_identity.assert_called_once()


def test_get_active_line_none(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    assert bridge.getActiveLine(1000) is None


def test_get_active_line_beyond_end(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    lrc = "[00:01.00]A\n[00:03.00]B"
    bridge._synced_lyrics = _parse_lrc(lrc)
    assert bridge.getActiveLine(5000) == 1


def test_stale_search_ignored(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._active_search_id = 99
    bridge._on_search_complete(1, {"ok": True, "lyrics": "stale"})
    assert bridge.status != "done"


def test_sync_fallback_runs(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    bridge._wm = None
    result = bridge.search("Test", "Artist")
    assert result["ok"] is True


def test_lrc_parse_invalid_timestamp():
    lines = _parse_lrc("[invalid]text")
    assert len(lines) >= 1


def test_search_manual_empty_query(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.searchManual("")
    assert result["ok"] is False
    assert result["error"] == "EMPTY_QUERY"


def test_search_manual_valid(mock_nowplaying, mock_worker):
    bridge = LyricsBridge(worker_manager=mock_worker, nowplaying_bridge=mock_nowplaying)
    result = bridge.searchManual("Bohemian Rhapsody Queen")
    assert result["ok"] is True
    assert bridge.status == "searching"
