"""Comprehensive test suite for M9-R2.1 UI/UX Correction + Functional Hardening."""

import tempfile
from pathlib import Path

from michi.application.playlist_service import PlaylistService
from michi.application.ports import PlaylistsPort
from michi.domain.playlist import Playlist, PlaylistNavigationState
from michi.infrastructure.playlist_artwork_store import FilesystemPlaylistArtworkStore


class FakePlaylistsPort(PlaylistsPort):
    def __init__(self, initial=()):
        self.items = list(initial)
        self.nav = PlaylistNavigationState()

    def load(self):
        return tuple(self.items)

    def save(self, items):
        self.items = list(items)

    def load_navigation(self):
        return self.nav

    def save_navigation(self, state):
        self.nav = state


class FakeQueueService:
    def __init__(self):
        self.items = []
        self.current_index = -1

    def add(self, path: Path):
        self.items.append(str(path))

    def clear(self):
        self.items.clear()
        self.current_index = -1

    def play_index(self, index: int):
        if 0 <= index < len(self.items):
            self.current_index = index


def test_playlist_play_now_semantics():
    queue = FakeQueueService()
    queue.add(Path("/music/songA.flac"))
    assert len(queue.items) == 1

    port = FakePlaylistsPort(
        [
            Playlist(
                playlist_id="p1",
                name="Favorites",
                track_paths=("/music/1.flac", "/music/2.flac"),
            )
        ]
    )
    service = PlaylistService(queue, port)

    # play_playlist_now must clear existing queue and start at track 0 of playlist
    service.play_playlist_now("p1")
    assert queue.items == ["/music/1.flac", "/music/2.flac"]
    assert queue.current_index == 0


def test_playlist_enqueue_semantics():
    queue = FakeQueueService()
    queue.add(Path("/music/existing.flac"))
    queue.current_index = 0

    port = FakePlaylistsPort(
        [
            Playlist(
                playlist_id="p1",
                name="Favorites",
                track_paths=("/music/1.flac", "/music/2.flac"),
            )
        ]
    )
    service = PlaylistService(queue, port)

    # enqueue_playlist must preserve existing queue without resetting index
    service.enqueue_playlist("p1")
    assert queue.items == ["/music/existing.flac", "/music/1.flac", "/music/2.flac"]
    assert queue.current_index == 0


def test_playlist_bridge_no_private_queue_access():
    bridge_src = Path("src/michi/presentation/playlists_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "._queue" not in bridge_src
    assert "_playlist_service._queue" not in bridge_src


def test_playlist_custom_cover_managed_copy_and_survives_original_delete():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "covers"
        store = FilesystemPlaylistArtworkStore(storage_dir)

        # Create external source image
        source_file = Path(tmpdir) / "my_external_cover.jpg"
        source_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01")

        queue = FakeQueueService()
        port = FakePlaylistsPort(
            [Playlist(playlist_id="p1", name="Rock", track_paths=())]
        )
        service = PlaylistService(queue, port, artwork_store=store)

        managed_path = service.set_custom_cover("p1", source_file)
        assert managed_path is not None
        assert Path(managed_path).is_file()
        assert Path(managed_path).parent == storage_dir

        # Delete external source file
        source_file.unlink()
        assert not source_file.exists()

        # Managed copy still exists!
        assert Path(managed_path).is_file()
        p = service.get_playlist("p1")
        assert p.custom_cover_path == managed_path


def test_playlist_custom_cover_replace_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "covers"
        store = FilesystemPlaylistArtworkStore(storage_dir)

        # Create PNG and JPG source files
        png_file = Path(tmpdir) / "cover.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")
        jpg_file = Path(tmpdir) / "cover.jpg"
        jpg_file.write_bytes(b"\xff\xd8\xff\xe0\x00\x10JFIF")

        queue = FakeQueueService()
        port = FakePlaylistsPort([Playlist(playlist_id="p1", name="Chill")])
        service = PlaylistService(queue, port, artwork_store=store)

        png_managed = service.set_custom_cover("p1", png_file)
        assert Path(png_managed).is_file()

        # Replace with JPG
        jpg_managed = service.set_custom_cover("p1", jpg_file)
        assert Path(jpg_managed).is_file()
        # Old PNG must be deleted
        assert not Path(png_managed).is_file()


def test_playlist_delete_cover_cleanup():
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_dir = Path(tmpdir) / "covers"
        store = FilesystemPlaylistArtworkStore(storage_dir)

        png_file = Path(tmpdir) / "cover.png"
        png_file.write_bytes(b"\x89PNG\r\n\x1a\n")

        queue = FakeQueueService()
        port = FakePlaylistsPort([Playlist(playlist_id="p1", name="To Delete")])
        service = PlaylistService(queue, port, artwork_store=store)

        managed = service.set_custom_cover("p1", png_file)
        assert Path(managed).is_file()

        # Delete playlist deletes the cover
        service.delete_playlist("p1")
        assert not Path(managed).is_file()


def test_more_icon_not_sliders_for_overflow():
    for rel_path in [
        "src/michi/presentation/qml/playlists/PlaylistCard.qml",
        "src/michi/presentation/qml/playlists/PlaylistDetailView.qml",
        "src/michi/presentation/qml/playlists/PlaylistTrackList.qml",
    ]:
        content = Path(rel_path).read_text(encoding="utf-8")
        # Ensure 'sliders' is not used as 'more options'
        assert not ('iconName: "sliders"' in content and "More" in content)
