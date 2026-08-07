"""Vertical context snapshot test — real ContextService with real services.

Verifies: playback section derives from the canonical PlaybackSnapshotService
(available=False without a player), library counts come from a real SQLite DB,
queue from a real QueueService, and capabilities reflect service presence
(remove a service -> capability False with a reason).
"""
from __future__ import annotations

import os
import sqlite3

import pytest

from core.context import context_repository as repo
from core.context.context_service import ContextService
from core.playback_snapshot_service import PlaybackSnapshotService
from core.queue_service import QueueService


class _FakePlayer:
    def __init__(self, snapshot: dict | None = None):
        self._snapshot = snapshot

    def get_playback_snapshot(self):
        return self._snapshot


class _RealDb:
    """Real SQLite-backed database duck-type with dashboard stats."""

    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self.conn = conn

    def get_dashboard_stats(self) -> dict:
        total = self.conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()[0]
        return {"total_songs": total, "total_albums": 0, "total_artists": 0}


@pytest.fixture
def real_db(tmp_path):
    conn = sqlite3.connect(str(tmp_path / "library.sqlite"))
    conn.execute(
        "CREATE TABLE media_items ("
        "filepath TEXT, title TEXT, artist TEXT, album TEXT, genre TEXT,"
        "kind TEXT, duration REAL, scan_status TEXT, deleted_at TEXT)"
    )
    conn.executemany(
        "INSERT INTO media_items VALUES (?, ?, ?, ?, ?, ?, ?, ?, NULL)",
        [
            ("/tmp/a.flac", "Song A", "Artist", "Album", "Rock", "audio", 180.0, "ok"),
            ("/tmp/b.flac", "Song B", "Artist", "Album", "Rock", "audio", 200.0, "ok"),
            ("/tmp/c.flac", "Song C", "Artist", "Album 2", "Jazz", "audio", 150.0, "error"),
        ],
    )
    conn.commit()
    yield _RealDb(conn)
    conn.close()


class _StubContainer:
    def __init__(self, present: set[str]):
        self._present = set(present)

    def contains(self, name: str) -> bool:
        return name in self._present

    def is_capable(self, name: str) -> bool:
        return name in self._present


_CAP_SERVICES = {
    "global_search_service", "playlist_service", "queue_service",
    "library_mutation_service", "audio_lab_service", "playback_service",
    "diagnostics_service", "device_sync_service",
}


class TestContextSnapshotVertical:
    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def _repo(self, tmp_path):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))

    def _snapshot_service(self, player=None, queue=None):
        return PlaybackSnapshotService(player_service=player, queue_service=queue)

    def test_playback_section_available_false_without_player(self, tmp_path, real_db):
        self._repo(tmp_path)
        snap_svc = self._snapshot_service(player=None)
        svc = ContextService(
            db=real_db,
            snapshot_service=snap_svc,
            container=_StubContainer(_CAP_SERVICES),
        )
        section = svc.snapshot()["playback"]
        assert section["available"] is False
        assert section["reason"] == "playback_readback_failed"

    def test_playback_section_from_canonical_snapshot(self, tmp_path, real_db):
        self._repo(tmp_path)
        player = _FakePlayer(snapshot={
            "available": True,
            "state": "playing",
            "position_seconds": 12.0,
            "duration_seconds": 200.0,
            "volume": 0.7,
            "title": "Song A",
            "artist": "Artist",
            "album": "Album",
            "current_path": "/tmp/a.flac",
            "queue_length": 3,
            "queue_index": 0,
            "backend_id": "gstreamer",
        })
        snap_svc = self._snapshot_service(player=player)
        svc = ContextService(
            db=real_db,
            snapshot_service=snap_svc,
            container=_StubContainer(_CAP_SERVICES),
        )
        section = svc.snapshot()["playback"]
        assert section["available"] is True
        assert section["state"] == "playing"
        assert section["now_playing"]["title"] == "Song A"
        assert section["queue"]["count"] == 3

    def test_library_counts_from_real_db(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        section = svc.snapshot()["library"]
        assert section["available"] is True
        assert section["track_count"] == 3
        assert section["genre_count"] == 2
        assert section["index_error_count"] == 1

    def test_queue_section_from_real_queue_service(self, tmp_path, real_db):
        self._repo(tmp_path)
        from unittest.mock import MagicMock
        queue = QueueService(
            player_service=None,
            event_bus=MagicMock(),
            runtime_persistence=MagicMock(),
        )
        queue.enqueue({"title": "A", "artist": "X"}, play_now=False)
        queue.enqueue({"title": "B", "artist": "X"}, play_now=False)
        svc = ContextService(
            db=real_db,
            services={"queue_service": queue},
            container=_StubContainer(_CAP_SERVICES),
        )
        section = svc.snapshot()["queue"]
        assert section["available"] is True
        assert section["count"] == 2
        assert section["active"] is True

    def test_queue_section_missing_service(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        section = svc.snapshot()["queue"]
        assert section["available"] is False
        assert "queue_service_missing" in section["reason"]

    def test_capabilities_reflect_service_presence(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        caps = svc.snapshot()["capabilities"]["capabilities"]
        assert caps["can_search_library"]["available"] is True
        assert caps["can_radio"]["available"] is False
        assert "radio_service" in caps["can_radio"]["reason"]

    def test_capability_false_when_service_removed(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES - {"playlist_service"}),
        )
        caps = svc.snapshot()["capabilities"]["capabilities"]
        assert caps["can_search_library"]["available"] is True
        assert caps["can_create_playlist"]["available"] is False
        assert "playlist_service" in caps["can_create_playlist"]["reason"]

    def test_capabilities_false_without_container(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(db=real_db)
        caps = svc.snapshot()["capabilities"]["capabilities"]
        assert caps["can_search_library"]["available"] is False
        assert "global_search_service" in caps["can_search_library"]["reason"]

    def test_errors_section_from_repository(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        svc.record_operational_error("audio_lab", "AUDIO_FAILED", "boom")
        section = svc.snapshot()["errors"]
        assert section["count"] == 1
        assert section["errors"][0]["code"] == "AUDIO_FAILED"

    def test_snapshot_sanitized_no_absolute_paths(self, tmp_path, real_db):
        self._repo(tmp_path)
        svc = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        raw = str(svc.snapshot())
        assert "/tmp/" not in raw
