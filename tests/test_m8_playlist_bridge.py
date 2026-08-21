"""M8-R1: presentation bridge gates — identity-driven playlist surface.

Contracts:
- playlist rows expose playlistId + pinned + recentRank
- selection is identity-driven (select by id); name is display-only
- selectedPlaylistId / selectedPlaylistName exposed
- rename updates the displayed name while the id remains
- playlistTracks / playlistTrackRows stay correct
- NavigationBridge exposes the PLAYLISTS route + playlist target
- no PlaylistService wired → safe empty surface
"""

from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.navigation_bridge import NavigationBridge
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


class TestPlaylistRows:
    def test_rows_expose_identity_and_navigation_metadata(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.create_playlist("Chill")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        bridge = LibraryBridge(library, service)
        rows = bridge.property("playlists")
        by_name = {r["name"]: r for r in rows}
        assert by_name["Road Trip"]["playlistId"] == a.playlist_id
        assert by_name["Road Trip"]["pinned"] is True
        assert by_name["Road Trip"]["recentRank"] == 0
        assert by_name["Chill"]["pinned"] is False
        assert by_name["Chill"]["recentRank"] == -1
        bridge.dispose()

    def test_rows_names_are_display_only(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Jazz")
        service.rename_playlist(a.playlist_id, "Jazz Nocturno")
        bridge = LibraryBridge(library, service)
        rows = bridge.property("playlists")
        assert rows[0]["name"] == "Jazz Nocturno"
        assert rows[0]["playlistId"] == a.playlist_id
        bridge.dispose()


class TestSelectionByIdentity:
    def test_select_by_id_and_derived_name(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "Road Trip"
        bridge.dispose()

    def test_rename_updates_name_while_id_stays(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        service.rename_playlist(a.playlist_id, "Road Trip Long")
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "Road Trip Long"
        bridge.dispose()

    def test_legacy_name_selection_resolves_to_id(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Legacy")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist("Legacy")  # DEPRECATED compat path
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        bridge.dispose()

    def test_unknown_selection_noop(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        bridge = LibraryBridge(library, PlaylistService(queue, FakePlaylistsPort()))
        bridge.select_playlist("ghost-id")
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        bridge.dispose()


class TestTracksProjection:
    def test_playlist_tracks_still_correct(self, tmp_path):
        library, queue, _, (p1, p2) = _tracks(tmp_path)
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.add_track(a.playlist_id, p1)
        service.add_track(a.playlist_id, p2)
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p1),
            str(p2),
        ]
        rows = bridge.property("playlistTrackRows")
        assert [r["path"] for r in rows] == [str(p1), str(p2)]
        bridge.dispose()

    def test_tracks_after_rename(self, tmp_path):
        library, queue, _, (p1,) = _tracks(tmp_path, names=("one.mp3",))
        service = PlaylistService(queue, FakePlaylistsPort())
        a = service.create_playlist("A")
        service.add_track(a.playlist_id, p1)
        service.rename_playlist(a.playlist_id, "B")
        bridge = LibraryBridge(library, service)
        bridge.select_playlist(a.playlist_id)
        assert len(bridge.property("playlistTracks")) == 1
        bridge.dispose()


class TestNoServiceCompat:
    def test_safe_empty_surface(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        bridge = LibraryBridge(library)  # no playlist service
        assert bridge.property("playlists") == []
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.select_playlist("anything")  # no-op, no crash
        bridge.create_playlist("X")  # no-op
        bridge.delete_playlist("X")  # no-op
        bridge.dispose()


class TestNavigationBridge:
    def _nav_bridge(self):
        from michi.application.navigation_service import NavigationService

        return NavigationService(), NavigationBridge(NavigationService())

    def test_playlists_route_exposed(self):
        from michi.application.navigation_service import NavigationService

        service = NavigationService()
        bridge = NavigationBridge(service)
        service.navigate(AppRoute.PLAYLISTS.value)
        assert bridge.property("currentRoute") == "playlists"
        assert bridge.property("playlistId") == ""
        bridge.dispose()

    def test_playlist_target_exposed(self):
        from michi.application.navigation_service import NavigationService

        service = NavigationService()
        bridge = NavigationBridge(service)
        service.navigate_to_playlist("id-77")
        assert bridge.property("currentRoute") == "playlists"
        assert bridge.property("playlistId") == "id-77"
        bridge.dispose()

    def test_slot_navigate_to_playlist(self):
        from michi.application.navigation_service import NavigationService

        service = NavigationService()
        bridge = NavigationBridge(service)
        bridge.navigate_to_playlist("id-1")
        assert service.state.playlist_id == "id-1"
        assert service.state.current_route == AppRoute.PLAYLISTS
        bridge.dispose()
