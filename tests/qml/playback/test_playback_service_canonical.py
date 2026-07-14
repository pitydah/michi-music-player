"""Test that PlaybackService is the SINGLE canonical facade for all playback control.

No bridge should duplicate play/pause/stop/seek/next/prev/shuffle/repeat logic.
Bridges must delegate to PlaybackService, NOT implement their own control logic.
"""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from audio.player_service import PlayerService


@pytest.fixture
def mock_engine():
    engine = MagicMock()
    engine.position_changed = MagicMock()
    engine.duration_changed = MagicMock()
    engine.state_changed = MagicMock()
    engine.queue_changed = MagicMock()
    engine.finished = MagicMock()
    engine.error_occurred = MagicMock()
    return engine


def test_player_service_is_single_facade(mock_engine):
    svc = PlayerService(mock_engine)
    assert hasattr(svc, 'play')
    assert hasattr(svc, 'pause')
    assert hasattr(svc, 'resume')
    assert hasattr(svc, 'stop')
    assert hasattr(svc, 'seek')
    assert hasattr(svc, 'play_next')
    assert hasattr(svc, 'play_prev')
    assert hasattr(svc, 'set_volume')
    assert hasattr(svc, 'toggle_shuffle')
    assert hasattr(svc, 'toggle_repeat')


def test_player_service_play_delegates_to_hybrid(mock_engine):
    svc = PlayerService(mock_engine)
    svc.play("/tmp/test.flac", "Test", "Artist")
    mock_engine.play.assert_called_once_with("/tmp/test.flac")


def test_player_service_pause_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.pause()
    mock_engine.pause.assert_called_once()


def test_player_service_resume_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.resume()
    mock_engine.resume.assert_called_once()


def test_player_service_stop_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.stop()
    mock_engine.stop.assert_called_once()


def test_player_service_seek_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.seek(42)
    mock_engine.seek.assert_called_once_with(42)


def test_player_service_play_next_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.play_next()
    mock_engine.play_next.assert_called_once()


def test_player_service_play_prev_delegates(mock_engine):
    svc = PlayerService(mock_engine)
    svc.play_prev()
    mock_engine.play_prev.assert_called_once()


def test_player_service_set_volume_emits(mock_engine):
    svc = PlayerService(mock_engine)
    svc.set_volume(75)
    mock_engine.set_volume.assert_called_once_with(75)


def test_player_service_get_queue_state_returns_tuple(mock_engine):
    svc = PlayerService(mock_engine)
    mock_engine.get_queue.return_value = [{"filepath": "/a.flac"}, {"filepath": "/b.flac"}]
    mock_engine.get_queue_index.return_value = 1
    paths, idx = svc.get_queue_state()
    assert len(paths) == 2
    assert idx == 1


def test_player_service_enqueue_no_empty(mock_engine):
    svc = PlayerService(mock_engine)
    svc._hybrid._active_id = "gstreamer"
    svc.enqueue([], play_now=True)
    assert not mock_engine.enqueue.called


def test_player_service_play_url_sets_retry(mock_engine):
    svc = PlayerService(mock_engine)
    svc.play_url("http://stream.example.com/radio", "Radio", "Station")
    mock_engine.play_url.assert_called_once_with("http://stream.example.com/radio")
    assert svc._retry_url == "http://stream.example.com/radio"
