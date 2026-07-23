"""Tests: Playback mode context — shuffle, repeat."""

from unittest.mock import MagicMock


class TestPlaybackModeContext:

    def test_toggle_shuffle_records_mode_changed(self):
        ctx = MagicMock()
        pb = MagicMock()
        queue = MagicMock()
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx
        win._playback = pb

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win, queue_service=queue)

        queue.shuffle = True
        ctrl.toggle_shuffle_with_context()

        queue.toggle_shuffle.assert_called_once()
        pb.toggle_shuffle.assert_not_called()
        ctx.record_playback_mode_changed.assert_called_once_with(shuffle=True)

    def test_toggle_repeat_records_mode_changed(self):
        ctx = MagicMock()
        pb = MagicMock()
        queue = MagicMock()
        queue.toggle_repeat.return_value = {"ok": True, "mode": "one"}
        win = MagicMock()
        win._services = None
        win._ctx.context_svc = ctx
        win._playback = pb

        from core.playback_controller import PlaybackController
        ctrl = PlaybackController(win, queue_service=queue)

        ctrl.toggle_repeat_with_context()

        queue.toggle_repeat.assert_called_once()
        pb.toggle_repeat.assert_not_called()
        ctx.record_playback_mode_changed.assert_called_once_with(repeat="one")
