"""NowPlayingPage and NowPlayingBar runtime tests — state machine, sync, accessibility."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

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

    @pytest.mark.parametrize("title", ["", None, "—"])
    def test_empty_title_without_path_has_no_track(self, title: str | None) -> None:
        player = MagicMock()
        player.current = None
        player.current_filepath = ""
        player.current_path = ""
        bridge = NowPlayingBridge(player_service=player)
        bridge._track_title = title

        assert not bridge.hasTrack

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
        assert bridge.commandPending
        assert bridge.commandState == "pending"

        bridge._on_state("playing")

        assert not bridge.commandPending
        assert bridge.commandState == "confirmed"

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

    @pytest.mark.parametrize(
        ("property_name", "notify_signal"),
        [
            ("trackTitle", "trackChanged"),
            ("trackArtist", "trackChanged"),
            ("trackAlbum", "trackChanged"),
            ("coverPath", "coverChanged"),
            ("isPlaying", "playbackStateChanged"),
            ("position", "positionChanged"),
            ("duration", "durationChanged"),
            ("volume", "volumeChanged"),
            ("muted", "volumeChanged"),
            ("repeatMode", "playbackStateChanged"),
            ("shuffleEnabled", "playbackStateChanged"),
            ("currentFilePath", "trackChanged"),
            ("liveSource", "playbackStateChanged"),
            ("remoteSource", "playbackStateChanged"),
            ("seekableSource", "playbackStateChanged"),
            ("sourceType", "qualityChanged"),
            ("formatLabel", "qualityChanged"),
            ("qualityLabel", "qualityChanged"),
            ("sampleRate", "qualityChanged"),
            ("bitDepth", "qualityChanged"),
            ("channels", "qualityChanged"),
            ("bitrate", "qualityChanged"),
            ("qualityInfoAvailable", "qualityChanged"),
            ("qualityLoading", "qualityChanged"),
            ("qualityError", "qualityChanged"),
            ("history", "historyChanged"),
            ("hasTrack", "trackChanged"),
            ("backendAvailable", "capabilitiesChanged"),
            ("errorMessage", "errorChanged"),
            ("lastCommand", "commandStateChanged"),
            ("lastCommandOk", "commandStateChanged"),
            ("lastCommandError", "commandStateChanged"),
            ("lastCommandMessage", "commandStateChanged"),
            ("lastCommandTimestamp", "commandStateChanged"),
            ("commandPending", "commandStateChanged"),
            ("commandState", "commandStateChanged"),
        ],
    )
    def test_property_uses_specific_notify_signal(
        self,
        property_name: str,
        notify_signal: str,
    ) -> None:
        meta_object = NowPlayingBridge.staticMetaObject
        meta_property = meta_object.property(meta_object.indexOfProperty(property_name))

        assert bytes(meta_property.notifySignal().name()).decode() == notify_signal


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

    def test_set_volume_coalesces_small_rapid_changes(self) -> None:
        bridge = _make_bridge()
        with patch(
            "ui_qml_bridge.nowplaying_bridge.time.time",
            side_effect=[100.0, 100.0, 100.0, 100.05],
        ):
            bridge.setVolume(75)
            bridge._player.set_volume.reset_mock()
            result = bridge.setVolume(76)

        assert result["data"]["coalesced"] is True
        bridge._player.set_volume.assert_not_called()

    def test_clear_history_removes_public_and_internal_entries(self) -> None:
        bridge = _make_bridge()
        bridge._history = [{"history_id": "h1", "title": "Track"}]
        bridge._history_internal_refs = {"h1": {"filepath": "/music/track.flac"}}

        bridge.clearHistory()

        assert bridge.history == []
        assert bridge._history_internal_refs == {}

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
