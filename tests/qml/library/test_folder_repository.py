from __future__ import annotations

import sqlite3
import pytest

from core.library.repositories.folder_repository import FolderRepository
import pytest
pytestmark = [pytest.mark.qml_module("library")]


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT, directory TEXT, title TEXT,
        artist TEXT, album TEXT, ext TEXT,
        deleted_at REAL
    )""")
    c.commit()
    return c


@pytest.fixture
def repo(conn):
    return FolderRepository(lambda: conn)


def _insert(conn, directory):
    conn.execute(
        "INSERT INTO media_items (filepath, directory, title) VALUES (?,?,?)",
        (f"{directory}/song.flac", directory, "Song"),
    )
    conn.commit()


class TestFolderRepository:
    def test_empty(self, repo):
        assert repo.count() == 0
        assert repo.tree() == []

    def test_count(self, conn, repo):
        _insert(conn, "/music/rock")
        _insert(conn, "/music/jazz")
        assert repo.count() == 2

    def test_tree(self, conn, repo):
        _insert(conn, "/music/rock")
        _insert(conn, "/music/jazz")
        tree = repo.tree()
        assert len(tree) == 2
        paths = {t["path"] for t in tree}
        assert "/music/rock" in paths

    def test_children(self, conn, repo):
        _insert(conn, "/music/rock/classic")
        _insert(conn, "/music/rock/prog")
        children = repo.children("/music/rock")
        assert len(children) == 2

    def test_parents(self, repo):
        parents = repo.parents("/music/rock/classic/sub")
        assert len(parents) == 3
        assert parents[0]["name"] == "music"
        assert parents[2]["name"] == "classic"

    def test_breadcrumb(self, repo):
        crumbs = repo.breadcrumb("/music/rock/classic")
        assert len(crumbs) == 3
        assert crumbs[-1]["name"] == "classic"

    def test_breadcrumb_root(self, repo):
        crumbs = repo.breadcrumb("/music")
        assert len(crumbs) == 1

    def test_count_with_parent(self, conn, repo):
        _insert(conn, "/music/rock/classic")
        _insert(conn, "/music/rock/prog")
        _insert(conn, "/music/jazz")
        cnt = repo.count("/music/rock")
        assert cnt == 2

    def test_tree_excludes_deleted(self, conn, repo):
        conn.execute("INSERT INTO media_items (filepath, directory, title, deleted_at) "
                      "VALUES (?,?,?,?)",
                      ("/music/old/song.flac", "/music/old", "Song", 12345))
        conn.commit()
        _insert(conn, "/music/new")
        assert repo.count() == 1
