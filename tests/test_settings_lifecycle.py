"""Lifecycle regression tests — protect full-state preservation."""

from michi.application.playback_service import PlaybackService
from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class TestSettingsLifecycle:
    def test_full_state_preserved_after_shutdown(self):
        repo = FakeSettingsRepo()
        repo.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="/music",
                recent_files=["a.mp3", "b.mp3"],
            )
        )
        settings = SettingsService(repo)
        s = settings.load()
        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        playback.restore_volume(s.volume, s.muted)
        playback.set_volume(73)
        playback.set_muted(True)
        vol, muted = playback.snapshot_volume()
        settings.set_playback_preferences(vol, muted)
        settings.save()
        settings2 = SettingsService(repo)
        s2 = settings2.load()
        assert s2.volume == 73
        assert s2.muted is True
        assert s2.last_directory == "/music"
        assert s2.recent_files == ["a.mp3", "b.mp3"]

    def test_playback_preferences_via_public_api(self):
        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        settings.set_playback_preferences(99, True)
        settings.save()
        s = repo.load()
        assert s.volume == 99
        assert s.muted is True

    def test_volume_clamping(self):
        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        settings.set_playback_preferences(150, False)
        assert settings.state.volume == 100
        settings.set_playback_preferences(-10, False)
        assert settings.state.volume == 0
