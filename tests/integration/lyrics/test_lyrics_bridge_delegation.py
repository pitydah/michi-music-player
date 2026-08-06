"""LyricsBridge thin-adapter integration (Slice 5, ADR-003).

The bridge must delegate to the canonical service and must never construct its
own LRCLIB client.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from core.lyrics.models import (
    LyricsOperationResult, LyricsDocument, LyricsSource,
)
from ui_qml_bridge.lyrics_bridge import LyricsBridge


@pytest.fixture
def sync_worker():
    """Worker mock that executes the task inline and invokes on_done."""

    def run_task(name, fn, on_done=None, **kw):
        if on_done:
            on_done(fn())
        return True

    wm = MagicMock()
    wm.run_task.side_effect = run_task
    return wm


class TestLyricsBridgeDelegation:
    def test_no_lrclib_client_constructed(self, monkeypatch):
        """The bridge must not build its own LRCLIB client (bug #25)."""
        import ui_qml_bridge.lyrics_bridge as bridge_module
        assert not hasattr(bridge_module, "LrcLibClient"), (
            "the bridge module must not reference LrcLibClient at all"
        )

        def _boom(*args, **kwargs):
            raise AssertionError("LrcLibClient must never be constructed by the bridge")

        monkeypatch.setattr("lyrics.lrclib_client.LrcLibClient", _boom)

        svc = MagicMock()
        svc.resolve.return_value = LyricsOperationResult(ok=False, code="not_found")
        bridge = LyricsBridge(worker_manager=MagicMock(), lyrics_service=svc)
        assert bridge.search("Title", "Artist")["ok"] is True

    def test_search_delegates_to_service_resolve(self, sync_worker):
        svc = MagicMock()
        svc.resolve.return_value = LyricsOperationResult(
            ok=True,
            document=LyricsDocument(
                plain_text="Line 1", synced_text="[00:01.00]Line 1",
                source=LyricsSource.REMOTE_PROVIDER,
            ),
        )
        bridge = LyricsBridge(worker_manager=sync_worker, lyrics_service=svc)
        result = bridge.search("Song", "Artist", "Album", 200)
        assert result["ok"] is True
        assert bridge.status == "done"
        assert bridge.lyrics == "Line 1"
        assert bridge.hasSyncedLyrics is True
        svc.resolve.assert_called_once()

    def test_search_manual_delegates(self, sync_worker):
        svc = MagicMock()
        svc.search_manual.return_value = LyricsOperationResult(
            ok=True,
            document=LyricsDocument(
                plain_text="Manual result", synced_text="",
                source=LyricsSource.REMOTE_PROVIDER,
            ),
        )
        bridge = LyricsBridge(worker_manager=sync_worker, lyrics_service=svc)
        result = bridge.searchManual("Queen Bohemian Rhapsody")
        assert result["ok"] is True
        assert bridge.status == "done"
        assert bridge.lyrics == "Manual result"
        svc.search_manual.assert_called_once_with("Queen Bohemian Rhapsody")

    def test_save_local_lyrics_delegates(self, tmp_path):
        import wave
        audio = tmp_path / "song.wav"
        with wave.open(str(audio), "w") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(44100)
            w.writeframes(b"\x00\x00" * 44100)

        from core.lyrics.service import LyricsService
        from core.lyrics.resolver import LyricsResolver
        from core.lyrics.registry import LyricsProviderRegistry
        from core.lyrics.storage import LyricsStorageService
        from core.lyrics.editor import LyricsEditorService
        from infrastructure.lyrics.sidecar_provider import FileSidecarProvider
        from infrastructure.lyrics.embedded_writer import MutagenEmbeddedLyricsWriter

        svc = LyricsService(
            resolver=LyricsResolver(provider_registry=LyricsProviderRegistry()),
            provider_registry=LyricsProviderRegistry(),
            storage_service=LyricsStorageService(
                sidecar_provider=FileSidecarProvider(),
                embedded_writer=MutagenEmbeddedLyricsWriter(),
            ),
            editor_service=LyricsEditorService(),
        )
        np = MagicMock()
        np.currentFilePath = str(audio)
        np.trackTitle = "Song"
        np.trackArtist = "Artist"
        bridge = LyricsBridge(worker_manager=MagicMock(), lyrics_service=svc,
                              nowplaying_bridge=np)
        result = bridge.saveLocalLyrics("Line 1\nLine 2")
        assert result["ok"] is True
        assert (tmp_path / "song.lrc").exists()
        assert result.get("source") == "local"

    def test_clear_cache_delegates_to_service(self):
        svc = MagicMock()
        bridge = LyricsBridge(worker_manager=MagicMock(), lyrics_service=svc)
        bridge._current_title = "Song"
        bridge._current_artist = "Artist"
        result = bridge.clearCacheForCurrentTrack()
        assert result["ok"] is True
        svc.invalidate_identity.assert_called_once()

    def test_manual_search_no_lrclib_import(self):
        source = __import__("pathlib").Path(
            __import__("ui_qml_bridge.lyrics_bridge", fromlist=["x"]).__file__
        ).read_text(encoding="utf-8")
        assert "LrcLibClient" not in source
        assert "search_lyrics" not in source
