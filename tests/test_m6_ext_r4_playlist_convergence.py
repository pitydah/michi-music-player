"""M6-EXT-R4 freeze gate — playlist runtime resolution by stable TrackId +
truthful persistence (goldens §7 and §19)."""

from pathlib import Path

import pytest

from michi.application.library_service import LibraryService
from michi.application.library_track_resolver import LibraryTrackResolver
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.playlist_playback_coordinator import (
    PlaylistPlaybackCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import TrackRef
from michi.domain.library_catalog import MediaAvailability
from michi.domain.playlist import PlaylistPersistenceError, PlaylistTrackReference


class _StubScanner:
    def validate_file(self, path: Path) -> None:
        return None

    def scan(self, root: Path):
        return []

    def fingerprint(self, path: Path):
        return (0, 0)


class _StubPrefs:
    def load(self):
        from michi.domain.library import LibraryPrefs

        return LibraryPrefs()

    def save(self, prefs):
        del prefs


class _FailingPlaylistsPort:
    """Truthful failure injection: save always raises."""

    def __init__(self) -> None:
        self.loaded: tuple = ()

    def load(self):
        return self.loaded

    def save(self, playlists) -> None:
        raise PlaylistPersistenceError("injected playlist write failure")

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save_navigation(self, state) -> None:
        del state


def _track(path: str, track_id: str) -> TrackRef:
    return TrackRef(
        Path(path),
        title=Path(path).stem,
        track_id=track_id,
        media_file_id=f"media-{track_id}",
        library_source_id="s1",
        availability=MediaAvailability.AVAILABLE,
    )


def _harness(tracks):
    from michi.application.playback_service import PlaybackService

    library = LibraryService(_StubScanner(), library_prefs=_StubPrefs())
    library._state.tracks = list(tracks)
    library._rebuild_derived_library_state()
    resolver = LibraryTrackResolver(library)
    playlists = PlaylistService()
    playback = PlaybackService(_FakeBackend())
    session = PlaybackSessionService(playback, QueueService())
    coordinator = PlaylistPlaybackCoordinator(
        playlists, session, QueueService(), resolver
    )
    return library, playlists, coordinator, resolver


class TestPlaylistRuntimeResolution:
    def test_golden_play_after_move_uses_new_path_same_id(self) -> None:
        """Create → add to playlist → move file → play → backend receives
        NEW path; library_track_id unchanged."""
        t1 = _track("/Music/A/song.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [PlaylistTrackReference(track_id="T1", fallback_path="/Music/A/song.flac")],
        )

        # The file moves; the TrackRef path projection updates.
        library._state.tracks = [_track("/Music/B/song.flac", "T1")]
        library._rebuild_derived_library_state()

        coordinator.play_playlist(playlist.playlist_id)
        pending = coordinator._session._pending
        assert pending is not None
        assert pending.file_path == Path("/Music/B/song.flac")  # NEW path
        assert pending.library_track_id == "T1"  # identity unchanged
        # Playlist membership still holds the stable id.
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

    def test_unresolved_legacy_falls_back_to_path(self) -> None:
        library, playlists, coordinator, resolver = _harness([])
        playlist = playlists.create_playlist_with_references(
            "Legacy", [PlaylistTrackReference(track_id="", fallback_path="/old/x.flac")]
        )
        coordinator.play_playlist(playlist.playlist_id)
        pending = coordinator._session._pending
        assert pending.file_path == Path("/old/x.flac")
        assert pending.library_track_id is None

    def test_missing_track_keeps_membership(self) -> None:
        t1 = _track("/Music/A/song.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix",
            [PlaylistTrackReference(track_id="T1", fallback_path="/Music/A/song.flac")],
        )
        # Track becomes MISSING: unplayable → skipped at play time, but the
        # playlist membership is never removed.
        missing = TrackRef(
            Path("/Music/A/song.flac"),
            title="song",
            track_id="T1",
            availability=MediaAvailability.MISSING,
        )
        library._state.tracks = [missing]
        library._rebuild_derived_library_state()
        coordinator.play_playlist(playlist.playlist_id)
        assert coordinator._session._pending is None  # nothing playable
        assert playlists.get_playlist(playlist.playlist_id).track_ids == ("T1",)

    def test_queue_playlist_carries_identity(self) -> None:
        t1 = _track("/a.flac", "T1")
        library, playlists, coordinator, resolver = _harness([t1])
        playlist = playlists.create_playlist_with_references(
            "Mix", [PlaylistTrackReference(track_id="T1", fallback_path="/a.flac")]
        )
        queue = QueueService()
        coordinator._queue = queue
        coordinator.queue_playlist(playlist.playlist_id)
        assert queue.state.tracks[0].library_track_id == "T1"


class TestPlaylistTruthfulPersistence:
    def test_create_failure_never_publishes(self) -> None:
        port = _FailingPlaylistsPort()
        service = PlaylistService(playlists_port=port)
        with pytest.raises(PlaylistPersistenceError):
            service.create_playlist("Mix")
        assert service.playlists == ()

    def test_mutation_failure_rolls_back(self) -> None:
        class _OkThenFail:
            """First save succeeds (create), then failures."""

            def __init__(self) -> None:
                self.saved = 0

            def load(self):
                return ()

            def save(self, playlists) -> None:
                self.saved += 1
                if self.saved > 1:
                    raise PlaylistPersistenceError("injected failure")

            def load_navigation(self):
                from michi.domain.playlist import PlaylistNavigationState

                return PlaylistNavigationState()

            def save_navigation(self, state) -> None:
                del state

        service = PlaylistService(playlists_port=_OkThenFail())
        playlist = service.create_playlist("Mix")
        with pytest.raises(PlaylistPersistenceError):
            service.rename_playlist(playlist.playlist_id, "Renamed")
        # In-memory state rolled back to the last persisted snapshot.
        assert service.playlists[0].name == "Mix"


class _FakeBackend:
    """Minimal AudioPort fake (play request only, no acceptance)."""

    def load(self, file_path): ...

    def play(self): ...

    def pause(self): ...

    def resume(self): ...

    def stop(self): ...

    def set_volume(self, value): ...

    def set_muted(self, muted): ...

    def seek(self, position_ms): ...

    def position(self):
        return 0

    def duration(self):
        return 0

    def subscribe_end_of_media(self, cb): ...

    def unsubscribe_end_of_media(self, cb): ...

    def subscribe_position_changed(self, cb): ...

    def unsubscribe_position_changed(self, cb): ...

    def subscribe_duration_changed(self, cb): ...

    def unsubscribe_duration_changed(self, cb): ...

    def subscribe_media_accepted(self, cb): ...

    def unsubscribe_media_accepted(self, cb): ...

    def subscribe_media_rejected(self, cb): ...

    def unsubscribe_media_rejected(self, cb): ...

    def subscribe_playback_state_changed(self, cb): ...

    def unsubscribe_playback_state_changed(self, cb): ...
