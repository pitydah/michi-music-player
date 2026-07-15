"""Tests for Playback v12 — PlaybackService must exist before READY, delegates to NowPlayingBridge."""
from unittest.mock import MagicMock, patch

import pytest


class TestPlaybackBridgeCreation:
    def test_requires_player_service(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        with pytest.raises(Exception):
            PlaybackBridge()

    def test_creation_with_player(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert pb is not None

    def test_creation_with_playback_ctrl(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(playback_ctrl=MagicMock())
        assert pb is not None

    def test_creation_creates_nowplaying(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert hasattr(pb, '_nowplaying')


class TestPlaybackState:
    def test_track_title_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.trackTitle, str)

    def test_track_artist_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.trackArtist, str)

    def test_is_playing_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.isPlaying, bool)

    def test_volume_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.volume, int)

    def test_duration_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.duration, int)

    def test_position_default(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.position, int)

    def test_has_track(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        assert isinstance(pb.hasTrack, bool)


class TestPlaybackCommands:
    def test_toggle_play(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.togglePlay()
        assert isinstance(result, dict)

    def test_next(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.next()
        assert isinstance(result, dict)

    def test_previous(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.previous()
        assert isinstance(result, dict)

    def test_set_volume(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.setVolume(50)
        assert isinstance(result, dict)

    def test_toggle_shuffle(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.toggleShuffle()
        assert isinstance(result, dict)

    def test_toggle_repeat(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.toggleRepeat()
        assert isinstance(result, dict)

    def test_clear_queue(self):
        from ui_qml_bridge.playback_bridge import PlaybackBridge
        pb = PlaybackBridge(player_service=MagicMock())
        result = pb.clearQueue()
        assert isinstance(result, dict)
