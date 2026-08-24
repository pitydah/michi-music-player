"""M8-R1F: startup navigation-metadata reconciliation gates.

Normalization is SAFE READ: stale ids pruned, duplicates first-wins, recent
bounded to MAX_RECENT_PLAYLISTS, order preserved — and NEVER written back
during load. Disk keeps stale payloads until the next legitimate mutation.
"""

import json
import sqlite3
from pathlib import Path

from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService
from michi.domain.playlist import (
    MAX_RECENT_PLAYLISTS,
    Playlist,
    PlaylistNavigationState,
)
from tests.test_playlists import FakePlaylistsPort


def _seed(db_path: Path, playlists, nav):
    conn = sqlite3.connect(str(db_path))
    try:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute(
            "INSERT INTO library_prefs(key, value) VALUES('playlists', ?)",
            (json.dumps(playlists),),
        )
        conn.execute(
            "INSERT INTO library_prefs(key, value) VALUES('playlist_navigation', ?)",
            (json.dumps(nav),),
        )
        conn.commit()
    finally:
        conn.close()


def _make(repo):
    _queue = QueueService()
    return PlaylistService(playlists_port=repo), _queue


class TestStartupNormalization:
    def test_stale_and_duplicate_ids_normalized_in_memory(self, tmp_path):
        db = tmp_path / "m.db"
        _seed(
            db,
            [
                {"id": "A", "name": "A", "track_paths": []},
                {"id": "B", "name": "B", "track_paths": []},
                {"id": "C", "name": "C", "track_paths": []},
            ],
            {
                "pinned_ids": ["B", "ghost", "B", "A"],
                "recent_ids": ["ghost", "C", "C", "A", "B", "X", "A"],
            },
        )
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        service, _ = _make(SqlitePlaylistsRepository(db))
        assert service.navigation.pinned_ids == ("B", "A")
        assert service.navigation.recent_ids == ("C", "A", "B")

    def test_recent_truncated_to_max(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        repo = SqlitePlaylistsRepository(tmp_path / "m.db")
        service, _ = _make(repo)
        ids = []
        for i in range(MAX_RECENT_PLAYLISTS + 5):
            p = service.create_playlist(f"P{i}")
            ids.append(p.playlist_id)
        # persist stale-heavy nav through the repo directly
        repo.save_navigation(
            PlaylistNavigationState(
                pinned_ids=(),
                recent_ids=tuple(ids + list(reversed(ids))),
            )
        )
        service2, _ = _make(SqlitePlaylistsRepository(tmp_path / "m.db"))
        assert len(service2.navigation.recent_ids) == MAX_RECENT_PLAYLISTS

    def test_fake_port_navigation_normalized(self):
        """Fake port with stale nav + valid playlists normalizes identically."""
        a = Playlist("A", "A")
        b = Playlist("B", "B")
        port = FakePlaylistsPort(
            playlists=(a, b),
            navigation=PlaylistNavigationState(
                pinned_ids=("ghost", "A", "A", "B"),
                recent_ids=("B", "ghost", "A"),
            ),
        )

        service = PlaylistService(playlists_port=port)
        assert service.navigation.pinned_ids == ("A", "B")
        assert service.navigation.recent_ids == ("B", "A")

    def test_empty_collection_keeps_navigation_empty(self, tmp_path):
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        db = tmp_path / "m.db"
        _seed(db, [], {"pinned_ids": ["ghost"], "recent_ids": ["ghost"]})
        service, _ = _make(SqlitePlaylistsRepository(db))
        assert service.navigation == PlaylistNavigationState()


class TestNoWritebackDuringLoad:
    def test_load_does_not_write_normalized_state(self, tmp_path):
        db = tmp_path / "m.db"
        _seed(
            db,
            [{"id": "A", "name": "A", "track_paths": []}],
            {"pinned_ids": ["ghost", "A"], "recent_ids": ["ghost"]},
        )
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        service, _ = _make(SqlitePlaylistsRepository(db))
        assert service.navigation.pinned_ids == ("A",)
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlist_navigation'"
            ).fetchone()
        finally:
            conn.close()
        raw = json.loads(row[0])
        assert raw == {"pinned_ids": ["ghost", "A"], "recent_ids": ["ghost"]}

    def test_next_legitimate_mutation_persists_normalized(self, tmp_path):
        db = tmp_path / "m.db"
        _seed(
            db,
            [{"id": "A", "name": "A", "track_paths": []}],
            {"pinned_ids": ["ghost", "A"], "recent_ids": ["ghost"]},
        )
        from michi.infrastructure.playlists import SqlitePlaylistsRepository

        service, _ = _make(SqlitePlaylistsRepository(db))
        service.pin_playlist("A")  # duplicate pin → no-op (already pinned)
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlist_navigation'"
            ).fetchone()
        finally:
            conn.close()
        raw = json.loads(row[0])
        assert raw == {"pinned_ids": ["ghost", "A"], "recent_ids": ["ghost"]}

        service.mark_recent("A")  # legitimate MRU change → persist normalized
        conn = sqlite3.connect(str(db))
        try:
            row = conn.execute(
                "SELECT value FROM library_prefs WHERE key='playlist_navigation'"
            ).fetchone()
        finally:
            conn.close()
        raw = json.loads(row[0])
        assert raw == {"pinned_ids": ["A"], "recent_ids": ["A"]}
