"""Workflow: Album and Artist functions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestAlbumFunctions:
    def test_album_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("album.play")
        assert a is not None and a.handler is not None

    def test_album_enqueue_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("album.enqueue")
        assert a is not None and a.handler is not None

    def test_album_add_to_playlist_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("album.add_to_playlist")
        assert a is not None and a.handler is not None

    def test_album_service_methods(self, bootstrap):
        svc = bootstrap.container.get("album_service")
        assert svc is not None
        assert hasattr(svc, 'play_album')
        assert hasattr(svc, 'queue_album')


class TestArtistFunctions:
    def test_artist_play_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("artist.play")
        assert a is not None and a.handler is not None

    def test_artist_shuffle_action(self, bootstrap):
        ar = bootstrap._bridges.get("action_registry")
        a = ar.find("artist.shuffle")
        assert a is not None and a.handler is not None

    def test_artist_service_methods(self, bootstrap):
        svc = bootstrap.container.get("artist_service")
        assert svc is not None
        assert hasattr(svc, 'play_artist')
