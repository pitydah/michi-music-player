"""M11.1 resilience tests — failure contracts and safe degradation."""

from pathlib import Path

import pytest

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.playback import PlaybackStatus
from michi.domain.settings import SettingsState
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class FailingPlayAudioPort(FakeAudioPort):
    def __init__(self):
        super().__init__()
        self._fail_play = False

    def set_fail_play(self, v: bool):
        self._fail_play = v

    def play(self):
        if self._fail_play:
            raise RuntimeError("backend play failure")
        super().play()


class TestPlaybackResilience:
    def test_play_failure_preserves_previous_state(self):
        audio = FailingPlayAudioPort()
        svc = PlaybackService(audio)
        assert svc.state.status == PlaybackStatus.STOPPED
        audio.set_fail_play(True)
        with pytest.raises(RuntimeError):
            svc.play()
        assert svc.state.status == PlaybackStatus.STOPPED

    def test_stop_is_idempotent(self):
        audio = FakeAudioPort()
        svc = PlaybackService(audio)
        svc.load_and_play(Path("/tmp/a.mp3"))
        assert svc.state.status == PlaybackStatus.PLAYING
        svc.stop()
        assert svc.state.status == PlaybackStatus.STOPPED
        svc.stop()
        assert svc.state.status == PlaybackStatus.STOPPED


class TestLibraryResilience:
    def test_scan_failure_preserves_known_good_state(self):
        audio = FakeAudioPort()
        scanner = _FakeScanner(files=[Path("/good/a.mp3")])
        library = LibraryService(scanner, QueueService(PlaybackService(audio)))
        library.scan("/good")
        assert library.state.current_directory == "/good"
        assert len(library.state.tracks) == 1
        library.search("test")
        assert library.state.query == "test"

        scanner.should_fail = True
        with pytest.raises(OSError):
            library.scan("/broken")
        assert library.state.current_directory == "/good"
        assert len(library.state.tracks) == 1
        assert library.state.query == "test"


class _FakeScanner:
    def __init__(self, files=None):
        self._files = files or []
        self.should_fail = False

    def scan(self, root):
        if self.should_fail:
            raise OSError("fake scan failure")
        return self._files


class FailingSettingsRepo(FakeSettingsRepo):
    def __init__(self):
        super().__init__()
        self._fail_save = False

    def set_fail_save(self, v: bool):
        self._fail_save = v

    def save(self, state):
        if self._fail_save:
            raise OSError("disk full")
        super().save(state)


class TestShutdownResilience:
    def test_cleanup_runs_when_save_fails(self):
        repo = FailingSettingsRepo()
        repo.save(SettingsState(volume=10, muted=False))
        repo.set_fail_save(True)
        settings = SettingsService(repo)
        settings.load()
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        playback.restore_volume(10, False)
        playback.set_volume(50)
        vol, muted = playback.snapshot_volume()
        settings.set_playback_preferences(vol, muted)
        with pytest.raises(OSError):
            try:
                settings.save()
            finally:
                audio.stop()
        assert audio.state == "stopped"

    def test_shutdown_idempotent_no_crash(self):
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        settings.load()
        playback.set_volume(50)
        vol, muted = playback.snapshot_volume()
        settings.set_playback_preferences(vol, muted)
        settings.save()
        audio.stop()
        audio.stop()  # idempotent
        settings.save()  # safe re-save
