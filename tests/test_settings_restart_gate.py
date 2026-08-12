"""M10.5 Restart / Persistence Gate — full lifecycle integration tests."""

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
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository
from tests.conftest import FakeAudioPort


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


def _build_session(db_path: Path, scanner: FakeScanner):
    """Wire a complete application session without QML/audio hardware."""
    repo = SQLiteSettingsRepository(db_path)
    settings = SettingsService(repo)
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    library = LibraryService(scanner, queue)
    prefs = LibraryPreferencesCoordinator(library, settings)
    return repo, settings, playback, queue, library, prefs


def _startup(settings, playback, prefs):
    s = settings.load()
    playback.restore_volume(s.volume, s.muted)
    prefs.start()


def _shutdown(playback, settings, prefs):
    prefs.stop()
    vol, muted = playback.snapshot_volume()
    settings.set_playback_preferences(vol, muted)
    settings.save()


class TestRestartGate:
    def test_full_restart_cycle(self, tmp_path):
        db = tmp_path / "michi-restart.db"

        # ── Prepare initial persisted state ─────────────────
        repo0 = SQLiteSettingsRepository(db)
        repo0.save(
            SettingsState(
                volume=20,
                muted=False,
                last_directory="/old/music",
                recent_files=["/music/a.flac", "/music/b.flac"],
            )
        )

        # ── Session 1 ──────────────────────────────────────
        scanner1 = FakeScanner(files=[Path("/new/music/a.mp3")])
        repo1, settings1, playback1, _q1, library1, prefs1 = _build_session(
            db, scanner1
        )
        _startup(settings1, playback1, prefs1)

        assert playback1.state.volume == 20
        assert playback1.state.muted is False
        assert library1.state.current_directory == "/old/music"
        assert scanner1.scan_calls == 0
        assert settings1.state.recent_files == ["/music/a.flac", "/music/b.flac"]

        # Runtime changes
        playback1.set_volume(73)
        playback1.set_muted(True)
        library1.scan("/new/music")
        assert library1.state.current_directory == "/new/music"
        assert settings1.state.last_directory == "/new/music"
        assert settings1.state.recent_files == ["/music/a.flac", "/music/b.flac"]

        _shutdown(playback1, settings1, prefs1)

        # ── Session 2 — fresh objects ───────────────────────
        scanner2 = FakeScanner()
        _repo2, settings2, playback2, _q2, library2, prefs2 = _build_session(
            db, scanner2
        )
        _startup(settings2, playback2, prefs2)

        assert settings2.state.volume == 73
        assert settings2.state.muted is True
        assert settings2.state.last_directory == "/new/music"
        assert settings2.state.recent_files == ["/music/a.flac", "/music/b.flac"]
        assert playback2.state.volume == 73
        assert playback2.state.muted is True
        assert library2.state.current_directory == "/new/music"
        assert scanner2.scan_calls == 0  # no auto-scan

        _shutdown(playback2, settings2, prefs2)

    def test_failed_scan_preserves_known_good_across_restart(self, tmp_path):
        db = tmp_path / "michi-fail.db"
        repo0 = SQLiteSettingsRepository(db)
        repo0.save(
            SettingsState(
                volume=30,
                muted=True,
                last_directory="/known-good",
                recent_files=["x.mp3"],
            )
        )

        scanner1 = FakeScanner(should_fail=True)
        repo1, settings1, playback1, _q1, library1, prefs1 = _build_session(
            db, scanner1
        )
        _startup(settings1, playback1, prefs1)
        assert library1.state.current_directory == "/known-good"

        with pytest.raises(OSError):
            library1.scan("/broken")
        assert settings1.state.last_directory == "/known-good"
        assert library1.state.current_directory == "/known-good"

        _shutdown(playback1, settings1, prefs1)

        # Session 2
        scanner2 = FakeScanner()
        _repo2, settings2, _p2, _q2, library2, prefs2 = _build_session(db, scanner2)
        _startup(settings2, _p2, prefs2)
        assert settings2.state.last_directory == "/known-good"
        assert library2.state.current_directory == "/known-good"
        assert scanner2.scan_calls == 0

    def test_empty_directory_restart_does_not_scan(self, tmp_path):
        db = tmp_path / "michi-empty.db"
        repo0 = SQLiteSettingsRepository(db)
        repo0.save(SettingsState(last_directory=""))

        scanner1 = FakeScanner()
        repo1, settings1, playback1, _q1, library1, prefs1 = _build_session(
            db, scanner1
        )
        _startup(settings1, playback1, prefs1)
        assert library1.state.current_directory == ""
        assert scanner1.scan_calls == 0

        _shutdown(playback1, settings1, prefs1)

        scanner2 = FakeScanner()
        _repo2, settings2, _p2, _q2, library2, prefs2 = _build_session(db, scanner2)
        _startup(settings2, _p2, prefs2)
        assert library2.state.current_directory == ""
        assert scanner2.scan_calls == 0
