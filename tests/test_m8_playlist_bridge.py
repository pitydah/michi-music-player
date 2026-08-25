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
from michi.presentation.navigation_bridge import NavigationBridge
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


def _make_bridge(service, library=None):
    """M9-R1I: selection IS navigation — bridge projects NavigationState."""
    from michi.application.navigation_service import NavigationService
    from michi.application.playlist_navigation_coordinator import (
        PlaylistNavigationCoordinator,
    )

    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(
        service,
        playlist_navigation=coord,
        navigation_service=nav,
        library=library,
    )
    return bridge, coord, nav


class TestPlaylistRows:
    def test_rows_expose_identity_and_navigation_metadata(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.create_playlist("Chill")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        bridge, _, _ = _make_bridge(service, library=library)
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
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Jazz")
        service.rename_playlist(a.playlist_id, "Jazz Nocturno")
        bridge, _, _ = _make_bridge(service, library=library)
        rows = bridge.property("playlists")
        assert rows[0]["name"] == "Jazz Nocturno"
        assert rows[0]["playlistId"] == a.playlist_id
        bridge.dispose()


class TestSelectionByIdentity:
    def test_select_by_id_and_derived_name(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "Road Trip"
        bridge.dispose()

    def test_rename_updates_name_while_id_stays(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        service.rename_playlist(a.playlist_id, "Road Trip Long")
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        assert bridge.property("selectedPlaylistName") == "Road Trip Long"
        bridge.dispose()

    def test_name_is_not_identity(self, tmp_path):
        """M9-R1I: names never resolve — opening by name falls back safely
        to All Playlists (name-based presentation identity is gone)."""
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        service.create_playlist("Legacy")
        bridge, _, nav = _make_bridge(service, library=library)
        bridge.open_playlist("Legacy")
        assert nav.state.playlist_id is None  # safe fallback (All Playlists)
        assert bridge.property("selectedPlaylistId") == ""
        bridge.dispose()

    def test_unknown_selection_noop(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        bridge, _, _ = _make_bridge(PlaylistService(playlists_port=FakePlaylistsPort()))
        bridge.open_playlist("ghost-id")
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        bridge.dispose()


class TestTracksProjection:
    def test_playlist_tracks_still_correct(self, tmp_path):
        library, queue, _, (p1, p2) = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.add_track(a.playlist_id, p1)
        service.add_track(a.playlist_id, p2)
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p1),
            str(p2),
        ]
        rows = bridge.property("playlistTrackRows")
        assert [r["path"] for r in rows] == [str(p1), str(p2)]
        bridge.dispose()

    def test_tracks_after_rename(self, tmp_path):
        library, queue, _, (p1,) = _tracks(tmp_path, names=("one.mp3",))
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        service.add_track(a.playlist_id, p1)
        service.rename_playlist(a.playlist_id, "B")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        assert len(bridge.property("playlistTracks")) == 1
        bridge.dispose()


class TestNoServiceCompat:
    def test_safe_empty_surface(self, tmp_path):
        library, _, _, _ = _tracks(tmp_path)
        bridge = PlaylistsBridge()  # no playlist service
        assert bridge.property("playlists") == []
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.open_playlist("anything")  # no-op, no crash
        bridge.create_and_open_playlist("X")  # no-op
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

    def test_no_raw_navigate_slot(self):
        """M9-R1 seal: the raw navigate_to_playlist slot is NOT public."""
        from michi.application.navigation_service import NavigationService

        service = NavigationService()
        bridge = NavigationBridge(service)
        assert not hasattr(bridge, "navigate_to_playlist")
        assert hasattr(bridge, "open_playlist")
        assert hasattr(bridge, "open_all_playlists")
        bridge.dispose()


def test_play_track_plays_playlist_from_index(tmp_path):
    """Editorial playlist page: selecting and playing a track must not
    require queue operations — the queue is a consequence of playback."""
    library, queue, audio, paths = _tracks(tmp_path, ("a.mp3", "b.mp3", "c.mp3"))
    service = PlaylistService(queue, FakePlaylistsPort())
    bridge, coord, _ = _make_bridge(service, library=library)
    pid = service.create_playlist("Road").playlist_id
    for p in paths:
        service.add_track(pid, p)
    coord.open_playlist(pid)

    bridge.play_track(1)  # start from the second track

    assert queue.state.count == 3
    # current_index commits only on media acceptance (canonical queue gate)
    audio.trigger_media_accepted(paths[1])
    assert queue.state.current_index == 1
    assert queue.state.tracks[queue.state.current_index].file_path.name == "b.mp3"


def test_play_track_clamps_out_of_range_index(tmp_path):
    library, queue, audio, paths = _tracks(tmp_path, ("a.mp3", "b.mp3"))
    service = PlaylistService(queue, FakePlaylistsPort())
    bridge, coord, _ = _make_bridge(service, library=library)
    pid = service.create_playlist("Road").playlist_id
    for p in paths:
        service.add_track(pid, p)
    coord.open_playlist(pid)

    bridge.play_track(99)

    assert queue.state.count == 2
    audio.trigger_media_accepted(paths[1])
    assert queue.state.current_index == 1  # clamped to last track


def test_queue_insert_at_restores_removed_position(tmp_path):
    """Undo support: insert_at puts a removed track back where it was."""
    library, queue, audio, paths = _tracks(tmp_path, ("a.mp3", "b.mp3", "c.mp3"))
    for p in paths:
        queue.add(p)
    queue.remove(1)  # b removed
    assert [t.file_path.name for t in queue.state.tracks] == ["a.mp3", "c.mp3"]
    queue.insert_at(1, paths[1])
    assert [t.file_path.name for t in queue.state.tracks] == ["a.mp3", "b.mp3", "c.mp3"]
    # clamping: beyond the end appends
    queue.insert_at(99, paths[0])
    assert queue.state.count == 4
