"""Contract tests for the productive HomeBridge dashboard state."""
from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from ui_qml_bridge.home_bridge import HomeBridge


class FakeLibraryBridge:
    songCount = 12
    albumCount = 3
    artistCount = 4


class EmptyLibraryBridge:
    songCount = 0
    albumCount = 0
    artistCount = 0


class FakeSources:
    def __init__(self, values=None, error: Exception | None = None):
        self.values = values or []
        self.error = error

    def list(self):
        if self.error:
            raise self.error
        return list(self.values)


class FakeJobs(QObject):
    jobsChanged = Signal()

    def __init__(self, active=0):
        super().__init__()
        self.activeCount = active


class FakeSnapshot:
    current_path = "/music/Artist/Song.flac"


class FakeHybrid:
    def get_snapshot(self):
        return FakeSnapshot()


class FakePlayer(QObject):
    track_changed = Signal(str, str)
    state_changed = Signal(str)

    def __init__(self):
        super().__init__()
        self._current_title = "Song"
        self._current_artist = "Artist"
        self._hybrid = FakeHybrid()

    def get_active_backend_id(self):
        return "gstreamer"

    def get_output_device_id(self):
        return "auto"


def test_refresh_loads_all_dashboard_sections():
    bridge = HomeBridge(
        library_bridge=FakeLibraryBridge(),
        library_sources_service=FakeSources(["/music"]),
        job_bridge=FakeJobs(active=2),
        player_service=FakePlayer(),
    )

    result = bridge.refresh()

    assert result["ok"] is True
    assert bridge.ready is True
    assert bridge.loading is False
    assert bridge.hasLibrary is True
    assert bridge.libraryTracks == 12
    assert bridge.libraryAlbums == 3
    assert bridge.libraryArtists == 4
    assert bridge.sourcesCount == 1
    assert bridge.activeJobs == 2
    assert bridge.hasPlayback is True
    assert bridge.currentTrackTitle == "Song"
    assert bridge.currentArtist == "Artist"
    assert bridge.backend == "gstreamer"
    assert bridge.output == "auto"


def test_empty_library_is_exposed_without_fake_success_data():
    bridge = HomeBridge(
        library_bridge=EmptyLibraryBridge(),
        library_sources_service=FakeSources([]),
    )

    result = bridge.refresh()

    assert result["ok"] is True
    assert bridge.ready is True
    assert bridge.hasLibrary is False
    assert bridge.sourcesCount == 0
    assert bridge.errorMessage == ""


def test_refresh_returns_structured_partial_error():
    bridge = HomeBridge(
        library_bridge=FakeLibraryBridge(),
        library_sources_service=FakeSources(error=RuntimeError("source unavailable")),
    )

    result = bridge.refresh()

    assert result["ok"] is False
    assert bridge.ready is True
    assert bridge.hasLibrary is True
    assert "fuentes" in bridge.errorMessage
    assert "source unavailable" in bridge.errorMessage
    assert result["errors"]


def test_playback_signal_accepts_emitted_arguments():
    player = FakePlayer()
    bridge = HomeBridge(player_service=player)

    player.track_changed.emit("New song", "New artist")
    player.state_changed.emit("playing")

    assert bridge.hasPlayback is True
    assert bridge.currentTrackTitle == "Song"
    assert bridge.currentArtist == "Artist"
    assert bridge.backend == "gstreamer"


def test_job_signal_refreshes_active_count():
    jobs = FakeJobs(active=1)
    bridge = HomeBridge(job_bridge=jobs)
    bridge.refresh()
    assert bridge.activeJobs == 1

    jobs.activeCount = 4
    jobs.jobsChanged.emit()

    assert bridge.activeJobs == 4


def test_home_score_reports_readiness_and_error_state():
    bridge = HomeBridge(
        db=object(),
        player_service=FakePlayer(),
        library_bridge=FakeLibraryBridge(),
        library_sources_service=FakeSources(["/music"]),
    )
    bridge.refresh()

    score = bridge.homeScore()

    assert score["ready"] is True
    assert score["error"] == ""
    assert score["score"] >= 70
