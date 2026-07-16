"""Workflow: Startup → Home → Library."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("home"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_dimension("service_wiring"),
]


class TestStartupHomeLibrary:
    def test_bootstrap_reads_ready(self, bootstrap):
        assert bootstrap._has_built, "Bootstrap should have built"
        assert bootstrap._has_started, "Bootstrap should have started"

    def test_home_bridge_exists(self, bootstrap):
        hb = bootstrap._bridges.get("home")
        assert hb is not None, "HomeBridge should exist"

    def test_library_bridge_exists(self, bootstrap):
        lb = bootstrap._bridges.get("library")
        assert lb is not None, "LibraryBridge should exist"

    def test_library_service_exists(self, bootstrap):
        svc = bootstrap.container.get("library_service")
        assert svc is not None, "LibraryService should exist"

    def test_songs_service_exists(self, bootstrap):
        svc = bootstrap.container.get("songs_service")
        assert svc is not None, "SongsService should exist"

    def test_navigation_bridge_exists(self, bootstrap):
        nb = bootstrap._bridges.get("navigation")
        assert nb is not None, "NavigationBridge should exist"

    def test_playback_bridge_exists(self, bootstrap):
        pb = bootstrap._bridges.get("playback")
        assert pb is not None, "PlaybackBridge should exist"
