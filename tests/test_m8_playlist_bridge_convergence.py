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
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
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

    _queue = QueueService()
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = NavigationBridge(nav, playlist_navigation=coord)
    return service, nav, coord, bridge


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
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        bridge, _, _ = _make_bridge(service, library=library)
        library.search("Road")
        rows = bridge.property("searchPlaylists")
        assert rows and rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "Road Trip"
        assert rows[0]["trackCount"] == 0
        bridge.dispose()

    def test_search_after_rename_same_id_new_name(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        service.rename_playlist(a.playlist_id, "Road Trip Long")
        bridge, _, _ = _make_bridge(service, library=library)
        library.search("Road")
        rows = bridge.property("searchPlaylists")
        assert rows[0]["playlistId"] == a.playlist_id
        assert rows[0]["name"] == "Road Trip Long"
        bridge.dispose()

    def test_search_playlist_supports_open_intent_chain(self, tmp_path):
        """M9-R1 readiness: search row playlistId → openPlaylist works."""
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("Road Trip")
        nav = NavigationService()
        coord = PlaylistNavigationCoordinator(service, nav)
        bridge, _, _ = _make_bridge(service, library=library)
        library.search("Road")
        row = bridge.property("searchPlaylists")[0]
        coord.open_playlist(row["playlistId"])
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)
        bridge.dispose()


class TestBridgeDeleteSelection:
    def test_delete_selected_clears_bridge_state(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        service.delete_playlist(a.playlist_id)  # service-level delete
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_delete_selected_via_bridge_slot(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        bridge.delete_playlist(a.playlist_id)
        assert bridge.property("selectedPlaylistId") == ""
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_delete_other_keeps_selection(self, tmp_path):
        library, queue, _, _ = _tracks(tmp_path)
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        bridge, _, _ = _make_bridge(service, library=library)
        bridge.open_playlist(a.playlist_id)
        service.delete_playlist(b.playlist_id)
        assert bridge.property("selectedPlaylistId") == a.playlist_id
        bridge.dispose()


class TestM4R1FinalSealPlaylistTrack:
    """P1-03: Playlist Detail row activation → PLAYLIST context."""

    def _world(self):
        from michi.application.playback_service import PlaybackService
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.playlist_playback_coordinator import (
            PlaylistPlaybackCoordinator,
        )
        from michi.application.queue_service import QueueService

        audio = FakeAudioPort()
        playback = PlaybackService(audio)
        queue = QueueService()
        session = PlaybackSessionService(playback, queue)
        session.start()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        nav = NavigationService()
        service.set_on_playlist_deleted(nav.forget_playlist)
        nav_coord = PlaylistNavigationCoordinator(service, nav)
        pcoord = PlaylistPlaybackCoordinator(service, session, queue)
        bridge = PlaylistsBridge(
            service,
            playlist_navigation=nav_coord,
            navigation_service=nav,
            playback_coordinator=pcoord,
        )
        return service, bridge, session, queue, audio

    def test_pl01_pl02_pl03_tracklist_signal_exists(self):
        """PlaylistTrackList exposes playTrackRequested; mouse/keyboard rows
        emit it (QML surface inspected statically)."""
        from pathlib import Path

        qml = Path(
            "src/michi/presentation/qml/playlists/PlaylistTrackList.qml"
        ).read_text()
        assert "signal playTrackRequested(int index)" in qml
        # PL-FINAL-14: mouse + keyboard emit the CANONICAL index
        # (filter-safe) — nunca el índice de la lista filtrada.
        assert "root.playTrackRequested(trackItem.canonicalIndex)" in qml
        assert "trackItem.canInteract" in qml
        assert "Keys.onReturnPressed" in qml
        assert "Keys.onEnterPressed" in qml

    def test_pl04_detail_view_wires_intent(self):
        from pathlib import Path

        qml = Path(
            "src/michi/presentation/qml/playlists/PlaylistDetailView.qml"
        ).read_text()
        # R4-11: el Detail re-emite el INTENT; ContentHost traduce al Bridge
        # (nunca child→bridge directo).
        assert "onPlayTrackRequested: index => root.playTrackRequested(index)" in qml
        assert (
            "onPlayTrackRequested: index => playlists.play_playlist_track(index)"
            not in qml
        )

    def test_pl05_click_index_2_playlist_context(self):
        from pathlib import Path

        service, bridge, session, queue, audio = self._world()
        p = service.create_playlist("P")
        for path in ("/m/P0.flac", "/m/P1.flac", "/m/P2.flac", "/m/P3.flac"):
            service.add_track(p.playlist_id, Path(path))
        bridge.open_playlist(p.playlist_id)
        bridge.play_playlist_track(2)
        audio.trigger_media_accepted(Path("/m/P2.flac"))
        assert session.state.context_type.name == "PLAYLIST"
        assert session.state.source_id == p.playlist_id
        assert session.state.current_index == 2
        assert session.state.current_entry.file_path == Path("/m/P2.flac")

    def test_pl06_queue_populated_playlist_click_queue_unchanged(self):
        from pathlib import Path

        service, bridge, session, queue, audio = self._world()
        queue.add(Path("/pre/Q1.flac"))
        queue.add(Path("/pre/Q2.flac"))
        before = [t.file_path for t in queue.state.tracks]
        p = service.create_playlist("P")
        for path in ("/m/P0.flac", "/m/P1.flac"):
            service.add_track(p.playlist_id, Path(path))
        bridge.open_playlist(p.playlist_id)
        bridge.play_playlist_track(1)
        audio.trigger_media_accepted(Path("/m/P1.flac"))
        assert [t.file_path for t in queue.state.tracks] == before  # unchanged

    def test_pl07_more_options_does_not_trigger_playback(self):
        """The More Options button opens the menu only — never playback."""
        from pathlib import Path

        qml = Path(
            "src/michi/presentation/qml/playlists/PlaylistTrackList.qml"
        ).read_text()
        # the options button calls trackMenu.popup() — not playTrackRequested
        assert "onClicked: trackMenu.popup()" in qml
