"""M9-R1: PlaylistsBridge — canonical first-class playlist presentation.

The bridge owns no business state: it projects PlaylistService +
coordinator. Rows are identity-driven; pinned/recent are projections;
selection is id-based; no service wired → safe empty surface.
"""

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.presentation.playlists_bridge import PlaylistsBridge
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


def _build(tmp_path=None, library=None):

    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(
        service,
        playlist_navigation=coord,
        navigation_service=nav,
        library=library,
    )
    return service, coord, bridge, nav


class TestRows:
    def test_rows_identity_correct(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, _, bridge, _ = _build(library=library)
        a = service.create_playlist("A")
        rows = bridge.property("playlists")
        assert rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "A"
        assert rows[0]["trackCount"] == 0
        assert rows[0]["pinned"] is False
        assert rows[0]["recentRank"] == -1

    def test_pinned_projection(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, _, bridge, _ = _build(library=library)
        service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(b.playlist_id)
        pinned = bridge.property("pinnedPlaylists")
        assert [r["playlistId"] for r in pinned] == [b.playlist_id]

    def test_recent_projection_excludes_pinned(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, _, bridge, _ = _build(library=library)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        c = service.create_playlist("C")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)  # A pinned + recent
        service.mark_recent(b.playlist_id)
        service.mark_recent(c.playlist_id)
        recent = bridge.property("recentPlaylists")
        assert [r["playlistId"] for r in recent] == [c.playlist_id, b.playlist_id]

    def test_recent_ordered_by_rank(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, _, bridge, _ = _build(library=library)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.mark_recent(a.playlist_id)
        service.mark_recent(b.playlist_id)
        recent = bridge.property("recentPlaylists")
        assert [r["playlistId"] for r in recent] == [b.playlist_id, a.playlist_id]


class TestSelection:
    """M9-R1I: selection IS navigation — the bridge has no local selection
    state; every selected* projection derives from NavigationState."""

    def test_open_playlist_drives_selection(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, coord, bridge, nav = _build(library=library)
        a = service.create_playlist("Road Trip")
        coord.open_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "Road Trip"

    def test_rename_updates_name_same_id(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, coord, bridge, nav = _build(library=library)
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        service.rename_playlist(a.playlist_id, "B")
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "B"

    def test_delete_selected_clears(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, coord, bridge, nav = _build(library=library)
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        service.delete_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []

    def test_open_all_clears_target(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, coord, bridge, nav = _build(library=library)
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        coord.open_all_playlists()
        assert bridge.property("selectedPlaylistId") == ""
        assert nav.state.playlist_id is None

    def test_no_bridge_local_selection_api(self):
        """The obsolete select_playlist/clear_playlist_selection are gone."""
        import inspect

        from michi.presentation.playlists_bridge import PlaylistsBridge

        src = inspect.getsource(PlaylistsBridge)
        assert "def select_playlist" not in src
        assert "def clear_playlist_selection" not in src
        assert "self._selected_playlist_id" not in src


class TestTracks:
    def test_track_rows_projection(self, tmp_path):
        library, _, _, (p1, p2) = _tracks(tmp_path)
        service, coord, bridge, _ = _build(library=library)
        a = service.create_playlist("A")
        service.add_track(a.playlist_id, p1)
        service.add_track(a.playlist_id, p2)
        coord.open_playlist(a.playlist_id)
        rows = bridge.property("playlistTrackRows")
        assert [r["path"] for r in rows] == [str(p1), str(p2)]


class TestIntents:
    def test_open_playlist_through_coordinator(self):
        service, coord, bridge, nav = _build()
        a = service.create_playlist("A")
        bridge.open_playlist(a.playlist_id)
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)

    def test_create_playlist(self):
        service, _, bridge, _ = _build()
        bridge.create_and_open_playlist("Jazz")
        assert len(service.playlists) == 1
        assert service.playlists[0].name == "Jazz"

    def test_create_duplicate_rejected(self):
        service, _, bridge, _ = _build()
        bridge.create_and_open_playlist("Jazz")
        assert bridge.create_and_open_playlist("Jazz") is False
        assert len(service.playlists) == 1

    def test_delete_and_pin_unpin(self):
        service, _, bridge, _ = _build()
        a = service.create_playlist("A")
        bridge.pin_playlist(a.playlist_id)
        assert a.playlist_id in service.navigation.pinned_ids
        bridge.unpin_playlist(a.playlist_id)
        assert a.playlist_id not in service.navigation.pinned_ids
        bridge.delete_playlist(a.playlist_id)
        assert len(service.playlists) == 0

    def test_add_track_to_playlist_cross_feature(self, tmp_path):
        library, _, _, (p1,) = _tracks(tmp_path, names=("one.mp3",))
        service, _, bridge, _ = _build(library=library)
        a = service.create_playlist("A")
        bridge.add_track_to_playlist(a.playlist_id, str(p1))
        assert service.playlists[0].track_paths == (str(p1),)

    def test_move_and_remove_track(self):
        service, coord, bridge, _ = _build()
        a = service.create_playlist("A")
        service.add_track(a.playlist_id, "/m/a.mp3")
        service.add_track(a.playlist_id, "/m/b.mp3")
        coord.open_playlist(a.playlist_id)
        bridge.move_track(0, 1)
        assert service.playlists[0].track_paths == ("/m/b.mp3", "/m/a.mp3")
        bridge.remove_track(1)
        assert service.playlists[0].track_paths == ("/m/b.mp3",)

    def test_play_selected_and_play_by_id(self):
        service, coord, bridge, _ = _build()
        a = service.create_playlist("A")
        service.add_track(a.playlist_id, "/m/a.mp3")
        coord.open_playlist(a.playlist_id)
        bridge.play_selected_playlist()
        # M4-R1: Play routes through PlaylistPlaybackCoordinator → the
        # PlaybackSession (PLAYLIST context); PlaylistService never owns a
        # queue.
        assert not hasattr(service, "_queue")  # no queue authority on service
        bridge.play_playlist(a.playlist_id)


class TestSearchProjection:
    def test_search_playlists_rows(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        service, _, bridge, _ = _build(library=library)
        a = service.create_playlist("Road Trip")
        library.search("Road")
        rows = bridge.property("searchPlaylists")
        assert rows and rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "Road Trip"


class TestNoServiceCompat:
    def test_safe_empty(self):
        bridge = PlaylistsBridge()
        assert bridge.property("playlists") == []
        assert bridge.property("pinnedPlaylists") == []
        assert bridge.property("recentPlaylists") == []
        assert bridge.property("selectedPlaylistId") == ""
        bridge.create_and_open_playlist("X")  # no-op
        bridge.delete_playlist("x")  # no-op
        bridge.open_playlist("x")  # no-op
        assert bridge.property("playlistTracks") == []
