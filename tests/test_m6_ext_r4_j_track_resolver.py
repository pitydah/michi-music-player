"""M6-EXT-R4-J — LibraryTrackResolver + playback/history identity convergence."""

from pathlib import Path

from michi.application.library_playback_coordinator import LibraryPlaybackCoordinator
from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.playback_history_coordinator import PlaybackHistoryCoordinator
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.ports import LibraryPrefsPort
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryPrefs, TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.domain.playback_session import PlaybackSequenceEntry


class _StubScanner:
    """Validates every file (playable) — the filesystem gate never blocks."""

    def validate_file(self, path: Path) -> None:
        return None

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


class _StubPrefs(LibraryPrefsPort):
    def __init__(self) -> None:
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return LibraryPrefs()

    def save(self, prefs: LibraryPrefs) -> None:
        self.saved.append(prefs)


class _FakeBackend:
    def __init__(self) -> None:
        self.loaded: list[Path] = []

    def load(self, file_path: Path) -> None:
        self.loaded.append(file_path)

    def play(self) -> None: ...

    def pause(self) -> None: ...

    def resume(self) -> None: ...

    def stop(self) -> None: ...

    def set_volume(self, value: int) -> None: ...

    def set_muted(self, muted: bool) -> None: ...

    def seek(self, position_ms: int) -> None: ...

    def position(self) -> int:
        return 0

    def duration(self) -> int:
        return 0

    def subscribe_end_of_media(self, callback) -> None: ...

    def unsubscribe_end_of_media(self, callback) -> None: ...

    def subscribe_position_changed(self, callback) -> None: ...

    def unsubscribe_position_changed(self, callback) -> None: ...

    def subscribe_duration_changed(self, callback) -> None: ...

    def unsubscribe_duration_changed(self, callback) -> None: ...

    def subscribe_media_accepted(self, callback) -> None: ...

    def unsubscribe_media_accepted(self, callback) -> None: ...

    def subscribe_media_rejected(self, callback) -> None: ...

    def unsubscribe_media_rejected(self, callback) -> None: ...

    def subscribe_playback_state_changed(self, callback) -> None: ...

    def unsubscribe_playback_state_changed(self, callback) -> None: ...

    def emit_accepted(self, path: Path) -> None:
        for cb in self._accepted:
            cb(path)

    _accepted: list = None

    def __post_init__(self) -> None:
        self._accepted = []

    def _register(self):  # pragma: no cover
        pass


def _harness(tracks: list[TrackRef]):
    """LibraryService with pre-populated canonical tracks."""
    from michi.application.playback_service import PlaybackService

    scanner = _StubScanner()
    prefs = _StubPrefs()
    library = LibraryService(scanner, library_prefs=prefs)
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    backend = _FakeBackend()
    playback = PlaybackService(backend)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    resolver = LibraryTrackResolver(library)
    coordinator = LibraryPlaybackCoordinator(library, session, resolver=resolver)
    history = PlaybackHistoryCoordinator(session, library, resolver=resolver)
    history.start()
    return library, session, backend, resolver, coordinator, history, prefs


def _track(path: str, track_id: str) -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id="source-1",
        availability=MediaAvailability.AVAILABLE,
    )


class TestResolver:
    def test_resolve_ref_by_stable_id(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, *_ = _harness([t1])
        resolver = LibraryTrackResolver(library)
        assert resolver.resolve_ref("T1") == t1
        assert resolver.resolve_ref("nope") is None

    def test_resolve_legacy_path_fallback_id(self) -> None:
        t1 = _track("/a.flac", "")
        library, *_ = _harness([t1])
        resolver = LibraryTrackResolver(library)
        assert resolver.resolve_ref("legacy-path::/a.flac") == t1

    def test_resolve_path_and_playable_path(self) -> None:
        available = _track("/a.flac", "T1")
        missing = TrackRef(
            Path("/gone.flac"),
            title="gone",
            track_id="T2",
            availability=MediaAvailability.MISSING,
        )
        library, *_ = _harness([available, missing])
        resolver = LibraryTrackResolver(library)
        assert resolver.resolve_path("T1") == Path("/a.flac")
        assert resolver.resolve_playable_path("T1") == Path("/a.flac")
        assert resolver.resolve_playable_path("T2") is None  # MISSING forbids

    def test_find_track_id_by_path(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, *_ = _harness([t1])
        resolver = LibraryTrackResolver(library)
        assert resolver.find_track_id_by_path(Path("/a.flac")) == "T1"
        assert resolver.find_track_id_by_path(Path("/nope.flac")) is None


class TestPlaybackByIdentity:
    def test_play_track_by_id_carries_identity(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1]
        )
        coordinator.play_track_by_id("T1")
        # Backend accepted the CURRENT path of the stable id; the pending
        # request carries the stable identity.
        assert backend.loaded == [Path("/a.flac")]
        assert session._pending.library_track_id == "T1"

    def test_play_unknown_id_is_noop(self) -> None:
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [_track("/a.flac", "T1")]
        )
        coordinator.play_track_by_id("missing")
        assert backend.loaded == []

    def test_path_wrapper_delegates_to_identity(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1]
        )
        coordinator.play_track(Path("/a.flac"))
        assert session._pending.library_track_id == "T1"


class TestHistoryByIdentity:
    def test_history_recorded_by_stable_id_on_commit(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1]
        )
        coordinator.play_track_by_id("T1")
        # Simulate backend acceptance of the pending request:
        from michi.application.playback_session_service import PlaybackContextType

        pending = session._pending
        assert pending is not None
        session._commit(
            PlaybackContextType.SINGLE,
            None,
            [pending],
            0,
            pending,
            pending.file_path,
            session._request_epoch,
        )
        assert library.state.history_paths == ("/a.flac",)

    def test_commit_carries_library_id_into_entry_event(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1]
        )
        captured: list[PlaybackSequenceEntry] = []
        session.subscribe_entry_committed(captured.append)
        coordinator.play_track_by_id("T1")
        pending = session._pending
        from michi.application.playback_session_service import PlaybackContextType

        session._commit(
            PlaybackContextType.SINGLE,
            None,
            [pending],
            0,
            pending,
            pending.file_path,
            session._request_epoch,
        )
        assert captured[0].library_track_id == "T1"


class TestProductionGraphParity:
    def test_bootstrap_wires_single_production_resolver(self, tmp_path) -> None:
        from michi.bootstrap import _build_services

        graph = _build_services(tmp_path / "michi.db", backend=_FakeBackend())
        assert graph.track_resolver is not None
        # The SAME resolver instance backs playback and history.
        assert graph.library_playback._resolver is graph.track_resolver
        assert graph.history_coordinator._resolver is graph.track_resolver
        graph.shutdown if hasattr(graph, "shutdown") else None
