from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.source_repository import SourceRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE IF NOT EXISTS library_roots (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        path TEXT UNIQUE NOT NULL,
        enabled INTEGER DEFAULT 1,
        last_scan REAL,
        file_count INTEGER DEFAULT 0,
        added_count INTEGER DEFAULT 0,
        updated_count INTEGER DEFAULT 0,
        skipped_count INTEGER DEFAULT 0,
        missing_count INTEGER DEFAULT 0,
        created_at REAL DEFAULT (strftime('%s','now')),
        updated_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return SourceRepository(lambda: conn)


class TestSourceRepository:
    def test_empty(self, repo):
        assert repo.get_all() == []
        assert repo.counts() == {"total": 0, "enabled": 0}

    def test_create(self, repo, conn):
        sid = repo.create("/music")
        assert sid > 0
        sources = repo.get_all()
        assert len(sources) == 1
        assert sources[0]["path"] == "/music"

    def test_get_by_id(self, repo, conn):
        sid = repo.create("/music")
        source = repo.get_by_id(sid)
        assert source is not None
        assert source["path"] == "/music"

    def test_get_by_id_not_found(self, repo):
        assert repo.get_by_id(999) is None

    def test_update(self, repo, conn):
        sid = repo.create("/music")
        ok = repo.update(sid, file_count=42)
        assert ok
        source = repo.get_by_id(sid)
        assert source["file_count"] == 42

    def test_delete(self, repo, conn):
        sid = repo.create("/music")
        ok = repo.delete(sid)
        assert ok
        assert repo.get_all() == []

    def test_enable_disable(self, repo, conn):
        sid = repo.create("/music", enabled=False)
        ok = repo.enable(sid)
        assert ok
        source = repo.get_by_id(sid)
        assert source["enabled"] == 1
        ok = repo.disable(sid)
        assert ok
        source = repo.get_by_id(sid)
        assert source["enabled"] == 0

    def test_scan_status(self, repo, conn):
        sid = repo.create("/music")
        repo.update(sid, file_count=10, added_count=5)
        status = repo.scan_status(sid)
        assert status["file_count"] == 10
        assert status["added_count"] == 5

    def test_counts(self, repo, conn):
        repo.create("/m1", enabled=True)
        repo.create("/m2", enabled=False)
        repo.create("/m3", enabled=True)
        counts = repo.counts()
        assert counts["total"] == 3
        assert counts["enabled"] == 2
