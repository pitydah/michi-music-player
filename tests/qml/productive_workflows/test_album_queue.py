"""Workflow: Album → Queue."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestAlbumQueue:
    def test_album_play_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("album.play")
        assert a is not None, "album.play action exists"

    def test_album_enqueue_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("album.enqueue")
        assert a is not None, "album.enqueue action exists"

    def test_album_service_exists(self, bootstrap):
        svc = bootstrap.container.get("album_service")
        assert svc is not None
        assert hasattr(svc, 'play_album')
        assert hasattr(svc, 'play_next_album')
        assert hasattr(svc, 'create_playlist_from_tracks')
        assert hasattr(svc, 'analyze_album_quality')
        assert hasattr(svc, 'navigate_to_album_by_title')
