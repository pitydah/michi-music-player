"""Tests for LibraryPreferencesCoordinator — M10.2 last_directory integration."""

import contextlib

from michi.application.library_preferences_coordinator import (
    LibraryPreferencesCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.settings import SettingsState
from tests.conftest import FakeAudioPort, FakeSettingsRepo


class FakeScanner:
    """Minimal scanner fake for tests."""

    def __init__(self, files=None, should_fail=False):
        self._files = files or []
        self.should_fail = should_fail
        self.scan_calls: int = 0

    def scan(self, root):
        self.scan_calls += 1
        if self.should_fail:
            raise OSError("fake scan failure")
        return self._files


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
        from pathlib import Path

        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        library.scan("/music")
        assert settings.state.last_directory == "/music"

    def test_failed_scan_does_not_overwrite(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/old"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        scanner = FakeScanner(should_fail=True)
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        with contextlib.suppress(OSError):
            library.scan("/broken")
        assert settings.state.last_directory == "/old"

    def test_search_does_not_alter_directory(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/music"))
        settings = SettingsService(repo)
        svc = PlaybackService(FakeAudioPort())
        from pathlib import Path

        scanner = FakeScanner(files=[Path("/music/a.mp3")])
        library = LibraryService(scanner, QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        library.scan("/music")
        library.search("depeche")
        assert settings.state.last_directory == "/music"

    def test_coordinator_start_idempotent(self):
        settings = SettingsService(FakeSettingsRepo())
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        coordinator.start()
        assert coordinator._started

    def test_coordinator_stop_unsubscribes(self):
        settings = SettingsService(FakeSettingsRepo())
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        sub_count = len(library._subscribers)
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        assert len(library._subscribers) == sub_count + 1
        coordinator.stop()
        assert len(library._subscribers) == sub_count


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
        assert len(calls) == 1  # no duplicate notification

    def test_empty_string_no_op(self):
        svc = PlaybackService(FakeAudioPort())
        library = LibraryService(FakeScanner(), QueueService(svc))
        library.restore_directory_hint("")
        assert library.state.current_directory == ""
