"""Tests for play_next semantics — enqueue_next in PlayerService."""
from __future__ import annotations

from unittest.mock import MagicMock


class _MockCtx:
    toast = MagicMock()
    playback = MagicMock()


class _MockWin:
    _ctx = _MockCtx()
    _playback = MagicMock()
    _playback_ctrl = MagicMock()
    _metadata_editor = MagicMock()
    _db = MagicMock()
    _nav_ctrl = MagicMock()
    _workers = MagicMock()
    _workers.run_task = MagicMock()


class TestEnqueueNext:
    def test_enqueue_next_inserts_after_current(self):
        from audio.player_service import PlayerService
        engine = MagicMock()
        svc = PlayerService.__new__(PlayerService)
        svc._engine = engine
        svc._hybrid = MagicMock(active_id="gstreamer")
        svc._retry_url = None

        svc.enqueue_next(["/p/s1.flac", "/p/s2.flac"])
        engine.enqueue_next.assert_called_once_with(["/p/s1.flac", "/p/s2.flac"])

    def test_enqueue_next_empty(self):
        from audio.player_service import PlayerService
        engine = MagicMock()
        svc = PlayerService.__new__(PlayerService)
        svc._engine = engine
        svc._hybrid = MagicMock(active_id="gstreamer")
        svc.enqueue_next([])
        engine.enqueue_next.assert_not_called()


class TestPlayNextAlbum:
    def test_play_next_inserts_when_queue_exists(self):
        from ui.controllers.album_controller import AlbumController
        w = _MockWin()
        w._playback.get_queue.return_value = ["/existing/s.flac"]
        w._playback.enqueue_next = MagicMock()
        ctrl = AlbumController(w)
        tracks = [MagicMock(filepath="/album/t1.flac")]
        ctrl.play_next_album(tracks)
        w._playback.enqueue_next.assert_called_once()

    def test_play_next_fallback_empty_queue(self):
        from ui.controllers.album_controller import AlbumController
        w = _MockWin()
        w._playback.get_queue.return_value = []
        ctrl = AlbumController(w)
        tracks = [MagicMock(filepath="/album/t1.flac")]
        ctrl.play_next_album(tracks)
        w._playback.enqueue.assert_called_once()

    def test_play_next_empty_tracks(self):
        from ui.controllers.album_controller import AlbumController
        w = _MockWin()
        ctrl = AlbumController(w)
        ctrl.play_next_album([])
        w._ctx.toast.show.assert_called()
