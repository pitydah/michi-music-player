"""Tests for Lyrics v12 — LRCLIB lyrics with async search, cache, timeout, cancel."""
from unittest.mock import MagicMock

import pytest


class TestLyricsBridgeCreation:
    def test_requires_worker_manager(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        with pytest.raises(Exception):
            LyricsBridge()

    def test_creation(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb is not None

    def test_lyrics_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb.lyrics == ""

    def test_status_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb.status == "idle"

    def test_source_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb.source == ""

    def test_has_synced_lyrics_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb.hasSyncedLyrics is False

    def test_error_message_default(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        assert lb.errorMessage == ""


class TestLyricsOperations:
    def test_search_with_empty(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.search("", "", "", 0)
        assert result.get("ok")

    def test_search_manual_empty(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.searchManual("")
        assert not result.get("ok")

    def test_search_manual(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.searchManual("test song")
        assert isinstance(result, dict)

    def test_cancel_search(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        lb.search("test", "artist", "", 0)
        lb.cancelSearch()
        assert lb.status in ("idle", "done", "error", "not_found")

    def test_clear_cache(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.clearCacheForCurrentTrack()
        assert result.get("ok")

    def test_save_local_lyrics(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.saveLocalLyrics("Test lyrics")
        assert result.get("ok")
        assert lb.lyrics == "Test lyrics"

    def test_refresh(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.refresh()
        assert isinstance(result, dict)

    def test_search_current_no_nowplaying(self):
        from ui_qml_bridge.lyrics_bridge import LyricsBridge
        lb = LyricsBridge(worker_manager=MagicMock())
        result = lb.searchCurrentTrack()
        assert not result.get("ok")
