"""NowPlayingPage and NowPlayingBar runtime tests — state machine, sync, accessibility."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.nowplaying_bridge import NowPlayingBridge

pytestmark = [pytest.mark.qml_module("queue")]


def _make_bridge(has_track=True, is_playing=False, has_player=True):
    player = MagicMock() if has_player else None
    queue = MagicMock()
    quality = MagicMock()
    quality.probe.return_value = {"ok": False}
    bridge = NowPlayingBridge(
        player_service=player,
        queue_service=queue,
        audio_quality_adapter=quality,
    )
    if has_track:
        bridge._track_title = "Test Track"
        bridge._track_artist = "Test Artist"
    if player:
        player.current = MagicMock()
        player.current.title = "Test Track"
        player.current.artist = "Test Artist"
    return bridge


class TestNowPlayingPageStateMachine:
    """Verify NowPlayingPage state logic."""

    def test_empty_when_no_track(self):
        # When player has no current track, _track_title stays at default "—"
        player = MagicMock()
        player.current = None
        # Prevent _current_path() from returning a truthy MagicMock string
        player.current_filepath = ""
        player.current_path = ""
        quality = MagicMock()
        quality.probe.return_value = {"ok": False}
        bridge = NowPlayingBridge(
            player_service=player,
            queue_service=MagicMock(),
            audio_quality_adapter=quality,
        )
        assert bridge._track_title == "—"
        assert not bridge.hasTrack

    def test_ready_when_has_track(self):
        bridge = _make_bridge(has_track=True)
        assert bridge.hasTrack

    def test_error_when_no_backend(self):
        bridge = _make_bridge()
        bridge._backend_available = False
        assert not bridge.backendAvailable

    def test_command_pending_is_false_initially(self):
        bridge = _make_bridge()
        assert not bridge.commandPending

    def test_toggle_play_sets_command_pending(self):
        bridge = _make_bridge()
        bridge.togglePlay()
        # After command completes, pending should be False
        assert not bridge.commandPending

    def test_track_title_updates(self):
        bridge = _make_bridge()
        bridge._on_track("New Title", "New Artist", "New Album")
        assert bridge.trackTitle == "New Title"
        assert bridge.trackArtist == "New Artist"
        assert bridge.trackAlbum == "New Album"

    def test_position_updates(self):
        bridge = _make_bridge()
        bridge._on_position(42.5)
        assert bridge.position == 42

    def test_duration_updates(self):
        bridge = _make_bridge()
        bridge._on_duration(240.0)
        assert bridge.duration == 240

    def test_volume_updates(self):
        bridge = _make_bridge()
        bridge._on_volume(50)
        assert bridge.volume == 50
        assert not bridge.muted

    def test_volume_zero_sets_muted(self):
        bridge = _make_bridge()
        bridge._on_volume(0)
        assert bridge.muted

    def test_playback_state_updates(self):
        bridge = _make_bridge()
        bridge._on_state("playing")
        assert bridge.isPlaying
        bridge._on_state("paused")
        assert not bridge.isPlaying

    def test_error_message_updates(self):
        bridge = _make_bridge()
        bridge._on_error("Something went wrong")
        assert "error" in bridge.errorMessage.lower() or bridge.errorMessage != ""


class TestNowPlayingTransport:
    """Verify transport commands delegate correctly."""

    def test_toggle_play_delegates(self):
        bridge = _make_bridge()
        bridge.togglePlay()
        bridge._player.play_or_resume.assert_called()

    def test_next_delegates_to_queue(self):
        bridge = _make_bridge()
        bridge._queue_service.next.return_value = {"ok": True}
        result = bridge.next()
        bridge._queue_service.next.assert_called_once()

    def test_previous_delegates_to_queue(self):
        bridge = _make_bridge()
        bridge._queue_service.previous.return_value = {"ok": True}
        result = bridge.previous()
        bridge._queue_service.previous.assert_called_once()

    def test_seek_updates_position(self):
        bridge = _make_bridge()
        bridge._duration = 200
        bridge._player.seek.return_value = None
        result = bridge.seek(100)
        assert result.get("ok") is True
        assert bridge.position == 100

    def test_seek_clamps_to_duration(self):
        bridge = _make_bridge()
        bridge._duration = 100
        bridge._player.seek.return_value = None
        result = bridge.seek(999)
        assert result.get("ok") is True
        assert bridge.position == 100  # Clamped to duration

    def test_set_volume_updates(self):
        bridge = _make_bridge()
        result = bridge.setVolume(75)
        assert result.get("ok") is True
        assert bridge.volume == 75

    def test_toggle_mute(self):
        bridge = _make_bridge()
        bridge._volume = 80
        bridge.toggleMute()
        assert bridge.volume == 0
        assert bridge.muted

    def test_toggle_mute_restores(self):
        bridge = _make_bridge()
        bridge._volume = 0
        bridge._previous_volume = 50
        bridge.toggleMute()
        assert bridge.volume == 50
        assert not bridge.muted

    def test_toggle_shuffle_delegates(self):
        bridge = _make_bridge()
        bridge._queue_service.toggle_shuffle.return_value = {"ok": True}
        bridge._queue_service.shuffle = True
        bridge.toggleShuffle()
        bridge._queue_service.toggle_shuffle.assert_called_once()

    def test_toggle_repeat_delegates(self):
        bridge = _make_bridge()
        bridge._queue_service.toggle_repeat.return_value = {"ok": True}
        bridge._queue_service.repeat = "all"
        bridge.toggleRepeat()
        bridge._queue_service.toggle_repeat.assert_called_once()


class TestNowPlayingAccessibility:
    """Verify accessibility attributes in QML files."""

    def _read_qml(self, relpath):
        from pathlib import Path
        base = Path(__file__).resolve().parents[3] / "ui_qml"
        return (base / relpath).read_text()

    def test_nowplaying_page_has_accessible_role(self):
        content = self._read_qml("pages/nowplaying/NowPlayingPage.qml")
        assert "Accessible.role" in content

    def test_nowplaying_page_has_accessible_name(self):
        content = self._read_qml("pages/nowplaying/NowPlayingPage.qml")
        assert "Accessible.name" in content

    def test_nowplaying_page_has_accessible_description(self):
        content = self._read_qml("pages/nowplaying/NowPlayingPage.qml")
        assert "Accessible.description" in content

    def test_nowplaying_bar_has_accessible_role(self):
        content = self._read_qml("components/NowPlayingBar.qml")
        assert "Accessible.role" in content

    def test_nowplaying_bar_has_accessible_name(self):
        content = self._read_qml("components/NowPlayingBar.qml")
        assert "Accessible.name" in content

    def test_nowplaying_bar_has_accessible_description(self):
        content = self._read_qml("components/NowPlayingBar.qml")
        assert "Accessible.description" in content
