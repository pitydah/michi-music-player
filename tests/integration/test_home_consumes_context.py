"""Home consumes the canonical ContextService — no independent snapshot.

``HomeDashboardService.build_snapshot()`` must use the SAME context service
values for the shared playback/library/audio/ecosystem sections (ADR-002):
removing the underlying service changes both the context snapshot and the
home snapshot in lockstep, and home capabilities are never hardcoded.
"""
from __future__ import annotations

import os
import sqlite3

import pytest

from core.context import context_repository as repo
from core.context.context_service import ContextService
from core.home.home_dashboard_service import HomeDashboardService
from core.playback_snapshot_service import PlaybackSnapshotService


class _FakePlayer:
    def __init__(self, snapshot: dict | None = None):
        self._snapshot = snapshot

    def get_playback_snapshot(self):
        return self._snapshot


class _RealDb:
    def __init__(self, conn: sqlite3.Connection):
        self._conn = conn
        self.conn = conn

    def get_dashboard_stats(self) -> dict:
        total = self.conn.execute(
            "SELECT COUNT(*) FROM media_items WHERE deleted_at IS NULL"
        ).fetchone()[0]
        return {"total_songs": total, "total_albums": 0, "total_artists": 0}


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
}


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
        ],
    )
    conn.commit()
    yield _RealDb(conn)
    conn.close()


def _playing_snapshot():
    return {
        "available": True,
        "state": "playing",
        "position_seconds": 12.0,
        "duration_seconds": 200.0,
        "volume": 0.7,
        "title": "Song A",
        "artist": "Artist",
        "album": "Album",
        "current_path": "/tmp/a.flac",
        "queue_length": 2,
        "queue_index": 0,
        "backend_id": "gstreamer",
    }


class TestHomeConsumesContext:
    def teardown_method(self):
        repo.close()
        repo.override_db_path(None)

    def test_playback_section_equals_context_snapshot(self, tmp_path, real_db):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        player = _FakePlayer(snapshot=_playing_snapshot())
        snap_svc = PlaybackSnapshotService(player_service=player)
        ctx = ContextService(
            db=real_db,
            snapshot_service=snap_svc,
            container=_StubContainer(_CAP_SERVICES),
        )
        home = HomeDashboardService(
            db=real_db,
            playback=player,
            context_svc=ctx,
        )
        snapshot = home.build_snapshot()

        ctx_playback = ctx.snapshot()["playback"]
        assert snapshot.playback.current_title == "Song A"
        assert snapshot.playback.current_artist == "Artist"
        assert snapshot.playback.state == "playing"
        assert snapshot.playback.current_title == (
            ctx_playback["now_playing"]["title"]
        )
        assert snapshot.playback.queue_count == ctx_playback["queue"]["count"]

    def test_playback_unavailable_matches_context(self, tmp_path, real_db):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        ctx = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        home = HomeDashboardService(
            db=real_db,
            playback=None,
            context_svc=ctx,
        )
        snapshot = home.build_snapshot()
        assert snapshot.playback.state == "stopped"
        assert snapshot.playback.has_current_track is False
        assert ctx.snapshot()["playback"]["available"] is False

    def test_library_counts_from_context_section(self, tmp_path, real_db):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        ctx = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        home = HomeDashboardService(
            db=real_db,
            context_svc=ctx,
        )
        snapshot = home.build_snapshot()
        assert snapshot.library.track_count == 2
        assert snapshot.library.track_count == ctx.snapshot()["library"]["track_count"]

    def test_capabilities_not_hardcoded(self, tmp_path, real_db):
        repo.override_db_path(os.path.join(str(tmp_path), "ctx.sqlite"))
        ctx = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES),
        )
        caps = ctx.snapshot()["capabilities"]["capabilities"]
        assert caps["can_search_library"]["available"] is True
        # Remove a service -> home context reflects it (no hardcoded True).
        ctx_limited = ContextService(
            db=real_db,
            container=_StubContainer(_CAP_SERVICES - {"playlist_service"}),
        )
        limited_caps = ctx_limited.snapshot()["capabilities"]["capabilities"]
        assert limited_caps["can_create_playlist"]["available"] is False
        assert "playlist_service" in limited_caps["can_create_playlist"]["reason"]

    def test_home_falls_back_without_context(self, tmp_path, real_db):
        home = HomeDashboardService(db=real_db, playback=None)
        snapshot = home.build_snapshot()
        assert snapshot.library.track_count == 2
        assert snapshot.playback.state == "stopped"
