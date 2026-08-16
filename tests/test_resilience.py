"""M11.1 resilience — real ApplicationContainer shutdown + failure atomicity."""

from pathlib import Path

import pytest

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.bootstrap import ApplicationContainer
from michi.domain.library import LibraryDiagnosticCode
from michi.domain.playback import PlaybackStatus
from michi.domain.settings import SettingsState
from tests.conftest import FakeAudioPort, FakeSettingsRepo

# ── Spies for ApplicationContainer shutdown testing ────────────


class StopSpy:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def stop(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("stop failure")


class DisposeSpy:
    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    def dispose(self):
        self.calls += 1
        if self.fail:
            raise RuntimeError("dispose failure")


class DeleteLaterSpy:
    def __init__(self):
        self.calls = 0

    def deleteLater(self):  # noqa: N802 — Qt API name
        self.calls += 1


# ── Playback failure atomicity ──────────────────────────────────


class FailingAudio(FakeAudioPort):
    def __init__(self):
        super().__init__()
        self.fail_volume = False
        self.fail_muted = False
        self.fail_play = False

    def set_volume(self, v):
        if self.fail_volume:
            raise RuntimeError("volume failure")
        super().set_volume(v)

    def set_muted(self, m):
        if self.fail_muted:
            raise RuntimeError("mute failure")
        super().set_muted(m)

    def play(self):
        if self.fail_play:
            raise RuntimeError("play failure")
        super().play()


class TestPlaybackResilience:
    def test_play_failure_preserves_stopped(self):
        audio = FailingAudio()
        audio.fail_play = True
        svc = PlaybackService(audio)
        with pytest.raises(RuntimeError):
            svc.play()
        assert svc.state.status == PlaybackStatus.STOPPED

    def test_volume_failure_preserves_previous(self):
        audio = FailingAudio()
        svc = PlaybackService(audio)
        audio.fail_volume = True
        with pytest.raises(RuntimeError):
            svc.set_volume(90)
        assert svc.state.volume == 100  # default preserved

    def test_mute_failure_preserves_previous(self):
        audio = FailingAudio()
        svc = PlaybackService(audio)
        audio.fail_muted = True
        with pytest.raises(RuntimeError):
            svc.set_muted(True)
        assert svc.state.muted is False

    def test_restore_volume_partial_failure(self):
        audio = FailingAudio()
        svc = PlaybackService(audio)
        svc.set_volume(40)
        svc.set_muted(False)
        audio.fail_muted = True
        with pytest.raises(RuntimeError):
            svc.restore_volume(80, True)
        # Both state fields preserved — commit only after both backends succeed
        assert svc.state.volume == 40
        assert svc.state.muted is False

    def test_stop_is_idempotent(self):
        audio = FakeAudioPort()
        svc = PlaybackService(audio)
        svc.load_and_play(Path("/tmp/a.mp3"))
        audio.trigger_media_accepted(Path("/tmp/a.mp3"))
        svc.stop()
        svc.stop()
        assert svc.state.status == PlaybackStatus.STOPPED


# ── Library failure atomicity ──────────────────────────────────


class FlakyScanner:
    def __init__(self, files=None):
        self._files = files or []
        self.should_fail = False

    def scan(self, root):
        if self.should_fail:
            raise LibraryFilesystemError(
                LibraryDiagnosticCode.DIRECTORY_MISSING, Path("/broken")
            )
        return self._files

    def validate_file(self, path):
        return None


class TestLibraryResilience:
    def test_scan_failure_preserves_complete_known_good_library_state(self):
        audio = FakeAudioPort()
        scanner = FlakyScanner(files=[Path("/good/a.flac"), Path("/good/b.mp3")])
        library = LibraryService(scanner, QueueService(PlaybackService(audio)))

        library.scan("/good")
        assert library.state.current_directory == "/good"
        assert len(library.state.tracks) == 2

        library.search("test")
        assert library.state.query == "test"

        previous_directory = library.state.current_directory
        previous_tracks = list(library.state.tracks)
        previous_query = library.state.query

        scanner.should_fail = True
        library.scan("/broken")  # must NOT raise

        assert library.state.current_directory == previous_directory
        assert library.state.tracks == previous_tracks
        assert library.state.query == previous_query
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING


# ── ApplicationContainer real shutdown ──────────────────────────


class TestApplicationContainerShutdown:
    def test_cleanup_runs_when_settings_save_fails(self):
        container = ApplicationContainer()

        class SaveFailingRepo(FakeSettingsRepo):
            def __init__(self):
                super().__init__()
                self.fail_next = False

            def save(self, state):
                if self.fail_next:
                    raise OSError("disk full")
                super().save(state)

        repo = SaveFailingRepo()
        repo.save(SettingsState(volume=10, muted=False))
        repo.fail_next = True
        settings = SettingsService(repo)
        playback = PlaybackService(FakeAudioPort())

        coord = StopSpy()
        prefs = StopSpy()
        backend = StopSpy()
        engine = DeleteLaterSpy()
        pb = DisposeSpy()
        qb = DisposeSpy()
        lb = DisposeSpy()
        nb = DisposeSpy()

        container._coordinator = coord
        container._library_prefs = prefs
        container._playback = playback
        container._settings = settings
        container._pb = pb
        container._qb = qb
        container._lb = lb
        container._nb = nb
        container._backend = backend
        container._engine = engine

        with pytest.raises(OSError, match="disk full"):
            container.shutdown()

        assert coord.calls >= 1
        assert prefs.calls >= 1
        assert pb.calls >= 1
        assert qb.calls >= 1
        assert lb.calls >= 1
        assert nb.calls >= 1
        assert backend.calls >= 1
        assert engine.calls >= 1
        assert container._pb is None
        assert container._settings is None
        assert container._backend is None

    def test_shutdown_continues_after_dispose_failure(self):
        container = ApplicationContainer()
        coord = StopSpy()
        prefs = StopSpy()
        backend = StopSpy()
        engine = DeleteLaterSpy()

        pb = DisposeSpy(fail=True)
        qb = DisposeSpy()
        lb = DisposeSpy()
        nb = DisposeSpy()

        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        playback = PlaybackService(FakeAudioPort())

        container._coordinator = coord
        container._library_prefs = prefs
        container._playback = playback
        container._settings = settings
        container._pb = pb
        container._qb = qb
        container._lb = lb
        container._nb = nb
        container._backend = backend
        container._engine = engine

        with pytest.raises(RuntimeError, match="dispose failure"):
            container.shutdown()

        assert qb.calls >= 1
        assert lb.calls >= 1
        assert nb.calls >= 1
        assert backend.calls >= 1
        assert engine.calls >= 1

    def test_shutdown_idempotent_no_crash(self):
        container = ApplicationContainer()
        coord = StopSpy()
        prefs = StopSpy()
        backend = StopSpy()
        engine = DeleteLaterSpy()
        pb = DisposeSpy()
        qb = DisposeSpy()
        lb = DisposeSpy()
        nb = DisposeSpy()

        repo = FakeSettingsRepo()
        settings = SettingsService(repo)
        playback = PlaybackService(FakeAudioPort())

        container._coordinator = coord
        container._library_prefs = prefs
        container._playback = playback
        container._settings = settings
        container._pb = pb
        container._qb = qb
        container._lb = lb
        container._nb = nb
        container._backend = backend
        container._engine = engine

        container.shutdown()
        container.shutdown()

        assert coord.calls == 1
        assert pb.calls == 1
        assert backend.calls == 1

    def test_settings_bridge_reference_cleared_after_shutdown(self):
        container = ApplicationContainer()
        container._coordinator = StopSpy()
        container._library_prefs = StopSpy()
        container._playback = PlaybackService(FakeAudioPort())
        container._settings = SettingsService(FakeSettingsRepo())
        container._pb = DisposeSpy()
        container._qb = DisposeSpy()
        container._lb = DisposeSpy()
        container._nb = DisposeSpy()
        container._sb = object()
        container._backend = StopSpy()
        container._engine = DeleteLaterSpy()
        container.shutdown()
        assert container._sb is None

    def test_shutdown_preserves_first_error_when_later_cleanup_also_fails(self):
        container = ApplicationContainer()

        class SaveFailingRepo(FakeSettingsRepo):
            def __init__(self):
                super().__init__()
                self.fail_next = False

            def save(self, state):
                if self.fail_next:
                    raise OSError("disk full")
                super().save(state)

        repo = SaveFailingRepo()
        repo.save(SettingsState(volume=10, muted=False))
        repo.fail_next = True
        settings = SettingsService(repo)

        coord = StopSpy()
        prefs = StopSpy()
        backend = StopSpy()
        engine = DeleteLaterSpy()
        pb = DisposeSpy(fail=True)  # second failure
        qb = DisposeSpy()
        lb = DisposeSpy()
        nb = DisposeSpy()

        container._coordinator = coord
        container._library_prefs = prefs
        container._playback = PlaybackService(FakeAudioPort())
        container._settings = settings
        container._pb = pb
        container._qb = qb
        container._lb = lb
        container._nb = nb
        container._backend = backend
        container._engine = engine

        with pytest.raises(OSError, match="disk full"):
            container.shutdown()

        # First error (OSError) wins over later RuntimeError
        assert qb.calls == 1
        assert lb.calls == 1
        assert nb.calls == 1
        assert backend.calls == 1
        assert engine.calls == 1
        assert container._pb is None
        assert container._backend is None
