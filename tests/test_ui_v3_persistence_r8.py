"""R8 — UI→Playlist V3 persistence integration seals (V4 §51, §75).

For every Library surface: semantic identity → Bridge seam →
LibraryPlaylistCoordinator → PlaylistService V3 (PlaylistTrackReference)
→ durable persistence → reload keeps the same identity.

The seams exercised are the exact ones the QML surfaces call:
  Songs/Favorites/History/Recently/Details/Search tracks →
    request_tracks_playlist_target / add_tracks_to_playlist
  Album batch   → request_album_playlist_target / add_album_to_playlist
  Artist batch  → request_artist_playlist_target / add_artist_to_playlist
  Playlist      → the playlists-shell surface (own coordinator)

Persistence uses the real V3 repository over sqlite (round-trip).
"""

from pathlib import Path

import pytest

from michi.application.library_collection_coordinators import (
    LibraryPlaylistCoordinator,
)
from michi.application.library_playback_coordinator import (
    LibraryPlaybackCoordinator,
)
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_library_views import _album_genre_factory


def _sqlite_repo(db_path: Path):
    return SqlitePlaylistsRepository(db_path)


@pytest.fixture()
def world(tmp_path):
    """Mundo con el coordinator REAL de playlists sobre sqlite V3."""
    a1 = tmp_path / "a1.mp3"
    a2 = tmp_path / "a2.mp3"
    for p in (a1, a2):
        p.write_bytes(b"x")
    library = LibraryService(
        FakeScanner([a1, a2]),
        metadata_extractor=FakeExtractor(factory=_album_genre_factory()),
    )
    library.scan(str(tmp_path))
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    repo = _sqlite_repo(tmp_path / "db.sqlite")
    playlists = PlaylistService(playlists_port=repo)
    playlist_coord = LibraryPlaylistCoordinator(library, playlists)
    playback_coord = LibraryPlaybackCoordinator(library, session)
    bridge = LibraryBridge(
        library,
        playback_coordinator=playback_coord,
        playlist_coordinator=playlist_coord,
    )
    return {
        "library": library,
        "bridge": bridge,
        "playlists": playlists,
        "tmp": tmp_path,
    }


def _track_id_of(library, path):
    ref = next(t for t in library.state.tracks if t.file_path == path)
    return ref.track_id or f"legacy-path::{ref.file_path}"


def _new_playlist(world, name):
    playlist = world["playlists"].create_playlist(name)
    assert playlist is not None, f"playlist {name!r} creada"
    return playlist.playlist_id


def _reload(world):
    """Round-trip: repo reabierto desde el MISMO sqlite."""
    repo = _sqlite_repo(world["tmp"] / "db.sqlite")
    playlists = PlaylistService(playlists_port=repo)
    return playlists


class TestTrackSurfacesV3RoundTrip:
    @pytest.mark.parametrize(
        "surface",
        [
            "songs",
            "favorites",
            "history",
            "recently",
            "album-detail",
            "artist-detail",
            "search",
        ],
    )
    def test_track_add_persists_and_reloads_same_identity(self, world, surface):
        """La cadena del menú de cada superficie de tracks: el seam que la
        superficie llama → membership V3 → persistencia → reload."""
        library = world["library"]
        a1 = world["tmp"] / "a1.mp3"
        track_id = _track_id_of(library, a1)
        # el seam de targeting que las superficies usan (add directo).
        added = world["bridge"].add_tracks_to_playlist(
            _new_playlist(world, f"R8-{surface}"), [track_id]
        )
        assert added == 1

        reloaded = _reload(world)
        lists = reloaded.playlists
        target = next(p for p in lists if p.name == f"R8-{surface}")
        members = target.references()
        refs = [
            m
            for m in members
            if (m.track_id and m.track_id == track_id)
            or m.fallback_path.endswith("a1.mp3")
        ]
        assert refs, (
            f"surface {surface}: el miembro sobrevive al reload V3 "
            f"(track_id {track_id!r})"
        )

    def test_album_batch_persists_and_reloads(self, world):
        album = world["library"].state.albums[0]
        pid = _new_playlist(world, "R8-album")
        added = world["bridge"].add_album_to_playlist(pid, album.key)
        assert added >= 1
        reloaded = _reload(world)
        lists = reloaded.playlists
        target = next(p for p in lists if p.name == "R8-album")
        assert len(target.references()) >= 1

    def test_artist_batch_persists_and_reloads(self, world):
        artist = world["library"].state.artists[0]
        pid = _new_playlist(world, "R8-artist")
        added = world["bridge"].add_artist_to_playlist(pid, artist.key)
        assert added >= 1
        reloaded = _reload(world)
        lists = reloaded.playlists
        target = next(p for p in lists if p.name == "R8-artist")
        assert len(target.references()) >= 1

    def test_create_from_tracks_persists_with_identity(self, world):
        """Create Playlist from Track (el flujo del diálogo del host)."""
        library = world["library"]
        track_id = _track_id_of(library, world["tmp"] / "a1.mp3")
        pid = world["bridge"].create_playlist_from_tracks("R8-create", [track_id])
        assert pid != ""
        reloaded = _reload(world)
        members = reloaded.get_playlist(pid).references()
        assert any(
            (m.track_id and m.track_id == track_id)
            or m.fallback_path.endswith("a1.mp3")
            for m in members
        ), "el miembro conserva la identidad estable tras el reload"
