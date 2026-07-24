"""Tests: Playback context bridge — connect_context_events."""

from unittest.mock import MagicMock


class TestPlaybackContextBridge:

    def _make_ctrl(self):
        ctx = MagicMock()
        pb = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx
        win._playback = pb
        queue = MagicMock()
        queue.count = 2
        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win, queue_service=queue)
        ctrl.connect_context_events(playback=pb, context_svc=ctx)
        return ctrl, ctx, pb, win

    def test_track_changed_registers_now_playing_and_played(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.track_changed.connect.call_args[0][0]
        handler("Song", "Artist")

        ctx.record_now_playing_updated.assert_called_once_with(
            title="Song", artist="Artist")
        ctx.record_track_played_title_artist.assert_called_once_with(
            title="Song", artist="Artist")

    def test_same_track_twice_no_duplicate_played(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.track_changed.connect.call_args[0][0]
        handler("Song", "Artist")
        ctx.record_track_played_title_artist.reset_mock()
        handler("Song", "Artist")

        ctx.record_track_played_title_artist.assert_not_called()
        ctx.record_now_playing_updated.assert_called()

    def test_different_track_emits_played(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.track_changed.connect.call_args[0][0]
        handler("Song A", "Artist A")
        ctx.record_track_played_title_artist.reset_mock()
        handler("Song B", "Artist B")

        ctx.record_track_played_title_artist.assert_called_once_with(
            title="Song B", artist="Artist B")

    def test_state_changed_paused_registers_paused(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.state_changed.connect.call_args[0][0]
        handler("paused")
        ctx.record_track_paused.assert_called_once()

    def test_state_changed_not_paused_does_nothing(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.state_changed.connect.call_args[0][0]
        handler("playing")
        ctx.record_track_paused.assert_not_called()

    def test_queue_changed_records_updated(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.queue_changed.connect.call_args_list[0][0][0]
        handler([{"filepath": "/a.flac"}, {"filepath": "/b.flac"}])
        ctx.record_queue_updated.assert_called_once_with(count=2, source="playback")

    def test_no_crash_without_context_svc(self):
        pb = MagicMock()
        win = MagicMock()
        win._services = None
        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win)
        ctrl.connect_context_events(playback=pb, context_svc=None)

    def test_connect_context_events_is_idempotent(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        ctrl.connect_context_events(playback=pb, context_svc=ctx)
        assert pb.track_changed.connect.call_count == 1
        assert pb.state_changed.connect.call_count == 1
        assert pb.queue_changed.connect.call_count == 1

    def test_initial_empty_queue_does_not_record_clear(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.queue_changed.connect.call_args[0][0]
        handler([])
        ctx.record_queue_cleared.assert_not_called()
        ctx.record_queue_updated.assert_not_called()

    def test_non_empty_queue_records_updated(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.queue_changed.connect.call_args[0][0]
        handler([{"filepath": "/a.flac"}])
        ctx.record_queue_updated.assert_called_once_with(count=1, source="playback")

    def test_active_to_empty_queue_records_only_cleared(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        handler = pb.queue_changed.connect.call_args[0][0]
        handler([{"filepath": "/a.flac"}])
        ctx.record_queue_updated.assert_called_once()
        ctx.reset_mock()
        handler([])
        ctx.record_queue_cleared.assert_called_once_with(reason="queue_empty")
        ctx.record_queue_updated.assert_not_called()

    def test_enqueue_with_context_added_count(self):
        ctrl, ctx, pb, win = self._make_ctrl()
        ctrl.enqueue_with_context(["/new/a.flac", "/new/b.flac"], source="test")
        ctrl._queue.enqueue.assert_called_once_with(
            ["/new/a.flac", "/new/b.flac"], play_now=True
        )
        pb.enqueue.assert_not_called()
        ctx.record_queue_updated.assert_called_once_with(
            count=2, source="test", added_count=2)

    def test_enqueue_with_context_single_track_title(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        ctrl.enqueue_with_context(["/new/a.flac"], source="album",
                                  title="Song", artist="Artist")
        ctx.record_track_queued.assert_called_once_with(
            title="Song", artist="Artist", source="album")

    def test_enqueue_with_context_batch_no_title(self):
        ctrl, ctx, pb, _ = self._make_ctrl()
        ctrl.enqueue_with_context(["/a.flac", "/b.flac"], source="genre")
        ctx.record_track_queued.assert_called_once()
        call_kwargs = ctx.record_track_queued.call_args[1]
        assert call_kwargs.get("source") == "genre"
        assert "title" not in call_kwargs or call_kwargs.get("title") == ""
