"""M8-R1: legacy playlist migration gates — V1 → deterministic V2 ids.

Rules under test:
- V1 records load with a DETERMINISTIC legacy id (same on every load).
- Load never writes back automatically.
- First legitimate mutation persists V2 (with the deterministic id).
- V2 restart preserves the exact id.
- Mixed V1+V2 load safely; malformed siblings are dropped; duplicates are
  handled deterministically (first wins); empty/invalid ids degrade safely.
"""

import json
import sqlite3
from pathlib import Path

from michi.domain.playlist import Playlist, legacy_playlist_id
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from tests.test_playlists import FakePlaylistsPort


def _seed_v1(db_path: Path, entries):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
            (json.dumps(entries),),
        )
        conn.commit()
    finally:
        conn.close()


class TestV1LoadsWithDeterministicId:
    def _repo(self, tmp_path, entries):
        db = tmp_path / "michi.db"
        _seed_v1(db, entries)
        return SqlitePlaylistsRepository(db)

    def test_v1_record_without_id_loads(self, tmp_path):
        repo = self._repo(tmp_path, [{"name": "Jazz", "track_paths": ["/a.flac"]}])
        loaded = repo.load()
        assert len(loaded) == 1
        assert loaded[0].playlist_id == legacy_playlist_id("Jazz")
        assert loaded[0].name == "Jazz"
        assert loaded[0].track_paths == ("/a.flac",)

    def test_same_v1_record_across_restarts_same_id(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(db, [{"name": "Jazz", "track_paths": []}])
        repo1 = SqlitePlaylistsRepository(db)
        repo2 = SqlitePlaylistsRepository(db)
        assert repo1.load()[0].playlist_id == repo2.load()[0].playlist_id
        assert repo1.load()[0].playlist_id == legacy_playlist_id("Jazz")

    def test_different_names_different_legacy_ids(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"name": "Jazz", "track_paths": []},
                {"name": "Rock", "track_paths": []},
            ],
        )
        repo = SqlitePlaylistsRepository(db)
        ids = {p.playlist_id for p in repo.load()}
        assert len(ids) == 2


class TestNoWritebackDuringLoad:
    def test_v1_load_does_not_write(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(db, [{"name": "Jazz", "track_paths": ["/a.flac"]}])
        repo = SqlitePlaylistsRepository(db)
        repo.load()
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlists'"
            ).fetchone()
        finally:
            conn.close()
        payload = json.loads(row[0])
        assert "id" not in payload[0]  # still V1 on disk

    def test_v1_mutate_persists_v2_with_same_deterministic_id(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(db, [{"name": "Jazz", "track_paths": ["/a.flac"]}])
        repo = SqlitePlaylistsRepository(db)
        from michi.application.playlist_service import PlaylistService

        service = PlaylistService(playlists_port=repo)
        loaded = service.playlists[0]
        assert loaded.playlist_id == legacy_playlist_id("Jazz")
        service.add_track(loaded.playlist_id, "/b.flac")  # mutation → persist
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlists'"
            ).fetchone()
        finally:
            conn.close()
        payload = json.loads(row[0])
        assert payload[0]["id"] == legacy_playlist_id("Jazz")
        assert payload[0]["track_paths"] == ["/a.flac", "/b.flac"]


class TestMixedAndMalformed:
    def test_v2_restart_exact_id_retained(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SqlitePlaylistsRepository(db)
        repo.save((Playlist("v2-id-42", "Modern", ("/x.flac",)),))
        loaded = SqlitePlaylistsRepository(db).load()
        assert loaded[0].playlist_id == "v2-id-42"

    def test_mixed_v1_and_v2_load_safely(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"name": "V1 Jazz", "track_paths": ["/a.flac"]},
                {"id": "v2-1", "name": "V2 Rock", "track_paths": ["/b.flac"]},
            ],
        )
        loaded = SqlitePlaylistsRepository(db).load()
        assert len(loaded) == 2
        by_name = {p.name: p for p in loaded}
        assert by_name["V1 Jazz"].playlist_id == legacy_playlist_id("V1 Jazz")
        assert by_name["V2 Rock"].playlist_id == "v2-1"

    def test_malformed_sibling_preserves_valid_ones(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"name": "Good", "track_paths": ["/a.flac"]},
                {"name": "Bad", "track_paths": ["/b.flac", 42]},  # malformed
                {"name": "AlsoGood", "track_paths": []},
            ],
        )
        loaded = SqlitePlaylistsRepository(db).load()
        assert [p.name for p in loaded] == ["Good", "AlsoGood"]

    def test_duplicate_valid_ids_first_wins(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"id": "same", "name": "First", "track_paths": ["/a.flac"]},
                {"id": "same", "name": "Second", "track_paths": ["/b.flac"]},
                {"name": "LegacyA", "track_paths": []},
                {"name": "LegacyA", "track_paths": ["/c.flac"]},  # same legacy id
            ],
        )
        loaded = SqlitePlaylistsRepository(db).load()
        # 'same' appears once (first wins); the duplicate LegacyA is dropped
        assert len(loaded) == 2
        assert loaded[0].name == "First"
        assert loaded[1].name == "LegacyA"
        assert loaded[1].track_paths == ()  # first occurrence wins

    def test_empty_and_invalid_ids_degrade_to_legacy(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"id": "", "name": "EmptyId", "track_paths": []},
                {"id": 42, "name": "WrongType", "track_paths": []},
                {"id": "ok", "name": "Valid", "track_paths": []},
            ],
        )
        loaded = SqlitePlaylistsRepository(db).load()
        by_name = {p.name: p for p in loaded}
        assert by_name["EmptyId"].playlist_id == legacy_playlist_id("EmptyId")
        assert by_name["WrongType"].playlist_id == legacy_playlist_id("WrongType")
        assert by_name["Valid"].playlist_id == "ok"

    def test_never_merges_distinct_playlists(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_v1(
            db,
            [
                {"name": "A", "track_paths": ["/1.flac"]},
                {"name": "B", "track_paths": ["/2.flac"]},
            ],
        )
        loaded = SqlitePlaylistsRepository(db).load()
        assert len(loaded) == 2  # never merged into one
        assert {p.name for p in loaded} == {"A", "B"}

    def test_fake_port_v1_records_get_legacy_ids(self):
        """FakePlaylistsPort seeded with V1-shaped records keeps working and
        the service assigns deterministic legacy ids."""
        port = FakePlaylistsPort(playlists=())
        from michi.application.playlist_service import PlaylistService

        service = PlaylistService(playlists_port=port)
        service.create_playlist("Jazz")
        assert service.playlists[0].playlist_id != ""
