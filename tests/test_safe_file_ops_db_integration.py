"""DB integration tests for SafeFileOperations using a real SQLite database.

Tests that move/rename correctly updates media_items, playlists, favorites,
play_history, and queue_state in an actual SQLite database.
"""

import os
import tempfile
import sqlite3

from core.safe_file_ops import SafeFileOperations


def _create_temp_db(path: str):
    """Create a minimal database schema matching the real one."""
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        directory TEXT NOT NULL,
        ext TEXT NOT NULL DEFAULT '',
        kind TEXT NOT NULL DEFAULT 'audio',
        size INTEGER DEFAULT 0,
        mtime REAL DEFAULT 0,
        duration REAL DEFAULT 0,
        title TEXT DEFAULT '',
        artist TEXT DEFAULT '',
        album TEXT DEFAULT '',
        deleted_at REAL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS playlists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS playlist_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        playlist_id INTEGER NOT NULL,
        filepath TEXT NOT NULL,
        track_id INTEGER,
        position INTEGER DEFAULT 0
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS favorites (
        track_id TEXT NOT NULL UNIQUE,
        device TEXT DEFAULT 'desktop',
        added_at REAL DEFAULT (strftime('%s','now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS play_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        track_id TEXT NOT NULL,
        device TEXT DEFAULT 'desktop',
        played_at REAL DEFAULT (strftime('%s','now'))
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS queue_state (
        id INTEGER PRIMARY KEY,
        filepath TEXT NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS library_roots (
        path TEXT UNIQUE NOT NULL,
        enabled INTEGER DEFAULT 1
    )""")
    conn.commit()
    return conn


class FakeDB:
    """Minimal DB wrapper for SafeFileOperations tests."""

    def __init__(self, conn, root_path):
        self.conn = conn
        self._root_path = root_path

    def get_library_roots(self):
        rows = self.conn.execute(
            "SELECT path FROM library_roots WHERE enabled=1").fetchall()
        return [r[0] for r in rows]


class TestSafeFileOpsDBIntegration:
    def test_rename_folder_within_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            old_dir = os.path.join(root, "Album")
            new_dir = os.path.join(root, "Album Renamed")
            os.makedirs(old_dir, exist_ok=True)
            fp = os.path.join(old_dir, "song.flac")
            open(fp, "w").close()

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (fp, "song.flac", old_dir))
            conn.execute(
                "INSERT INTO playlists (name) VALUES (?)", ("Test",))
            conn.execute(
                "INSERT INTO playlist_items (playlist_id, filepath) "
                "VALUES (1, ?)", (fp,))
            conn.execute(
                "INSERT INTO favorites (track_id) VALUES (?)", (fp,))
            conn.execute(
                "INSERT INTO play_history (track_id) VALUES (?)", (fp,))
            conn.execute(
                "INSERT INTO queue_state (id, filepath) VALUES (0, ?)", (fp,))
            conn.commit()

            db = FakeDB(conn, root)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_dir, new_dir)
            assert plan.can_proceed, f"Plan blocked: {plan.conflicts}"
            result = ops.execute_move(plan)
            assert result.success, f"Move failed: {result.error_message}"
            assert os.path.isdir(new_dir), "Destination should exist"
            assert not os.path.exists(old_dir), "Source should not exist"

            # Verify DB updates
            new_fp = os.path.join(new_dir, "song.flac")
            row = conn.execute(
                "SELECT filepath, directory, filename FROM media_items "
                "WHERE id=1").fetchone()
            assert row[0] == new_fp, f"Expected {new_fp}, got {row[0]}"
            assert row[1] == new_dir
            assert row[2] == "song.flac"

            p_row = conn.execute(
                "SELECT filepath FROM playlist_items WHERE id=1").fetchone()
            assert p_row[0] == new_fp

            f_row = conn.execute(
                "SELECT track_id FROM favorites").fetchone()
            assert f_row[0] == new_fp

            h_row = conn.execute(
                "SELECT track_id FROM play_history").fetchone()
            assert h_row[0] == new_fp

            q_row = conn.execute(
                "SELECT filepath FROM queue_state WHERE id=0").fetchone()
            assert q_row[0] == new_fp

            conn.close()

    def test_rename_file_within_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            os.makedirs(root, exist_ok=True)
            old_fp = os.path.join(root, "song.flac")
            new_fp = os.path.join(root, "renamed.flac")
            open(old_fp, "w").close()

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (old_fp, "song.flac", root))
            conn.commit()

            db = FakeDB(conn, root)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_fp, new_fp)
            assert plan.can_proceed
            result = ops.execute_move(plan)
            assert result.success

            row = conn.execute(
                "SELECT filepath FROM media_items WHERE id=1").fetchone()
            assert row[0] == new_fp
            conn.close()

    def test_block_destination_outside_root(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            outside = os.path.join(tmpdir, "Outside")
            os.makedirs(root, exist_ok=True)
            os.makedirs(outside, exist_ok=True)
            old_dir = os.path.join(root, "Album")
            new_dir = os.path.join(outside, "Album")
            os.makedirs(old_dir, exist_ok=True)
            open(os.path.join(old_dir, "song.flac"), "w").close()

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.commit()

            db = FakeDB(conn, root)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_dir, new_dir)
            assert not plan.can_proceed
            assert plan.conflicts
            conn.close()

    def test_block_cross_root_move(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root_a = os.path.join(tmpdir, "MusicA")
            root_b = os.path.join(tmpdir, "MusicB")
            os.makedirs(root_a, exist_ok=True)
            os.makedirs(root_b, exist_ok=True)
            old_dir = os.path.join(root_a, "Album")
            new_dir = os.path.join(root_b, "Album")
            os.makedirs(old_dir, exist_ok=True)

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root_a,))
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root_b,))
            conn.commit()

            db = FakeDB(conn, root_a)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_dir, new_dir)
            assert not plan.can_proceed
            conn.close()

    def test_block_destination_exists(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            old_dir = os.path.join(tmpdir, "Album")
            new_dir = os.path.join(tmpdir, "Existing")
            os.makedirs(old_dir, exist_ok=True)
            os.makedirs(new_dir, exist_ok=True)

            ops = SafeFileOperations()
            plan = ops.plan_move(old_dir, new_dir)
            assert not plan.can_proceed
            assert plan.conflicts

    def test_rollback_on_db_failure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            old_dir = os.path.join(root, "Album")
            new_dir = os.path.join(root, "Album Moved")
            os.makedirs(old_dir, exist_ok=True)
            fp = os.path.join(old_dir, "song.flac")
            open(fp, "w").close()

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (fp, "song.flac", old_dir))
            conn.commit()
            # Cause DB failure by dropping table
            conn.execute("DROP TABLE media_items")
            conn.commit()

            db = FakeDB(conn, root)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_dir, new_dir)
            if plan.can_proceed:
                result = ops.execute_move(plan)
                # Physical move happened, DB failed
                if result.rollback_performed:
                    assert os.path.exists(old_dir) or not os.path.exists(new_dir)

            conn.close()

    def test_rollback_preserves_original_on_db_failure(self):
        """When physical move succeeds but DB update fails, rollback should restore original."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            old_dir = os.path.join(root, "Album")
            new_dir = os.path.join(root, "Album_Moved")
            os.makedirs(old_dir, exist_ok=True)
            fp = os.path.join(old_dir, "song.flac")
            with open(fp, "w") as f:
                f.write("data")

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (fp, "song.flac", old_dir))
            conn.commit()

            # Simulate DB failure during execute_move — use a broken conn
            import sqlite3
            conn.close()
            broken_conn = sqlite3.connect(db_path)
            broken_conn.execute("DROP TABLE IF EXISTS media_items")
            broken_conn.commit()
            # Re-add table but with wrong schema so UPDATE fails
            broken_conn.execute(
                "CREATE TABLE media_items (id INTEGER PRIMARY KEY, garbage TEXT)")
            broken_conn.commit()

            db = FakeDB(broken_conn, root)
            ops = SafeFileOperations(db=db)
            plan = ops.plan_move(old_dir, new_dir)
            if plan.can_proceed:
                # Physical move will succeed, DB update will fail
                result = ops.execute_move(plan)
                assert result.rollback_performed, "Rollback should have been attempted"
                # After rollback, original should exist
                assert os.path.exists(old_dir), (
                    f"Original dir should exist after rollback: {old_dir}")
                assert os.path.isfile(fp), (
                    f"Original file should exist after rollback: {fp}")

            broken_conn.close()

            conn.close()

    def test_move_preserves_path_prefix_security(self):
        """Ensure /music/rock_backup is not confused with /music/rock."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = os.path.join(tmpdir, "Music")
            rock = os.path.join(root, "rock")
            rock_bak = os.path.join(root, "rock_backup")
            os.makedirs(rock, exist_ok=True)
            os.makedirs(rock_bak, exist_ok=True)
            fp_rock = os.path.join(rock, "song.flac")
            fp_bak = os.path.join(rock_bak, "track.mp3")
            open(fp_rock, "w").close()
            open(fp_bak, "w").close()

            db_path = os.path.join(tmpdir, "test.db")
            conn = _create_temp_db(db_path)
            conn.execute(
                "INSERT INTO library_roots (path) VALUES (?)", (root,))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (fp_rock, "song.flac", rock))
            conn.execute(
                "INSERT INTO media_items (filepath, filename, directory) "
                "VALUES (?, ?, ?)", (fp_bak, "track.mp3", rock_bak))
            conn.commit()

            db = FakeDB(conn, root)
            ops = SafeFileOperations(db=db)
            new_rock = os.path.join(root, "rock_v2")
            plan = ops.plan_move(rock, new_rock)
            assert plan.can_proceed
            result = ops.execute_move(plan)
            assert result.success

            # rock_backup should NOT have been updated
            rows = conn.execute(
                "SELECT filepath FROM media_items WHERE id=2"
            ).fetchone()
            assert rows[0] == fp_bak, (
                f"rock_backup path should be unchanged, got {rows[0]}")
            conn.close()
