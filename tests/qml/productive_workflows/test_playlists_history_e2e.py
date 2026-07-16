"""E2E workflow: Playlists + History — bridge interactions."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("playlists"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("playlists"),
]


class TestPlaylistsHistoryE2E:
    def test_playlists_bridge_exists(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None, "PlaylistsBridge should exist"

    def test_playlists_list(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        result = pl.listPlaylists()
        assert isinstance(result, dict)

    def test_playlists_get(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        result = pl.getPlaylist(1)
        assert isinstance(result, dict)

    def test_playlists_detail(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        result = pl.getPlaylistDetail(1)
        assert isinstance(result, dict)

    def test_history_bridge_exists(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None, "HistoryBridge should exist"

    def test_history_get(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None
        result = hb.getHistory()
        assert isinstance(result, (list, tuple))

    def test_history_clear(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None
        result = hb.clearHistory()
        assert isinstance(result, dict)

    def test_playlists_navigation(self, nav):
        nav.navigate("playlists")
        assert nav.currentRoute == "playlists", (
            f"Expected 'playlists', got '{nav.currentRoute}'"
        )
