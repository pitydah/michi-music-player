import pytest


class TestTogglePlayPause:
    """PLAYBACK-CONTROLS-R1: the canonical three-state toggle lives in the
    bridge — QML never knows transport semantics."""

    def test_toggle_maps_all_three_states(self, qapp):
        from pathlib import Path

        from michi.application.playback_service import PlaybackService
        from michi.domain.playback import PlaybackStatus
        from michi.presentation.playback_bridge import PlaybackBridge
        from tests.conftest import FakeAudioPort

        audio = FakeAudioPort()
        service = PlaybackService(audio)
        bridge = PlaybackBridge(service)
        # a committed logical track exists (as after acceptance)
        service._state.file_path = Path("/m/a.flac")
        service._accepted = True
        # STOPPED → play (intent armed, backend truth follows)
        bridge.toggle_play_pause()
        assert audio.state == "playing"
        service._on_playback_state_changed(PlaybackStatus.PLAYING)
        assert service.state.status == PlaybackStatus.PLAYING
        # PLAYING → pause
        bridge.toggle_play_pause()
        assert audio.state == "paused"
        service._on_playback_state_changed(PlaybackStatus.PAUSED)
        assert service.state.status == PlaybackStatus.PAUSED
        # PAUSED → resume (NOT play)
        bridge.toggle_play_pause()
        assert audio.state == "playing"
        service._on_playback_state_changed(PlaybackStatus.PLAYING)
        assert service.state.status == PlaybackStatus.PLAYING
        # and the cycle continues: PLAYING → pause
        bridge.toggle_play_pause()
        assert audio.state == "paused"

    def test_command_failure_surfaces_signal(self, qapp):
        from michi.application.playback_service import PlaybackService
        from michi.presentation.playback_bridge import PlaybackBridge
        from tests.conftest import FakeAudioPort

        audio = FakeAudioPort()
        service = PlaybackService(audio)
        bridge = PlaybackBridge(service)
        failed = []
        bridge.command_failed.connect(lambda cmd, msg: failed.append((cmd, msg)))
        # hold the lease → play must fail with a visible signal
        lease = service.acquire_engine_switch_lease()
        try:
            bridge.play()
        finally:
            lease.release()
        assert failed and failed[0][0] == "play"
        assert "audio engine" in failed[0][1].lower()
        # after release, play works again and no failure is emitted
        failed.clear()
        bridge.play()
        assert failed == []

    def test_unexpected_failure_is_signalled_and_reraised(self, qapp):
        from michi.application.playback_service import PlaybackService
        from michi.presentation.playback_bridge import PlaybackBridge
        from tests.conftest import FakeAudioPort

        audio = FakeAudioPort()
        service = PlaybackService(audio)
        bridge = PlaybackBridge(service)
        failed = []
        bridge.command_failed.connect(lambda cmd, msg: failed.append((cmd, msg)))

        def unexpected():
            raise ValueError("programming defect")

        service.pause = unexpected
        with pytest.raises(ValueError, match="programming defect"):
            bridge.pause()
        assert failed == [("pause", "Playback could not complete the command.")]
