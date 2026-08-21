"""M8-R1F: presentation bridge convergence gates.

- Bridge product path: open_playlist (validated) / open_all_playlists.
- Invalid-id product path: no dangling target, recent untouched.
- searchPlaylists rows carry the canonical playlistId.
- Delete of the selected playlist clears bridge selection safely.
"""

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.navigation import AppRoute
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.navigation_bridge import NavigationBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_playlists import FakePlaylistsPort, _make_library_and_queue


def _tracks(tmp_path, names=("one.mp3", "two.mp3")):
    paths = []
    for name in names:
        p = tmp_path / name
        p.write_bytes(b"x")
        paths.append(p)
    library, queue, audio = _make_library_and_queue(
        FakeScanner(paths), extractor=FakeExtractor()
    )
    library.scan(str(tmp_path))
    return library, queue, audio, paths


def _nav_bridge():
    from michi.application.playback_service import PlaybackService

    audio = FakeAudioPort()
    queue = QueueService(PlaybackService(audio))
    service = PlaylistService(queue, FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = NavigationBridge(nav, playlist_navigation=coord)
    return service, nav, coord, bridge


class TestBridgeOpenIntent:
    def test_open_playlist_valid(self):
        service, nav, _, bridge = _nav_bridge()
        a = service.create_playlist("A")
        bridge.open_playlist(a.playlist_id)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_open_playlist_unknown_falls_back(self):
        service, nav, _, bridge = _nav_bridge()
        bridge.open_playlist("ghost")
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert bridge.property("playlistId") == ""
        assert service.navigation.recent_ids == ()

    def test_open_all_playlists(self):
        service, nav, _, bridge = _nav_bridge()
        a = service.create_playlist("A")
        service.mark_recent(a.playlist_id)
        bridge.open_all_playlists()
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_raw_navigate_slot_is_sealed(self):
        _, nav, _, bridge = _nav_bridge()
        assert not hasattr(bridge, "navigate_to_playlist")


class TestSearchPlaylistIdentity:
    def test_search_rows_expose_playlist_id(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge = LibraryBridge(library, service)
        bridge.search("Road")
        rows = bridge.property("searchPlaylists")
        assert rows and rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "Road Trip"
        assert rows[0]["trackCount"] == 0
        bridge.dispose()

    def test_search_after_rename_same_id_new_name(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.rename_playlist(a.playlist_id, "Road Trip Long")
        bridge = LibraryBridge(library, service)
        bridge.search("Road")
        rows = bridge.property("searchPlaylists")
        assert rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "Road Trip Long"
        bridge.dispose()

    def test_search_playlist_supports_open_intent_chain(self, tmp_path):
        """M9-R1 readiness: search row playlistId → openPlaylist works."""
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge = LibraryBridge(library, service)
        bridge.search("Road")
        row = bridge.property("searchPlaylists")[0]
        coord.open_playlist(row["playlistId"])
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)
        bridge.dispose()


class TestBridgeDeleteSelection:
    def test_delete_selected_clears_bridge_state(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("A")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        service.delete_playlist(a.playlist_id)  # service-level delete
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_delete_selected_via_bridge_slot(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("A")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        bridge.delete_playlist("A")
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_delete_other_keeps_selection(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        service.delete_playlist(b.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        bridge.dispose()
