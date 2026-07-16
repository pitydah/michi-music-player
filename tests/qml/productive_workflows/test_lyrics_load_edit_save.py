"""Workflow: Lyrics → Load → Edit → Save."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("lyrics"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestLyrics:
    def test_lyrics_service_methods(self, bootstrap):
        svc = bootstrap.container.get("lyrics_service")
        assert svc is not None
        assert hasattr(svc, 'get_lyrics')
        assert hasattr(svc, 'save_lyrics')
        assert hasattr(svc, 'health')

    def test_lyrics_bridge_exists(self, bootstrap):
        lb = bootstrap._bridges.get("lyrics")
        assert lb is not None
