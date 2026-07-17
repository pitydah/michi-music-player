"""E2E workflow: Playlists + History — all bridge interactions."""
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
        assert hasattr(pl, 'refresh')
        assert hasattr(pl, 'getPlaylistDetail')

    def test_playlists_get_by_id(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        result = pl.getPlaylistDetail(1)
        assert isinstance(result, dict)
        assert "ok" in result

    def test_playlists_detail(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        result = pl.getPlaylistDetail(1)
        assert isinstance(result, dict)
        assert "ok" in result

    def test_playlists_navigation(self, nav):
        nav.navigate("playlists")
        assert nav.currentRoute == "playlists", (
            f"Expected 'playlists', got '{nav.currentRoute}'"
        )

    def test_history_bridge_exists(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None, "HistoryBridge should exist"

    def test_history_get(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None
        result = hb.refresh()
        assert isinstance(result, dict)
        assert "ok" in result

    def test_history_clear(self, all_bridges):
        hb = all_bridges.get("history")
        assert hb is not None
        result = hb.clearHistory()
        assert isinstance(result, dict)
        assert result.get("ok") is True

    def test_playlists_bridge_methods_return_dicts(self, all_bridges):
        pl = all_bridges.get("playlists")
        assert pl is not None
        for method_name in ("listPlaylists", "getPlaylist", "getPlaylistDetail"):
            method = getattr(pl, method_name, None)
            if method:
                arg = 1 if method_name != "listPlaylists" else None
                result = method(arg) if arg is not None else method()
                assert isinstance(result, dict), (
                    f"{method_name} should return dict, got {type(result).__name__}"
                )
