"""Tests for LibraryPreferencesCoordinator — M10.2 last_directory integration."""

from pathlib import Path

import pytest

from michi.application.library_preferences_coordinator import (
    LibraryPreferencesCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class FakeScanner:
    def __init__(self, files=None, should_fail=False):
        self._files = files or []
        self.should_fail = should_fail
        self.scan_calls: int = 0

    def scan(self, root):
        self.scan_calls += 1
        if self.should_fail:
            raise OSError("fake scan failure")
        return self._files


class CountingSettingsRepo(FakeSettingsRepo):
    """Fake that counts load() calls."""

    def __init__(self):
        super().__init__()
        self.load_count = 0

    def load(self):
        self.load_count += 1
        return super().load()


# ── Core coordinator tests ──────────────────────────────────────


class TestLibraryPreferencesCoordinator:
    def test_restore_stored_directory_no_scan(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/music"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner()
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        assert library.state.current_directory == "/music"
        assert scanner.scan_calls == 0

    def test_empty_preference_no_restore(self):
        settings = SettingsService(FakeSettingsRepo())
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        assert library.state.current_directory == ""
        assert len(library.state.tracks) == 0

    def test_successful_scan_updates_settings(self):
        settings = SettingsService(FakeSettingsRepo())
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        library.scan("/music")
        assert settings.state.last_directory == "/music"

    def test_failed_scan_propagates_and_preserves(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/old"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(should_fail=True)
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        with pytest.raises(OSError):
            library.scan("/broken")
        assert settings.state.last_directory == "/old"

    def test_search_does_not_alter_directory(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/music"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        library.scan("/music")
        library.search("depeche")
        assert settings.state.last_directory == "/music"

    # ── Behavioral: no private implementation assertions ─────────

    def test_start_idempotent_does_not_double_sync(self):
        """Second start() should not cause double set_last_directory."""
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/old"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        c = LibraryPreferencesCoordinator(library, settings)
        c.start()
        c.start()  # idempotent
        library.scan("/music")
        assert settings.state.last_directory == "/music"

    def test_stop_prevents_sync(self):
        """After stop(), a scan must not update settings."""
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/old"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        c = LibraryPreferencesCoordinator(library, settings)
        c.start()
        c.stop()
        c.stop()  # idempotent — no error
        library.scan("/music")
        assert settings.state.last_directory == "/old"

    def test_single_settings_load(self):
        """SettingsRepository.load() must be called exactly once."""
        repo = CountingSettingsRepo()
        repo.save(SettingsState(last_directory="/music", volume=30))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner()
        library = LibraryService(scanner, QueueService(svc))
        # Simulate bootstrap: load once, use for both restore and coordinator
        s = settings.load()
        svc.restore_volume(s.volume, s.muted)
        c = LibraryPreferencesCoordinator(library, settings)
        c.start()
        assert repo.load_count == 1


# ── Bridge test ──────────────────────────────────────────────────


class TestLibraryBridgeRestore:
    def test_bridge_sees_restored_directory_no_scan(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/music"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner()
        library = LibraryService(scanner, QueueService(svc))
        c = LibraryPreferencesCoordinator(library, settings)
        c.start()
        bridge = LibraryBridge(library)
        assert bridge.property("currentDir") == "/music"
        assert scanner.scan_calls == 0
        bridge.dispose()


# ── Combined lifecycle ───────────────────────────────────────────


class TestCombinedLifecycle:
    def test_playback_and_library_persist_together(self):
        repo = FakeSettingsRepo()
        repo.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="",
                recent_files=["a.mp3", "b.mp3"],
            )
        )
        settings = SettingsService(repo)
        s = settings.load()

        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        playback.restore_volume(s.volume, s.muted)

        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(playback))
        c = LibraryPreferencesCoordinator(library, settings)
        c.start()

        # Library runtime
        library.scan("/music")
        assert settings.state.last_directory == "/music"

        # Playback runtime
        playback.set_volume(73)
        playback.set_muted(True)

        # Shutdown
        c.stop()
        vol, muted = playback.snapshot_volume()
        settings.set_playback_preferences(vol, muted)
        settings.save()

        # Reload
        settings2 = SettingsService(repo)
        s2 = settings2.load()
        assert s2.volume == 73
        assert s2.muted is True
        assert s2.last_directory == "/music"
        assert s2.recent_files == ["a.mp3", "b.mp3"]


# ── Restore hint unit ────────────────────────────────────────────


class TestRestoreDirectoryHint:
    def test_idempotent(self):
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        calls = []

        def cb():
            calls.append(1)

        library.subscribe_changed(cb)
        library.restore_directory_hint("/music")
        assert len(calls) == 1
        library.restore_directory_hint("/music")
        assert len(calls) == 1

    def test_empty_string_no_op(self):
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        library.restore_directory_hint("")
        assert library.state.current_directory == ""
