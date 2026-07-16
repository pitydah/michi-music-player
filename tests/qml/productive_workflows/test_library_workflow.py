"""Workflow: Library → Search → Select → Play — bridge interaction tests."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("library"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("library"),
]


class TestLibraryWorkflow:
    def test_navigate_to_library(self, bootstrap, engine):
        nav = bootstrap._bridges.get("navigation")
        assert nav is not None, "NavigationBridge should exist"
        nav.navigate("library")
        assert nav.currentRoute == "library"

    def test_library_bridge_search(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None, "LibraryBridge should exist"
        result = lib.search("test")
        assert isinstance(result, dict), "search() should return dict"
        assert "ok" in result or "error" in result or "results" in result

    def test_library_bridge_play_track(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None
        result = lib.play_song("1")
        assert isinstance(result, dict)

    def test_global_search_bridge(self, bootstrap):
        gs = bootstrap._bridges.get("global_search")
        assert gs is not None, "GlobalSearchBridge should exist"
        result = gs.search("test")
        assert isinstance(result, dict)

    def test_playback_bridge_controls(self, bootstrap):
        pb = bootstrap._bridges.get("playback")
        assert pb is not None, "PlaybackBridge should exist"
        result = pb.togglePlay()
        assert isinstance(result, dict)

    def test_library_loads_songs(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None
        result = lib.loadLibrary()
        assert isinstance(result, dict)
        if result.get("ok", True):
            songs = result.get("songs", result.get("results", []))
            assert isinstance(songs, (list, tuple))

    def test_library_sort(self, bootstrap):
        lib = bootstrap._bridges.get("library")
        assert lib is not None
        result = lib.sortBy("title")
        assert isinstance(result, dict)

    def test_queue_bridge_add(self, bootstrap):
        qb = bootstrap._bridges.get("queue")
        assert qb is not None, "QueueBridge should exist"
        pb = bootstrap._bridges.get("playback")
        if pb:
            result = pb.enqueueSong("1")
            assert isinstance(result, dict)

    def test_navigation_back_and_forward(self, bootstrap):
        nav = bootstrap._bridges.get("navigation")
        assert nav is not None
        nav.navigate("library")
        nav.navigate("home")
        assert nav.currentRoute == "home"
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "home"

    def test_workflow_search_select_play(self, bootstrap):
        gs = bootstrap._bridges.get("global_search")
        pb = bootstrap._bridges.get("playback")
        lib = bootstrap._bridges.get("library")
        nav = bootstrap._bridges.get("navigation")
        assert all(b is not None for b in (gs, pb, lib, nav))
        search_result = gs.search("test")
        assert isinstance(search_result, dict)
        nav.navigate("library")
        assert nav.currentRoute == "library"
        lib_result = lib.loadLibrary()
        assert isinstance(lib_result, dict)
        play_result = pb.togglePlay()
        assert isinstance(play_result, dict)
