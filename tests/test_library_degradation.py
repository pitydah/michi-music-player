"""TD-013 filesystem degradation — RED-phase tests for the degradation contract.

This file is the Phase-1 (RED) evidence for TD-013. On the current baseline
the module-level imports of the new domain/port symbols fail at collection
(ImportError) — that IS the expected red evidence. The tests encode the
target contract and must pass once the production changes land.

Coverage:
- FilesystemLibraryScanner error taxonomy (scan + validate_file)
- LibraryService scan failure atomicity (spec §13/§39)
- Same-directory rescan stale-entry reconciliation (spec §40)
- Activation-time validation (spec §18-21, §41)
- LibraryBridge diagnostic projection (spec Z)
- QML surface guard (spec AA)
"""

import errno
import os
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_preferences_coordinator import (
    LibraryPreferencesCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.queue_service import QueueService
from michi.application.settings_service import SettingsService
from michi.domain.library import (
    LibraryDiagnostic,
    LibraryDiagnosticCode,
    LibraryState,
    TrackRef,
)
from michi.domain.settings import SettingsState
from michi.infrastructure.filesystem_scanner import FilesystemLibraryScanner
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort, FakeSettingsRepo

QML_DIR = Path("src/michi/presentation/qml").resolve()


class FakeScanner:
    """Runtime-behavioral fake: provides scan() + validate_file().

    scan() returns the configured files or raises scan_error (typically a
    LibraryFilesystemError). validate_file() raises the error registered for
    a path, else returns None. Both calls are recorded.
    """

    def __init__(self, files=None, validate_errors=None, scan_error=None):
        self.files = list(files) if files else []
        self.validate_errors = validate_errors or {}
        self.scan_error = scan_error
        self.scan_calls = []
        self.validated = []

    def scan(self, root):
        self.scan_calls.append(root)
        if self.scan_error is not None:
            raise self.scan_error
        return list(self.files)

    def validate_file(self, path):
        self.validated.append(path)
        error = self.validate_errors.get(path)
        if error is not None:
            raise error
        return None


def _make_library(scanner):
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    library = LibraryService(scanner)
    return library, queue, session, playback, audio


def _coordinator_for(library, session):
    from michi.application.library_playback_coordinator import (
        LibraryPlaybackCoordinator,
    )

    return LibraryPlaybackCoordinator(library, session)


def _patch_os_stat(monkeypatch, target, error):
    """Make os.stat raise `error` for `target` and anything below it."""

    real_stat = os.stat
    target_s = os.fspath(target)

    def raiser(path, *, follow_symlinks=True):
        p = os.fspath(path)
        if p == target_s or p.startswith(target_s + os.sep):
            raise error
        return real_stat(path, follow_symlinks=follow_symlinks)

    monkeypatch.setattr(os, "stat", raiser)


class TestScanRootDistinction:
    def test_missing_root_raises_directory_missing(self, tmp_path):
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.scan(tmp_path / "absent")
        assert excinfo.value.code is LibraryDiagnosticCode.DIRECTORY_MISSING

    def test_valid_empty_root_returns_empty_list(self, tmp_path):
        scanner = FilesystemLibraryScanner()
        assert scanner.scan(tmp_path) == []

    def test_scan_access_failure_classified(self, tmp_path, monkeypatch):
        _patch_os_stat(monkeypatch, tmp_path, PermissionError(errno.EACCES, "denied"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.scan(tmp_path)
        assert excinfo.value.code is LibraryDiagnosticCode.ACCESS_FAILURE

    def test_scan_io_failure_classified(self, tmp_path, monkeypatch):
        _patch_os_stat(monkeypatch, tmp_path, OSError(errno.EIO, "i/o error"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.scan(tmp_path)
        assert excinfo.value.code is LibraryDiagnosticCode.IO_FAILURE

    def test_scan_unknown_failure_classified(self, tmp_path, monkeypatch):
        _patch_os_stat(monkeypatch, tmp_path, OSError(12345, "weird"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.scan(tmp_path)
        assert excinfo.value.code is LibraryDiagnosticCode.UNKNOWN_FAILURE

    def test_scan_traversal_error_is_typed(self, tmp_path, monkeypatch):
        (tmp_path / "a.mp3").write_text("")

        def raising_rglob(self, pattern):
            raise PermissionError(errno.EACCES, "denied")

        monkeypatch.setattr(
            "michi.infrastructure.filesystem_scanner.Path.rglob", raising_rglob
        )
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.scan(tmp_path)
        assert excinfo.value.code is LibraryDiagnosticCode.ACCESS_FAILURE


class TestValidateFile:
    def test_validate_existing_regular_file_returns_none(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.write_text("")
        scanner = FilesystemLibraryScanner()
        assert scanner.validate_file(f) is None

    def test_validate_missing_file_raises_track_missing(self, tmp_path):
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.validate_file(tmp_path / "nope.mp3")
        assert excinfo.value.code is LibraryDiagnosticCode.TRACK_MISSING

    def test_validate_directory_raises_track_missing(self, tmp_path):
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.validate_file(tmp_path)
        assert excinfo.value.code is LibraryDiagnosticCode.TRACK_MISSING

    def test_validate_access_failure_classified(self, tmp_path, monkeypatch):
        f = tmp_path / "song.mp3"
        f.write_text("")
        _patch_os_stat(monkeypatch, f, PermissionError(errno.EACCES, "denied"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.validate_file(f)
        assert excinfo.value.code is LibraryDiagnosticCode.ACCESS_FAILURE

    def test_validate_io_failure_classified(self, tmp_path, monkeypatch):
        f = tmp_path / "song.mp3"
        f.write_text("")
        _patch_os_stat(monkeypatch, f, OSError(errno.EIO, "i/o error"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.validate_file(f)
        assert excinfo.value.code is LibraryDiagnosticCode.IO_FAILURE

    def test_validate_unknown_failure_classified(self, tmp_path, monkeypatch):
        f = tmp_path / "song.mp3"
        f.write_text("")
        _patch_os_stat(monkeypatch, f, OSError(12345, "weird"))
        scanner = FilesystemLibraryScanner()
        with pytest.raises(LibraryFilesystemError) as excinfo:
            scanner.validate_file(f)
        assert excinfo.value.code is LibraryDiagnosticCode.UNKNOWN_FAILURE


class TestScanFailureAtomicity:
    def test_failed_scan_preserves_tracks_query_and_directory(self):
        scanner = FakeScanner(files=[Path("/a/a.mp3")])
        library, *_ = _make_library(scanner)
        library.scan("/a")
        library.search("mix")
        assert len(library.state.tracks) == 1
        assert isinstance(library.state, LibraryState)
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=Path("/b"), detail="gone"
        )
        library.scan("/b")  # contract: must NOT raise
        assert library.state.tracks == [TrackRef(file_path=Path("/a/a.mp3"))]
        assert library.state.query == "mix"
        assert library.state.current_directory == "/a"
        assert isinstance(library.state.diagnostic, LibraryDiagnostic)
        assert library.state.diagnostic.code is LibraryDiagnosticCode.DIRECTORY_MISSING

    def test_failed_scan_does_not_persist_last_directory(self):
        repo = FakeSettingsRepo()
        repo.save(SettingsState(last_directory="/a"))
        settings = SettingsService(repo)
        scanner = FakeScanner(files=[Path("/a/a.mp3")])
        library, *_ = _make_library(scanner)
        coordinator = LibraryPreferencesCoordinator(library, settings)
        coordinator.start()
        library.scan("/a")
        assert settings.state.last_directory == "/a"
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=Path("/b"), detail="gone"
        )
        library.scan("/b")  # must NOT raise; on baseline it propagates (RED)
        assert settings.state.last_directory == "/a"

    def test_failed_scan_notifies_once(self):
        scanner = FakeScanner()
        library, *_ = _make_library(scanner)
        calls = []
        library.subscribe_changed(lambda: calls.append(1))
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=Path("/b"), detail="gone"
        )
        library.scan("/b")
        assert len(calls) == 1


class TestSameDirectoryRescan:
    def test_same_dir_rescan_removes_stale_entries(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.flac"
        b = music / "b.flac"
        a.write_text("")
        b.write_text("")
        scanner = FilesystemLibraryScanner()
        library, *_ = _make_library(scanner)
        library.scan(str(music))
        assert len(library.state.tracks) == 2
        calls = []
        library.subscribe_changed(lambda: calls.append(1))
        b.unlink()
        library.scan(str(music))
        assert len(calls) == 1  # single notify for the rescan transition
        assert [t.file_path for t in library.state.tracks] == [a]
        assert library.state.diagnostic is not None
        assert (
            library.state.diagnostic.code is LibraryDiagnosticCode.STALE_ENTRIES_REMOVED
        )
        assert library.state.diagnostic.affected_count == 1
        assert (
            library.state.diagnostic.message
            == "Removed 1 unavailable file(s) from the library."
        )

    def test_different_dir_scan_clears_diagnostic(self):
        scanner = FakeScanner(files=[Path("/a/one.mp3")])
        library, *_ = _make_library(scanner)
        library.scan("/a")
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.DIRECTORY_MISSING, path=Path("/b"), detail="gone"
        )
        library.scan("/b")  # failed scan sets the diagnostic, dir preserved
        assert library.state.diagnostic is not None
        scanner.scan_error = None
        scanner.files = [Path("/b/two.mp3")]
        library.scan("/b")  # success in a different directory clears it
        assert library.state.diagnostic is None
        assert [t.file_path for t in library.state.tracks] == [Path("/b/two.mp3")]
        assert library.state.current_directory == "/b"

    def test_renamed_file_reconciled_as_removed(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.flac"
        a.write_text("")
        scanner = FilesystemLibraryScanner()
        library, *_ = _make_library(scanner)
        library.scan(str(music))
        c = music / "c.flac"
        a.rename(c)
        library.scan(str(music))
        paths = {t.file_path for t in library.state.tracks}
        assert c in paths
        assert a not in paths
        assert library.state.diagnostic is not None
        assert (
            library.state.diagnostic.code is LibraryDiagnosticCode.STALE_ENTRIES_REMOVED
        )
        assert library.state.diagnostic.affected_count == 1

    def test_same_dir_rescan_no_stale_no_diagnostic(self, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        (music / "a.flac").write_text("")
        scanner = FilesystemLibraryScanner()
        library, *_ = _make_library(scanner)
        library.scan(str(music))
        library.scan(str(music))
        assert library.state.diagnostic is None


class TestActivationValidation:
    def test_activation_missing_removes_exact_trackref(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3"), Path("/m/b.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        tracks_before = list(library.state.tracks)
        missing = Path("/m/a.mp3")
        scanner.validate_errors = {
            missing: LibraryFilesystemError(
                LibraryDiagnosticCode.TRACK_MISSING, missing
            )
        }
        calls = []
        library.subscribe_changed(lambda: calls.append(1))
        coordinator.play_visible_track(0)
        assert len(calls) == 1  # single notify for the activation transition
        assert len(library.state.tracks) == 1
        assert library.state.tracks[0] is tracks_before[1]  # exact ref identity
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.TRACK_MISSING
        assert library.state.diagnostic.path == missing
        assert queue.state.count == 0
        assert audio.state == "stopped"
        assert audio.loaded is None

    def test_missing_activation_no_queue_mutation(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3"), Path("/m/b.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        missing = Path("/m/a.mp3")
        scanner.validate_errors = {
            missing: LibraryFilesystemError(
                LibraryDiagnosticCode.TRACK_MISSING, missing
            )
        }
        coordinator.play_visible_track(0)
        assert queue.state.tracks == []
        assert session.state.current_index == -1  # pristine queue, never touched

    def test_missing_activation_no_playback(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        missing = Path("/m/a.mp3")
        scanner.validate_errors = {
            missing: LibraryFilesystemError(
                LibraryDiagnosticCode.TRACK_MISSING, missing
            )
        }
        coordinator.play_visible_track(0)
        assert audio.state == "stopped"
        assert audio.loaded is None

    def test_filtered_visible_index_removes_correct_base_track(self, tmp_path):
        base = tmp_path / "m"
        base.mkdir()
        alpha = base / "alpha.mp3"
        beta = base / "beta.mp3"
        gamma = base / "gamma.mp3"
        for f in (alpha, beta, gamma):
            f.write_text("")
        scanner = FakeScanner(files=[alpha, beta, gamma])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan(str(base))
        library.search("beta")
        scanner.validate_errors = {
            beta: LibraryFilesystemError(LibraryDiagnosticCode.TRACK_MISSING, beta)
        }
        coordinator.play_visible_track(0)  # visible index 0 == beta under the filter
        assert [t.file_path for t in library.state.tracks] == [alpha, gamma]
        assert queue.state.count == 0

    def test_activation_access_failure_preserves_ref_and_queue(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        before = list(library.state.tracks)
        p = Path("/m/a.mp3")
        scanner.validate_errors = {
            p: LibraryFilesystemError(LibraryDiagnosticCode.ACCESS_FAILURE, p, "denied")
        }
        coordinator.play_visible_track(0)
        assert library.state.tracks == before
        assert library.state.tracks[0] is before[0]
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.ACCESS_FAILURE
        assert queue.state.count == 0
        assert audio.loaded is None

    def test_activation_io_failure_preserves(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        p = Path("/m/a.mp3")
        scanner.validate_errors = {
            p: LibraryFilesystemError(LibraryDiagnosticCode.IO_FAILURE, p, "i/o error")
        }
        coordinator.play_visible_track(0)
        assert len(library.state.tracks) == 1
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.IO_FAILURE
        assert queue.state.count == 0
        assert audio.loaded is None

    def test_activation_unknown_failure_preserves(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        p = Path("/m/a.mp3")
        scanner.validate_errors = {
            p: LibraryFilesystemError(LibraryDiagnosticCode.UNKNOWN_FAILURE, p, "weird")
        }
        coordinator.play_visible_track(0)
        assert len(library.state.tracks) == 1
        assert library.state.diagnostic is not None
        assert library.state.diagnostic.code is LibraryDiagnosticCode.UNKNOWN_FAILURE
        assert queue.state.count == 0
        assert audio.loaded is None

    def test_invalid_visible_index_no_validation_no_notify(self):
        scanner = FakeScanner(files=[Path("/m/a.mp3"), Path("/m/b.mp3")])
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan("/m")
        calls = []
        library.subscribe_changed(lambda: calls.append(1))
        scanner.validate_errors = {
            Path("/m/a.mp3"): LibraryFilesystemError(
                LibraryDiagnosticCode.TRACK_MISSING, Path("/m/a.mp3")
            )
        }
        coordinator.play_visible_track(5)
        assert scanner.validated == []
        assert len(calls) == 0
        assert library.state.diagnostic is None

    def test_valid_activation_preserves_existing_queue_behavior(self, tmp_path):
        f = tmp_path / "song.mp3"
        f.write_text("")
        scanner = FilesystemLibraryScanner()
        library, queue, session, playback, audio = _make_library(scanner)
        coordinator = _coordinator_for(library, session)
        library.scan(str(tmp_path))
        coordinator.play_visible_track(0)
        audio.trigger_media_accepted(f)
        # M4-R1: generic track click → SINGLE; Queue NEVER receives it.
        assert queue.state.count == 0
        assert session.state.context_type.name == "SINGLE"
        assert session.state.current_index == 0
        assert audio.loaded == f


class TestBridgeDiagnosticProjection:
    def test_bridge_diagnostic_after_failed_scan(self):
        scanner = FakeScanner(
            scan_error=LibraryFilesystemError(
                LibraryDiagnosticCode.DIRECTORY_MISSING, path=Path("/b"), detail="gone"
            )
        )
        library, *_ = _make_library(scanner)
        bridge = LibraryBridge(library)
        library.scan("/b")
        assert bridge.property("hasDiagnostic") is True
        assert bridge.property("diagnosticCode") == "directory_missing"
        assert (
            bridge.property("diagnosticMessage")
            == "Music directory is no longer available: /b"
        )
        scanner.scan_error = None
        scanner.files = [Path("/c/ok.mp3")]
        library.scan("/c")
        assert bridge.property("hasDiagnostic") is False
        assert bridge.property("diagnosticCode") == ""
        assert bridge.property("diagnosticMessage") == ""
        bridge.dispose()

    def test_bridge_no_diagnostic_initial(self):
        scanner = FakeScanner()
        library, *_ = _make_library(scanner)
        bridge = LibraryBridge(library)
        assert bridge.property("hasDiagnostic") is False
        assert bridge.property("diagnosticCode") == ""
        assert bridge.property("diagnosticMessage") == ""
        bridge.dispose()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlDiagnosticSurface:
    def test_library_view_loads_with_diagnostic_context(self, qapp):
        scanner = FakeScanner()
        library, *_ = _make_library(scanner)
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        obj.deleteLater()
        bridge.dispose()
