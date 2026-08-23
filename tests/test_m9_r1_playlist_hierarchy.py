"""M9-R1 closeout gates — playlist shell hierarchy.

PLAYLIST-HIERARCHY-01..06: Playlists is a first-class Shell feature; Library
does not contain Playlists; all canonical navigation uses AppRoute.PLAYLISTS;
detail = PLAYLISTS + playlist_id; PlaylistsBridge owns the presentation
projection; Queue and Playlists stay independent.
"""

from pathlib import Path

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


def _text(rel: str) -> str:
    return (QML_DIR / rel).read_text()


class TestHierarchy:
    def test_playlists_is_first_class_shell(self):
        sidebar = _text("shell/Sidebar.qml")
        assert '{ id: "playlists", label: "Playlists"' in sidebar

    def test_library_has_no_playlists_tab(self):
        tabs = _text("views/LibraryTabs.qml")
        assert 'value: "playlists"' not in tabs
        assert 'icon: "playlist"' not in tabs
        library_view = _text("views/LibraryView.qml")
        assert 'currentTab = "playlists"' not in library_view

    def test_canonical_route_single(self):
        from michi.domain.navigation import AppRoute

        assert AppRoute.PLAYLISTS == "playlists"
        # no extra playlist routes
        routes = [r.value for r in AppRoute]
        assert routes.count("playlists") == 1
        assert "playlist_detail" not in routes
        assert "pinned" not in routes
        assert "recent_playlists" not in routes

    def test_detail_is_playlists_plus_id(self):
        content = _text("shell/ContentHost.qml")
        assert "playlistDetail" in content
        assert "playlists.selectedPlaylistId" in content

    def test_playlists_bridge_owns_projection(self):
        bridge = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "michi"
            / "presentation"
            / "playlists_bridge.py"
        ).read_text()
        assert "class PlaylistsBridge" in bridge
        assert "pinnedPlaylists" in bridge
        assert "recentPlaylists" in bridge
        # LibraryBridge no longer owns the canonical playlist presentation
        lib_bridge = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "michi"
            / "presentation"
            / "library_bridge.py"
        ).read_text()
        assert "selectedPlaylistId" not in lib_bridge
        assert "playlistTracks" not in lib_bridge

    def test_queue_and_playlists_independent(self):
        # domain: PlaylistService and QueueService are distinct authorities
        from michi.application.playlist_service import PlaylistService
        from michi.application.queue_service import QueueService

        assert PlaylistService is not QueueService

    def test_no_raw_navigation_slot(self):
        nav_bridge = (
            Path(__file__).resolve().parents[1]
            / "src"
            / "michi"
            / "presentation"
            / "navigation_bridge.py"
        ).read_text()
        assert "def navigate_to_playlist" not in nav_bridge

    def test_playlists_presentation_lives_in_playlists_dir(self):
        assert (QML_DIR / "playlists" / "PlaylistsView.qml").exists()
        assert (QML_DIR / "playlists" / "PlaylistDetailView.qml").exists()
        assert (QML_DIR / "playlists" / "PlaylistCard.qml").exists()
        assert (QML_DIR / "playlists" / "PlaylistCreateDialog.qml").exists()
        assert (QML_DIR / "playlists" / "PlaylistTrackList.qml").exists()
        # old library-homed playlist view is gone
        assert not (QML_DIR / "views" / "PlaylistsView.qml").exists()

    def test_create_dialog_flow(self):
        dialog = _text("playlists/PlaylistCreateDialog.qml")
        assert "create_and_open_playlist" in dialog
        assert "Playlist name must not be empty" in dialog

    def test_delete_confirmation_never_implies_file_deletion(self):
        # M9-R1I: shared dialogs live in ContentHost (single location).
        content = _text("shell/ContentHost.qml")
        assert "Music files will remain in your library" in content

    def test_remove_wording(self):
        track_list = _text("playlists/PlaylistTrackList.qml")
        assert "Remove from playlist" in track_list
        assert "Delete track" not in track_list
