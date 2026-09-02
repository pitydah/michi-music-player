"""M6-EXT-R4-H SEMANTIC INTEGRATION — playlist stable identity + persistence.

Adapted to the CANONICAL playlist architecture of main (PR #223/#229):
``Playlist.track_paths`` is the membership/order authority; persistence is
the V2 shape {"id", "name", "track_paths"} with deterministic legacy ids.
The R4-era ``PlaylistTrackReference``/V3 seam was superseded by main's
design. Invariants preserved without weakening assertions:
- deterministic identity (playlist_id survives restarts);
- membership/order round-trip through the repository;
- legacy V1 payloads decode to deterministic ids without writeback;
- dedupe of duplicate members; remove/move keep collections aligned.
"""

from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import Playlist, legacy_playlist_id
from michi.infrastructure.playlists import (
    SqlitePlaylistsRepository,
)


class _MemoryPlaylistsPort:
    """V2-shaped in-memory persistence (main's canonical shape)."""

    def __init__(self) -> None:
        self.payload: list[dict] = []
        self.nav = {}

    def load(self) -> tuple[Playlist, ...]:
        from michi.infrastructure.playlists import _decode_playlist_entry

        return tuple(
            playlist
            for entry in self.payload
            if (playlist := _decode_playlist_entry(entry)) is not None
        )

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        self.payload = [
            {
                "id": p.playlist_id,
                "name": p.name,
                "track_paths": list(p.track_paths),
            }
            for p in playlists
        ]

    def save_state(self, playlists, navigation) -> None:
        self.save(playlists)

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save_navigation(self, state) -> None:
        del state


class TestV2Persistence:
    def test_save_emits_v2_shape(self) -> None:
        port = _MemoryPlaylistsPort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        assert port.payload[0]["id"] == playlist.playlist_id
        assert port.payload[0]["name"] == "Mix"
        assert port.payload[0]["track_paths"] == ["/a.flac"]

    def test_roundtrip_restores_ids_and_paths(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac"])
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.playlist_id == playlist.playlist_id, "identidad estable"
        assert reloaded.track_paths == ("/a.flac", "/b.flac"), "orden preservado"


class TestLegacyV1Decode:
    def test_legacy_v1_payload_decodes_to_deterministic_id(self) -> None:
        """V1 {"name", "track_paths"} → id determinístico (legacy_playlist_id),
        sin writeback en load."""
        port = _MemoryPlaylistsPort()
        port.payload = [{"name": "Old Mix", "track_paths": ["/x.flac"]}]
        service = PlaylistService(playlists_port=port)
        loaded = service._playlists
        assert len(loaded) == 1
        playlist = loaded[0]
        assert playlist.playlist_id == legacy_playlist_id("Old Mix")
        # Load no escribió de vuelta.
        assert port.payload[0] == {"name": "Old Mix", "track_paths": ["/x.flac"]}


class TestPlaylistServiceIdentityOps:
    def test_add_tracks_dedupes(self) -> None:
        service = PlaylistService(playlists_port=_MemoryPlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        added, already = service.add_tracks(
            playlist.playlist_id, ["/b.flac", "/a.flac", "/b.flac"]
        )
        assert (added, already) == (1, 1)
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/a.flac",
            "/b.flac",
        )

    def test_remove_and_move_keep_order_aligned(self) -> None:
        service = PlaylistService(playlists_port=_MemoryPlaylistsPort())
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac", "/b.flac", "/c.flac"])
        assert service.move_track(playlist.playlist_id, 2, 0)
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/c.flac",
            "/a.flac",
            "/b.flac",
        )
        assert service.remove_track(playlist.playlist_id, 1)
        assert service.get_playlist(playlist.playlist_id).track_paths == (
            "/c.flac",
            "/b.flac",
        )

    def test_v2_roundtrip_via_repo(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db_path)
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist("Mix")
        service.add_tracks(playlist.playlist_id, ["/a.flac"])
        service.rename_playlist(playlist.playlist_id, "Renamed")
        reloaded = PlaylistService(
            playlists_port=SqlitePlaylistsRepository(db_path)
        ).get_playlist(playlist.playlist_id)
        assert reloaded is not None
        assert reloaded.name == "Renamed"
        assert reloaded.track_paths == ("/a.flac",)
