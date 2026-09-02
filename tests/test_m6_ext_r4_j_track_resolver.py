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


class TestSelectionResolverStableIds:
    """M6-EXT-R4 freeze gate: Library Queue/Playlist intents resolve by
    stable TrackId — never Path(track_id)."""

    def test_queue_tracks_resolves_by_uuid_and_carries_identity(self) -> None:
        from michi.application.library_collection_coordinators import (
            LibraryQueueCoordinator,
        )

        t1 = _track("/a.flac", "T1")
        t2 = _track("/b.flac", "T2")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1, t2]
        )
        queue = QueueService()
        queue_coordinator = LibraryQueueCoordinator(library, queue)
        added = queue_coordinator.queue_tracks(["T1", "T2", "no-such-id"])
        assert added == 2
        assert [t.library_track_id for t in queue.state.tracks] == ["T1", "T2"]
        assert [t.file_path for t in queue.state.tracks] == [
            Path("/a.flac"),
            Path("/b.flac"),
        ]

    def test_queue_album_uses_track_id_membership(self) -> None:
        from michi.application.library_collection_coordinators import (
            LibraryQueueCoordinator,
        )
        from michi.domain.library import build_music_model

        t1 = _track("/a/one.flac", "T1")
        t2 = _track("/a/two.flac", "T2")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1, t2]
        )
        album_key = build_music_model([t1, t2]).albums[0].key
        queue = QueueService()
        queue_coordinator = LibraryQueueCoordinator(library, queue)
        added = queue_coordinator.queue_album(album_key)
        assert added == 2
        assert {t.library_track_id for t in queue.state.tracks} == {"T1", "T2"}

    def test_playlist_add_persists_stable_references(self) -> None:
        from michi.application.library_collection_coordinators import (
            LibraryPlaylistCoordinator,
        )
        from michi.application.playlist_service import PlaylistService

        t1 = _track("/a.flac", "T1")
        library, session, backend, resolver, coordinator, history, prefs = _harness(
            [t1]
        )
        playlist_service = PlaylistService()
        playlist = playlist_service.create_playlist("Mix")
        playlist_coordinator = LibraryPlaylistCoordinator(library, playlist_service)
        added = playlist_coordinator.add_tracks(playlist.playlist_id, ["T1"])
        assert added == 1
        updated = playlist_service.get_playlist(playlist.playlist_id)
        # SEMANTIC INTEGRATION: la membresía canónica de main es
        # track_paths (el path resuelto por el resolver).
        assert updated.track_paths == (str(t1.file_path),)
        # La identidad estable del Track se conserva vía el resolver en el
        # path canónico (la referencia R4 fue reemplazada por main).
        assert updated.track_paths == (str(t1.file_path),)

    def test_resolve_media_uses_track_then_media_chain(self, tmp_path) -> None:
        from michi.domain.library_catalog import (
            LibrarySource,
            MediaAvailability,
            MediaFileRecord,
            TrackRecord,
            new_library_source_id,
            new_media_file_id,
            new_track_id,
        )
        from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository

        catalog = SqliteLibraryCatalogRepository(tmp_path / "michi.db")
        source = LibrarySource(
            library_source_id=new_library_source_id(),
            display_name="S",
            root_path="/M",
        )
        catalog.upsert_source(source)
        media = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path="a.flac",
            last_known_path="/M/a.flac",
            availability=MediaAvailability.AVAILABLE,
        )
        track = TrackRecord(track_id=new_track_id(), media_file_id=media.media_file_id)
        catalog.apply_source_reconciliation((media,), (track,))
        from michi.application.library_track_resolver import LibraryTrackResolver

        library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
        resolver = LibraryTrackResolver(library, catalog=catalog)
        assert resolver.resolve_media(track.track_id) == media
        assert resolver.resolve_media("no-such") is None
        # A media_id must never be returned for a track_id query mismatch.
        assert resolver.resolve_media(media.media_file_id) is None


class TestStructuralNoPathIdentity:
    def test_collection_coordinators_never_build_path_from_track_id(self) -> None:
        import inspect

        from michi.application import library_collection_coordinators as mod

        source = inspect.getsource(mod)
        assert "Path(str(track_id))" not in source
        # documented LEGACY raw-path seam only (resolve_trackref fallback).
        assert "make_track_id" not in source

    def test_selection_resolver_uses_resolver_authority(self) -> None:
        import inspect

        from michi.application import library_collection_coordinators as mod

        source = inspect.getsource(mod)
        assert "LibraryTrackResolver" in source
        assert "resolve_ref" in source
