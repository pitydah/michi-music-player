"""M9-R3 gates for application-owned Library collection actions."""

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtTest import QSignalSpy

from michi.application.library_collection_coordinators import (
    LibraryPlaylistCoordinator,
    LibraryQueueCoordinator,
)
from michi.application.library_track_query import LibraryTrackQueryService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.library import (
    AlbumRef,
    ArtistRef,
    TrackRef,
    make_artist_key,
    make_genre_key,
)
from michi.presentation.library_bridge import LibraryBridge


class _Library:
    def __init__(self, tracks, albums=()):
        artist_names = sorted({ref.artist for ref in tracks})
        self.state = SimpleNamespace(
            tracks=tuple(tracks),
            albums=tuple(albums),
            artists=tuple(
                ArtistRef(make_artist_key(name), name, 0, 0) for name in artist_names
            ),
        )
        self._tracks = {ref.file_path: ref for ref in tracks}

    def resolve_trackref(self, path):
        return self._tracks.get(Path(path))

    def subscribe_changed(self, _callback):
        pass

    def unsubscribe_changed(self, _callback):
        pass


class _PlaylistPort:
    def __init__(self):
        self.saved = []

    def load(self):
        return ()

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save(self, playlists):
        self.saved.append(playlists)

    def save_navigation(self, navigation):
        pass


def _library():
    tracks = [
        TrackRef(Path("/music/a.flac"), artist="Alpha", album="First"),
        TrackRef(Path("/music/b.flac"), artist="Alpha", album="First"),
        TrackRef(Path("/music/c.flac"), artist="Beta", album="Second"),
    ]
    album = AlbumRef(
        key="album-first",
        title="First",
        artist="Alpha",
        track_count=2,
        duration_ms=0,
        track_paths=(tracks[0].file_path, tracks[1].file_path),
    )
    return _Library(tracks, (album,)), tracks


def test_playlist_batch_add_persists_and_notifies_once() -> None:
    port = _PlaylistPort()
    service = PlaylistService(playlists_port=port)
    playlist = service.create_playlist("Focus")
    port.saved.clear()
    changes = []
    service.subscribe_changed(lambda: changes.append(True))

    added = service.add_tracks(
        playlist.playlist_id,
        [Path("/music/a.flac"), Path("/music/a.flac"), Path("/music/b.flac")],
    )

    assert added == 2
    assert service.get_playlist(playlist.playlist_id).track_paths == (
        "/music/a.flac",
        "/music/b.flac",
    )
    assert len(port.saved) == 1
    assert changes == [True]


def test_create_playlist_with_tracks_is_one_atomic_publication() -> None:
    port = _PlaylistPort()
    service = PlaylistService(playlists_port=port)
    changes = []
    service.subscribe_changed(lambda: changes.append(True))

    playlist = service.create_playlist_with_tracks(
        "Album Set",
        [Path("/music/a.flac"), Path("/music/a.flac"), Path("/music/b.flac")],
    )

    assert playlist.name == "Album Set"
    assert playlist.track_paths == ("/music/a.flac", "/music/b.flac")
    assert service.get_playlist(playlist.playlist_id) == playlist
    assert len(port.saved) == 1
    assert changes == [True]


def test_queue_coordinator_resolves_and_appends_selection_atomically() -> None:
    library, tracks = _library()
    queue = QueueService()
    coordinator = LibraryQueueCoordinator(library, queue)

    added = coordinator.queue_tracks(
        [str(tracks[1].file_path), "/missing.flac", str(tracks[0].file_path)]
    )

    assert added == 2
    assert [track.file_path for track in queue.state.tracks] == [
        tracks[1].file_path,
        tracks[0].file_path,
    ]


def test_genre_query_uses_canonical_key_and_preserves_source_order() -> None:
    tracks = [
        TrackRef(Path("/music/a.flac"), genre="Ambient"),
        TrackRef(Path("/music/b.flac"), genre="Rock"),
        TrackRef(Path("/music/c.flac"), genre=" ambient  "),
    ]

    filtered = LibraryTrackQueryService.filter_genre(tracks, make_genre_key("AMBIENT"))

    assert [track.file_path for track in filtered] == [
        Path("/music/a.flac"),
        Path("/music/c.flac"),
    ]


def test_collection_coordinators_resolve_album_and_artist_ids() -> None:
    library, tracks = _library()
    queue = QueueService()
    playlists = PlaylistService()
    playlist = playlists.create_playlist("Collection")
    queue_coordinator = LibraryQueueCoordinator(library, queue)
    playlist_coordinator = LibraryPlaylistCoordinator(library, playlists)

    assert queue_coordinator.queue_album("album-first") == 2
    assert (
        playlist_coordinator.add_artist(playlist.playlist_id, make_artist_key("Beta"))
        == 1
    )
    assert playlists.get_playlist(playlist.playlist_id).track_paths == (
        str(tracks[2].file_path),
    )


def test_playlist_coordinator_creates_from_canonical_album_atomically() -> None:
    library, tracks = _library()
    port = _PlaylistPort()
    playlists = PlaylistService(playlists_port=port)
    coordinator = LibraryPlaylistCoordinator(library, playlists)

    playlist = coordinator.create_from_album("First Set", "album-first")

    assert playlist is not None
    assert playlist.track_paths == tuple(str(track.file_path) for track in tracks[:2])
    assert len(port.saved) == 1
    assert coordinator.create_from_album("Missing", "missing") is None


def test_unknown_identities_are_truthful_no_ops() -> None:
    library, _ = _library()
    queue = QueueService()
    playlists = PlaylistService()
    queue_coordinator = LibraryQueueCoordinator(library, queue)
    playlist_coordinator = LibraryPlaylistCoordinator(library, playlists)

    assert queue_coordinator.queue_album("missing") == 0
    assert playlist_coordinator.add_tracks("missing", ["/music/a.flac"]) == 0
    assert queue.state.count == 0


def test_bridge_requests_picker_only_for_known_collection_identities() -> None:
    library, _ = _library()
    bridge = LibraryBridge(library, playlist_coordinator=object())
    spy = QSignalSpy(bridge.playlist_target_requested)

    bridge.request_album_playlist_target("missing")
    bridge.request_album_playlist_target("album-first")
    bridge.request_artist_playlist_target(make_artist_key("Beta"))
    bridge.request_tracks_playlist_target(["/music/a.flac"])

    assert spy.count() == 3
    assert list(spy.at(0)) == [{"kind": "album", "albumKey": "album-first"}]
    assert list(spy.at(1)) == [{"kind": "artist", "artistKey": make_artist_key("Beta")}]
    assert list(spy.at(2)) == [{"kind": "tracks", "trackIds": ["/music/a.flac"]}]


def test_bridge_creates_playlist_from_semantic_selection() -> None:
    library, tracks = _library()
    playlists = PlaylistService()
    coordinator = LibraryPlaylistCoordinator(library, playlists)
    bridge = LibraryBridge(library, playlist_coordinator=coordinator)

    playlist_id = bridge.create_playlist_from_album("First Set", "album-first")

    playlist = playlists.get_playlist(playlist_id)
    assert playlist is not None
    assert playlist.track_paths == tuple(str(track.file_path) for track in tracks[:2])
    assert bridge.create_playlist_from_album("Missing", "missing") == ""
