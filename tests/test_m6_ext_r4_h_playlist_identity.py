"""M6-EXT-R4-H — playlist stable TrackId membership + V3 persistence seam."""

import json

from michi.application.playlist_service import PlaylistService
from michi.domain.playlist import (
    Playlist,
    PlaylistTrackReference,
    legacy_playlist_id,
)
from michi.infrastructure.playlists import (
    PLAYLIST_PERSISTENCE_VERSION,
    SqlitePlaylistsRepository,
)


class _MemoryPlaylistsPort:
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
                "version": PLAYLIST_PERSISTENCE_VERSION,
                "id": p.playlist_id,
                "name": p.name,
                "tracks": [
                    {"track_id": ref.track_id, "fallback_path": ref.fallback_path}
                    for ref in p.references()
                ],
            }
            for p in playlists
        ]

    def load_navigation(self):
        from michi.domain.playlist import PlaylistNavigationState

        return PlaylistNavigationState()

    def save_navigation(self, state) -> None:
        self.nav = state

    def save_playlists_with_navigation(self, playlists, navigation):

        self.save(playlists)

        self.save_navigation(navigation)


class TestPlaylistDomain:
    def test_playlist_references_align_both_collections(self) -> None:
        playlist = Playlist(
            playlist_id="p1",
            name="Mix",
            track_ids=("T1", "T2"),
            track_paths=("/a.flac", "/b.flac"),
        )
        refs = playlist.references()
        assert refs == (
            PlaylistTrackReference(track_id="T1", fallback_path="/a.flac"),
            PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
        )

    def test_legacy_path_only_record_aligns_with_empty_ids(self) -> None:
        playlist = Playlist(playlist_id="p1", name="Old", track_paths=("/a.flac",))
        assert playlist.references() == (
            PlaylistTrackReference(track_id="", fallback_path="/a.flac"),
        )


class TestV3Persistence:
    def test_save_emits_v3_shape(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        playlist = Playlist(
            playlist_id="p1",
            name="Mix",
            track_ids=("T1", "T2"),
            track_paths=("/a.flac", "/b.flac"),
        )
        repo.save((playlist,))
        raw = repo._load_raw("playlists")
        assert raw[0]["version"] == 3
        assert raw[0]["tracks"] == [
            {"track_id": "T1", "fallback_path": "/a.flac"},
            {"track_id": "T2", "fallback_path": "/b.flac"},
        ]
        # Derived compatibility projection of the SAME membership.
        assert raw[0]["track_paths"] == ["/a.flac", "/b.flac"]

    def test_v3_load_restores_ids_and_paths(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        repo._save_raw(
            "playlists",
            json.dumps(
                [
                    {
                        "version": 3,
                        "id": "p1",
                        "name": "Mix",
                        "tracks": [
                            {"track_id": "T1", "fallback_path": "/a.flac"},
                            {"track_id": "T2", "fallback_path": ""},
                        ],
                    }
                ]
            ),
        )
        playlists = repo.load()
        assert playlists == (
            Playlist(
                playlist_id="p1",
                name="Mix",
                track_ids=("T1", "T2"),
                track_paths=("/a.flac", ""),
            ),
        )

    def test_v2_load_keeps_paths_with_empty_ids(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        repo._save_raw(
            "playlists",
            json.dumps([{"id": "p1", "name": "Old", "track_paths": ["/a.flac"]}]),
        )
        playlists = repo.load()
        assert playlists[0].track_ids == ()
        assert playlists[0].track_paths == ("/a.flac",)

    def test_v1_load_derives_deterministic_id(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        repo._save_raw(
            "playlists", json.dumps([{"name": "Legacy", "track_paths": ["/a.flac"]}])
        )
        playlists = repo.load()
        assert playlists[0].playlist_id == legacy_playlist_id("Legacy")

    def test_malformed_v3_track_rejects_whole_entry(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        repo._save_raw(
            "playlists",
            json.dumps(
                [
                    {
                        "version": 3,
                        "id": "p1",
                        "name": "Bad",
                        "tracks": [{"fallback_path": "/a.flac"}],  # missing track_id
                    },
                    {"id": "p2", "name": "Good", "track_paths": ["/b.flac"]},
                ]
            ),
        )
        playlists = repo.load()
        assert [p.playlist_id for p in playlists] == ["p2"]


class TestPlaylistServiceIdentityOps:
    def test_create_with_references_persists_ids(self) -> None:
        port = _MemoryPlaylistsPort()
        service = PlaylistService(playlists_port=port)
        playlist = service.create_playlist_with_references(
            "Mix",
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/a.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
            ],
        )
        assert playlist.track_ids == ("T1", "T2")
        assert playlist.track_paths == ("/a.flac", "/b.flac")
        assert port.payload[0]["tracks"][0] == {
            "track_id": "T1",
            "fallback_path": "/a.flac",
        }

    def test_add_track_references_dedupes_by_id(self) -> None:
        service = PlaylistService(playlists_port=_MemoryPlaylistsPort())
        playlist = service.create_playlist_with_references(
            "Mix", [PlaylistTrackReference(track_id="T1", fallback_path="/a.flac")]
        )
        added = service.add_track_references(
            playlist.playlist_id,
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/moved.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
            ],
        )
        assert added == 1
        updated = service.get_playlist(playlist.playlist_id)
        assert updated.track_ids == ("T1", "T2")
        assert updated.track_paths == ("/a.flac", "/b.flac")

    def test_remove_and_move_keep_both_collections_aligned(self) -> None:
        service = PlaylistService(playlists_port=_MemoryPlaylistsPort())
        playlist = service.create_playlist_with_references(
            "Mix",
            [
                PlaylistTrackReference(track_id="T1", fallback_path="/a.flac"),
                PlaylistTrackReference(track_id="T2", fallback_path="/b.flac"),
                PlaylistTrackReference(track_id="T3", fallback_path="/c.flac"),
            ],
        )
        service.move_track(playlist.playlist_id, 0, 2)
        updated = service.get_playlist(playlist.playlist_id)
        assert updated.track_ids == ("T2", "T3", "T1")
        assert updated.track_paths == ("/b.flac", "/c.flac", "/a.flac")
        service.remove_track(playlist.playlist_id, 1)
        updated = service.get_playlist(playlist.playlist_id)
        assert updated.track_ids == ("T2", "T1")
        assert updated.track_paths == ("/b.flac", "/a.flac")

    def test_legacy_path_wrapper_still_works(self) -> None:
        service = PlaylistService(playlists_port=_MemoryPlaylistsPort())
        playlist = service.create_playlist_with_tracks("Old", ["/a.flac"])
        service.add_tracks(playlist.playlist_id, ["/b.flac"])
        updated = service.get_playlist(playlist.playlist_id)
        assert updated.track_paths == ("/a.flac", "/b.flac")
        assert updated.track_ids == ("", "")

    def test_load_from_v3_roundtrip_via_repo(self, tmp_path) -> None:
        repo = SqlitePlaylistsRepository(tmp_path / "michi.db")
        service = PlaylistService(playlists_port=repo)
        playlist = service.create_playlist_with_references(
            "Mix", [PlaylistTrackReference(track_id="T9", fallback_path="/x.flac")]
        )
        del service
        reloaded = PlaylistService(playlists_port=repo)
        loaded = reloaded.get_playlist(playlist.playlist_id)
        assert loaded.track_ids == ("T9",)
        assert loaded.track_paths == ("/x.flac",)
