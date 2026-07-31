"""Tests for library.connection_factory — SQLite concurrency primitives.

Covers the Patch 5 model: one read-only connection per thread
(ReadConnectionFactory) and a single serialized writer (WriterCoordinator),
plus WAL verification.
"""
from __future__ import annotations

import sqlite3
import threading

import pytest

from library.connection_factory import ReadConnectionFactory, WriterCoordinator


@pytest.fixture
def db_path(tmp_path: str) -> str:
    path = str(tmp_path / "concurrency.db")
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE media_items (id INTEGER PRIMARY KEY, title TEXT)")
    conn.execute("INSERT INTO media_items (title) VALUES ('Genesis')")
    conn.commit()
    conn.close()
    # File must exist so read-only URIs can open it.
    return path


class TestReadConnectionFactory:
    def test_connection_cached_per_thread(self, db_path: str):
        factory = ReadConnectionFactory(db_path)
        assert factory.connection() is factory.connection()

    def test_thread_local_connections(self, db_path: str):
        factory = ReadConnectionFactory(db_path)
        main_conn = factory.connection()
        holder: dict = {}

        def grab() -> None:
            holder["conn"] = factory.connection()

        t = threading.Thread(target=grab)
        t.start()
        t.join()
        assert holder["conn"] is not None
        assert holder["conn"] is not main_conn

    def test_read_only_cannot_write(self, db_path: str):
        factory = ReadConnectionFactory(db_path)
        with pytest.raises(sqlite3.OperationalError):
            factory.connection().execute(
                "INSERT INTO media_items (title) VALUES ('fail')")

    def test_row_factory_is_row(self, db_path: str):
        factory = ReadConnectionFactory(db_path)
        row = factory.connection().execute(
            "SELECT title FROM media_items LIMIT 1").fetchone()
        assert row["title"] == "Genesis"

    def test_db_path_property(self, db_path: str):
        assert ReadConnectionFactory(db_path).db_path == db_path


class TestWriterCoordinator:
    def test_execute_writes_and_commits(self, db_path: str):
        writer = WriterCoordinator(db_path)
        writer.execute("INSERT INTO media_items (title) VALUES (?)", ("Yes",))
        reader = ReadConnectionFactory(db_path)
        titles = [r["title"] for r in reader.connection().execute(
            "SELECT title FROM media_items ORDER BY title").fetchall()]
        assert "Yes" in titles

    def test_wal_verified(self, db_path: str):
        writer = WriterCoordinator(db_path)
        writer.execute("INSERT INTO media_items (title) VALUES ('x')")
        mode = writer.execute("PRAGMA journal_mode").fetchone()
        assert str(mode[0]).lower() == "wal"

    def test_connection_created_lazily(self, db_path: str):
        writer = WriterCoordinator(db_path)
        assert writer._conn is None
        writer.execute("SELECT 1")
        assert writer._conn is not None

    def test_serialized_concurrent_writers(self, db_path: str):
        writer = WriterCoordinator(db_path)
        errors: list = []

        def insert(tid: int) -> None:
            try:
                for _ in range(20):
                    writer.execute(
                        "INSERT INTO media_items (title) VALUES (?)",
                        (f"t{tid}",))
            except Exception as exc:  # noqa: BLE001
                errors.append(exc)

        threads = [threading.Thread(target=insert, args=(i,)) for i in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        assert errors == []
        count = writer.execute("SELECT COUNT(*) FROM media_items").fetchone()[0]
        assert count >= 4 * 20

    def test_close_releases_connection(self, db_path: str):
        writer = WriterCoordinator(db_path)
        writer.execute("SELECT 1")
        writer.close()
        assert writer._conn is None
