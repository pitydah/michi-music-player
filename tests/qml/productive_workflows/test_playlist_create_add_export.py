"""Workflow: Playlist → Create → Add → Export."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("playlists"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestPlaylistCreateExport:
    def test_playlist_create_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        for aid in ("playlist.create", "playlist.rename", "playlist.delete",
                    "playlist.add", "playlist.remove", "playlist.import", "playlist.export"):
            a = ar.get(aid)
            assert a is not None, f"{aid} action exists"

    def test_playlist_service_methods(self, bootstrap):
        svc = bootstrap.container.get("playlist_service")
        assert svc is not None
        assert hasattr(svc, 'create_playlist')
        assert hasattr(svc, 'rename_playlist')
        assert hasattr(svc, 'delete_playlist')
        assert hasattr(svc, 'add_track')
        assert hasattr(svc, 'import_m3u')
        assert hasattr(svc, 'export_m3u')

    def test_qtest_navigate_playlists(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item, wait_for_property
        nav.navigate("playlists")
        assert nav.currentRoute == "playlists"
        pl_page = find_qml_item(root_window, "playlistsPage")
        assert pl_page is not None, "playlistsPage not found"
        create_btn = find_qml_item(root_window, "createPlaylistButton")
        assert create_btn is not None, "createPlaylistButton not found"
        qtest_click_item(create_btn, root_window)
        dialog = find_qml_item(root_window, "playlistEditorDialog")
        assert dialog is not None, "playlistEditorDialog should appear after clicking create"
        wait_for_property(dialog, "visible", True, timeout_ms=500)
        QTest.qWait(100)
        pl_bridge = all_bridges.get("playlists")
        assert pl_bridge is not None, "PlaylistsBridge should exist"
        pl_state = getattr(pl_bridge, '_state', '') or getattr(pl_bridge, 'state', '')
        assert pl_state != ""
