"""Tests for M9-R2 Playlists: covers, duration, mosaic, and artwork store."""

from pathlib import Path

from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.playlist import Playlist
from michi.infrastructure.playlist_artwork_store import FilesystemPlaylistArtworkStore
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.playlists_bridge import PlaylistsBridge

QML = Path("src/michi/presentation/qml")


def _queue() -> QueueService:
    return QueueService()


def test_playlist_domain_and_service_custom_cover() -> None:
    queue = _queue()
    service = PlaylistService(queue)
    p = service.create_playlist("Chill")
    assert p.custom_cover_path == ""

    # Set custom cover
    service.set_custom_cover(p.playlist_id, "/path/to/cover.jpg")
    p_updated = service.get_playlist(p.playlist_id)
    assert p_updated is not None
    assert p_updated.custom_cover_path == "/path/to/cover.jpg"

    # Add track preserves cover
    service.add_track(p.playlist_id, "/music/track1.mp3")
    p_with_track = service.get_playlist(p.playlist_id)
    assert p_with_track is not None
    assert p_with_track.custom_cover_path == "/path/to/cover.jpg"
    assert len(p_with_track.track_paths) == 1

    # Rename preserves cover
    service.rename_playlist(p.playlist_id, "Chill Out")
    p_renamed = service.get_playlist(p.playlist_id)
    assert p_renamed is not None
    assert p_renamed.custom_cover_path == "/path/to/cover.jpg"
    assert p_renamed.name == "Chill Out"

    # Remove cover
    service.remove_custom_cover(p.playlist_id)
    p_no_cover = service.get_playlist(p.playlist_id)
    assert p_no_cover is not None
    assert p_no_cover.custom_cover_path == ""


def test_sqlite_repository_persists_custom_cover(tmp_path: Path) -> None:
    db_path = tmp_path / "test_library.db"
    repo = SqlitePlaylistsRepository(db_path)
    playlists = (
        Playlist(
            playlist_id="p1",
            name="Rock",
            track_paths=("/a.mp3",),
            custom_cover_path="/covers/rock.png",
        ),
        Playlist(
            playlist_id="p2", name="Jazz", track_paths=("/b.mp3",), custom_cover_path=""
        ),
    )
    repo.save(playlists)

    loaded = repo.load()
    assert len(loaded) == 2
    assert loaded[0].playlist_id == "p1"
    assert loaded[0].custom_cover_path == "/covers/rock.png"
    assert loaded[1].playlist_id == "p2"
    assert loaded[1].custom_cover_path == ""


def test_filesystem_playlist_artwork_store(tmp_path: Path) -> None:
    store_dir = tmp_path / "covers"
    store = FilesystemPlaylistArtworkStore(store_dir)

    src_img = tmp_path / "source.png"
    src_img.write_bytes(b"dummy png content")

    stored_path = store.store_cover("pl-123", src_img)
    assert stored_path is not None
    assert Path(stored_path).is_file()
    assert Path(stored_path).name == "playlist_pl-123.png"

    # Delete cover
    store.delete_cover("pl-123")
    assert not Path(stored_path).exists()


def test_playlists_bridge_mosaic_and_duration_projections() -> None:
    queue = _queue()
    service = PlaylistService(queue)
    bridge = PlaylistsBridge(playlist_service=service)
    p = service.create_playlist("Favorites")
    service.set_custom_cover(p.playlist_id, "/custom.jpg")

    rows = bridge.property("playlists")
    assert len(rows) == 1
    assert rows[0]["playlistId"] == p.playlist_id
    assert rows[0]["customCoverPath"] == "/custom.jpg"
    assert "mosaicArtworkPaths" in rows[0]
    assert "durationMs" in rows[0]
