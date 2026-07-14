from __future__ import annotations

from core.assistant_gateways import ProductionPlaylistServiceGateway


class FakePlaylistService:
    def __init__(self) -> None:
        self._playlists: dict[int, dict] = {}
        self._next_id = 1

    def get_all_playlists(self) -> list[dict]:
        return list(self._playlists.values())

    def get_playlists(self) -> list[dict]:
        return list(self._playlists.values())

    def get_playlist_items(self, pid: int) -> list:
        pl = self._playlists.get(pid)
        return pl.get("tracks", []) if pl else []

    def create_playlist(self, name: str) -> int:
        pid = self._next_id
        self._next_id += 1
        self._playlists[pid] = {"id": pid, "name": name, "tracks": []}
        return pid

    def add_track_to_playlist(self, pid: int, track_id: str) -> None:
        pl = self._playlists.get(pid)
        if pl:
            pl["tracks"].append(track_id)


class TestProductionPlaylistServiceGateway:
    def setup_method(self) -> None:
        self.ps = FakePlaylistService()
        self.gw = ProductionPlaylistServiceGateway(self.ps)

    def test_list_playlists_empty(self) -> None:
        r = self.gw.list_playlists()
        assert r["ok"] is True
        assert r["total"] == 0

    def test_create_playlist(self) -> None:
        r = self.gw.create_playlist("Test")
        assert r["ok"] is True
        assert r["playlist"]["name"] == "Test"
        assert "id" in r["playlist"]

    def test_list_playlists_after_create(self) -> None:
        self.gw.create_playlist("A")
        self.gw.create_playlist("B")
        r = self.gw.list_playlists()
        assert r["total"] == 2

    def test_create_playlist_with_tracks(self) -> None:
        r = self.gw.create_playlist("WithTracks", ["1", "2", "3"])
        assert r["ok"] is True

    def test_add_to_playlist(self) -> None:
        create = self.gw.create_playlist("Test")
        pid = int(create["playlist"]["id"])
        r = self.gw.add_to_playlist(str(pid), ["10"])
        assert r["ok"] is True
        assert r["added"] >= 1

    def test_get_playlist(self) -> None:
        create = self.gw.create_playlist("Test")
        pid = create["playlist"]["id"]
        r = self.gw.get_playlist(pid)
        assert r["ok"] is True

    def test_unavailable(self) -> None:
        gw = ProductionPlaylistServiceGateway(None)
        r = gw.list_playlists()
        assert r["ok"] is False
