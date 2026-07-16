"""Workflow: Playlist functions — create, rename, delete, add, remove, import, export."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playlists"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
    pytest.mark.qml_dimension("primary_interaction"),
]


class TestPlaylistFunctions:
    def test_playlist_create_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.create")
        assert a is not None and a.handler is not None

    def test_playlist_rename_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.rename")
        assert a is not None and a.handler is not None

    def test_playlist_delete_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.delete")
        assert a is not None and a.handler is not None

    def test_playlist_add_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.add")
        assert a is not None and a.handler is not None

    def test_playlist_remove_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.remove")
        assert a is not None and a.handler is not None

    def test_playlist_import_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.import")
        assert a is not None and a.handler is not None

    def test_playlist_export_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("playlist.export")
        assert a is not None and a.handler is not None

    def test_playlist_service_methods(self, bootstrap):
        svc = bootstrap.container.get("playlist_service")
        assert svc is not None
        assert hasattr(svc, 'create_playlist')
        assert hasattr(svc, 'rename_playlist')
        assert hasattr(svc, 'delete_playlist')
        assert hasattr(svc, 'add_track')
        assert hasattr(svc, 'remove_track')
        assert hasattr(svc, 'import_m3u')
        assert hasattr(svc, 'export_m3u')

    def test_playlists_bridge_exists(self, bootstrap):
        pb = bootstrap._bridges.get("playlists")
        assert pb is not None
