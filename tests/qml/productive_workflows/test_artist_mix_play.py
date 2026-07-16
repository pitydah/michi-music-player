"""Workflow: Artist → Mix → Play."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestArtistMixPlay:
    def test_artist_play_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("artist.play")
        assert a is not None, "artist.play action exists"

    def test_artist_service_exists(self, bootstrap):
        svc = bootstrap.container.get("artist_service")
        assert svc is not None
        assert hasattr(svc, 'play_artist')
        assert hasattr(svc, 'create_artist_mix')
        assert hasattr(svc, 'create_playlist_from_artist')
        assert hasattr(svc, 'analyze_artist_discography')

    def test_mix_generate_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        a = ar.get("mix.generate")
        assert a is not None, "mix.generate action exists"

    def test_mix_service_exists(self, bootstrap):
        svc = bootstrap.container.get("mix_service")
        assert svc is not None
        assert hasattr(svc, 'generate')
        assert hasattr(svc, 'cancel')
