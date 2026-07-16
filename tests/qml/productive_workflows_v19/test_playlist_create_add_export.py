"""Workflow: Playlist → Create → Add → Export."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("playlists"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestPlaylistCreateExport:
    def test_playlist_create_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        for aid in ("playlist.create", "playlist.rename", "playlist.delete",
                    "playlist.add", "playlist.remove", "playlist.import", "playlist.export"):
            a = ar.find(aid)
            assert a is not None and a.handler is not None, f"{aid} handler"

    def test_playlist_service_methods(self, bootstrap):
        svc = bootstrap.container.get("playlist_service")
        assert svc is not None
        assert hasattr(svc, 'create_playlist')
        assert hasattr(svc, 'rename_playlist')
        assert hasattr(svc, 'delete_playlist')
        assert hasattr(svc, 'add_track')
        assert hasattr(svc, 'import_m3u')
        assert hasattr(svc, 'export_m3u')
