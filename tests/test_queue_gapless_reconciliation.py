"""Logical gapless progression tests without a physical audio device."""
from __future__ import annotations

from unittest.mock import MagicMock

from audio.player import GStreamerEngine


def _engine() -> GStreamerEngine:
    engine = GStreamerEngine.__new__(GStreamerEngine)
    engine._queue = ["/a.flac", "/b.flac", "/c.flac"]
    engine._queue_index = 0
    engine._current = "/a.flac"
    engine._repeat = "none"
    engine._gapless_enabled = True
    engine._gapless_active = False
    engine._gapless_pending_index = None
    engine._queue_revision = 7
    engine._db = None
    engine.queue_changed = MagicMock()
    engine.queue_progressed = MagicMock()
    return engine


def test_gapless_commits_only_when_stream_starts() -> None:
    engine = _engine()
    playbin = MagicMock()

    engine._on_about_to_finish(playbin)

    assert engine._queue_index == 0
    assert engine._gapless_pending_index == 1
    engine.queue_progressed.emit.assert_not_called()

    engine._commit_gapless_progress()

    assert engine._queue_index == 1
    assert engine._current == "/b.flac"
    engine.queue_progressed.emit.assert_called_once_with(
        1, "/b.flac", "gapless", 7
    )


def test_repeat_one_preloads_current_track() -> None:
    engine = _engine()
    engine._queue_index = 1
    engine._current = "/b.flac"
    engine._repeat = "one"
    playbin = MagicMock()

    engine._on_about_to_finish(playbin)
    engine._commit_gapless_progress()

    assert engine._queue_index == 1
    engine.queue_progressed.emit.assert_called_once_with(
        1, "/b.flac", "gapless", 7
    )


def test_repeat_all_preloads_first_track_after_last() -> None:
    engine = _engine()
    engine._queue_index = 2
    engine._current = "/c.flac"
    engine._repeat = "all"
    playbin = MagicMock()

    engine._on_about_to_finish(playbin)
    engine._commit_gapless_progress()

    assert engine._queue_index == 0
    engine.queue_progressed.emit.assert_called_once_with(
        0, "/a.flac", "gapless", 7
    )


def test_eos_requests_domain_decision_without_internal_advance() -> None:
    engine = _engine()

    engine._on_media_finished_eos()

    assert engine._queue_index == 0
    engine.queue_progressed.emit.assert_called_once_with(
        0, "/a.flac", "eos", 7
    )
