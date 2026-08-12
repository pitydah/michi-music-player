"""Tests for SettingsService ownership and lifecycle."""

from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState
from tests.conftest import FakeSettingsRepo


class TestSettingsService:
    def test_defaults_on_new_repo(self):
        svc = SettingsService(FakeSettingsRepo())
        s = svc.load()
        assert s.volume == 80
        assert s.muted is False

    def test_loads_persisted_state(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(volume=42, muted=True, last_directory="/m"))
        svc = SettingsService(repo)
        s = svc.load()
        assert s.volume == 42
        assert s.muted is True
        assert s.last_directory == "/m"

    def test_set_last_directory(self):
        svc = SettingsService(FakeSettingsRepo())
        svc.set_last_directory("/music")
        assert svc.state.last_directory == "/music"

    def test_set_recent_files(self):
        svc = SettingsService(FakeSettingsRepo())
        svc.set_recent_files(["a.mp3", "b.mp3"])
        assert svc.state.recent_files == ["a.mp3", "b.mp3"]

    def test_save_persists(self):
        repo = FakeSettingsRepo()
        svc = SettingsService(repo)
        svc.set_playback_preferences(99, True)
        svc.save()
        s2 = repo.load()
        assert s2.volume == 99
        assert s2.muted is True

    def test_full_state_preserved_on_partial_update(self):
        repo = FakeSettingsRepo()
        repo.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="/m",
                recent_files=["x.mp3"],
            )
        )
        svc = SettingsService(repo)
        svc.load()
        svc.set_playback_preferences(70, True)
        svc.save()
        s = repo.load()
        assert s.volume == 70
        assert s.muted is True
        assert s.last_directory == "/m"
        assert s.recent_files == ["x.mp3"]
