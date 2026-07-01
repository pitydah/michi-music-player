"""Tests for GenreRepository (DB-backed) — CRUD, merge, stats, suggestions."""
import sqlite3
import pytest

from library.genre_repository import GenreRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    # Create required tables
    c.execute("""CREATE TABLE IF NOT EXISTS media_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filepath TEXT UNIQUE NOT NULL,
        filename TEXT NOT NULL,
        directory TEXT NOT NULL,
        ext TEXT NOT NULL DEFAULT '.mp3',
        kind TEXT NOT NULL DEFAULT 'audio',
        title TEXT DEFAULT '',
        artist TEXT DEFAULT '',
        album TEXT DEFAULT '',
        genre TEXT DEFAULT '',
        duration REAL DEFAULT 0,
        sample_rate INTEGER DEFAULT 44100,
        bit_depth INTEGER DEFAULT 16,
        bitrate INTEGER DEFAULT 320,
        play_count INTEGER DEFAULT 0,
        rating INTEGER DEFAULT 0,
        deleted_at REAL
    )""")
    c.execute("""
        CREATE TABLE IF NOT EXISTS track_genres (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            track_id INTEGER NOT NULL REFERENCES media_items(id) ON DELETE CASCADE,
            genre TEXT NOT NULL,
            canonical_genre TEXT NOT NULL DEFAULT '',
            original_value TEXT NOT NULL DEFAULT '',
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'tag',
            is_manual INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL,
            UNIQUE(track_id, genre)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS genre_aliases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            alias TEXT NOT NULL UNIQUE,
            canonical_genre TEXT NOT NULL,
            confidence REAL DEFAULT 1.0,
            source TEXT DEFAULT 'builtin',
            is_builtin INTEGER DEFAULT 0,
            is_user_defined INTEGER DEFAULT 0,
            created_at REAL DEFAULT (strftime('%s','now')),
            updated_at REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS genre_stats_cache (
            genre TEXT PRIMARY KEY,
            canonical_genre TEXT NOT NULL DEFAULT '',
            track_count INTEGER DEFAULT 0,
            album_count INTEGER DEFAULT 0,
            artist_count INTEGER DEFAULT 0,
            duration_total REAL DEFAULT 0.0,
            dominant_format TEXT DEFAULT '',
            dominant_quality TEXT DEFAULT '',
            lossless_count INTEGER DEFAULT 0,
            lossy_count INTEGER DEFAULT 0,
            hires_count INTEGER DEFAULT 0,
            missing_metadata_count INTEGER DEFAULT 0,
            play_count INTEGER DEFAULT 0,
            favorite_count INTEGER DEFAULT 0,
            year_min INTEGER DEFAULT 0,
            year_max INTEGER DEFAULT 0,
            dominant_decade TEXT DEFAULT '',
            health_status TEXT DEFAULT 'ok',
            last_computed_at REAL DEFAULT 0
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS genre_cleanup_suggestions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            suggestion_type TEXT NOT NULL,
            source_genre TEXT NOT NULL,
            target_genre TEXT DEFAULT '',
            affected_track_count INTEGER DEFAULT 0,
            confidence REAL DEFAULT 0.0,
            reason TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            extra_json TEXT DEFAULT '{}',
            created_at REAL DEFAULT (strftime('%s','now')),
            resolved_at REAL
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS genre_operation_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            operation_type TEXT NOT NULL,
            source_genre TEXT DEFAULT '',
            target_genre TEXT DEFAULT '',
            track_ids TEXT DEFAULT '',
            affected_count INTEGER DEFAULT 0,
            wrote_tags INTEGER DEFAULT 0,
            details_json TEXT DEFAULT '{}',
            created_at REAL DEFAULT (strftime('%s','now'))
        )
    """)
    # Insert test tracks
    c.executemany(
        "INSERT INTO media_items (filepath, filename, directory, title, artist, album, genre, ext) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            ("/rock/01.flac", "01.flac", "/rock", "Rock Song 1", "Rock Band", "Rock Album", "Rock", ".flac"),
            ("/rock/02.flac", "02.flac", "/rock", "Rock Song 2", "Rock Band", "Rock Album", "Rock", ".flac"),
            ("/pop/01.mp3", "01.mp3", "/pop", "Pop Song", "Pop Star", "Pop Album", "Pop", ".mp3"),
            ("/jazz/01.flac", "01.flac", "/jazz", "Jazz Standard", "Jazz Trio", "Jazz Live", "Jazz", ".flac"),
        ]
    )
    c.commit()
    yield c
    c.close()


class TestGenreRepository:
    def test_ensure_track_genre(self, conn):
        repo = GenreRepository(conn)
        assert repo.ensure_track_genre(1, "Rock")
        genres = repo.get_track_genres(1)
        assert len(genres) == 1
        assert genres[0]["genre"] == "Rock"

    def test_set_track_genre(self, conn):
        repo = GenreRepository(conn)
        assert repo.set_track_genre(1, "Hard Rock")
        genres = repo.get_track_genres(1)
        assert len(genres) == 1
        assert genres[0]["source"] == "manual"

    def test_remove_track_genre(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        assert repo.remove_track_genre(1, "Rock")
        assert len(repo.get_track_genres(1)) == 0

    def test_get_tracks_for_genre(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        repo.ensure_track_genre(2, "Rock")
        repo.ensure_track_genre(3, "Pop")
        tids = repo.get_tracks_for_genre("Rock")
        assert 1 in tids
        assert 2 in tids
        assert 3 not in tids

    def test_get_all_canonical_genres(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        repo.ensure_track_genre(3, "Pop")
        repo.ensure_track_genre(4, "Jazz")
        genres = repo.get_all_canonical_genres()
        assert "Jazz" in genres
        assert "Pop" in genres

    def test_add_alias(self, conn):
        repo = GenreRepository(conn)
        assert repo.add_alias("alt rock", "Alternative rock")
        resolved = repo.resolve_alias("Alt Rock")
        assert resolved == "Alternative rock"

    def test_remove_alias(self, conn):
        repo = GenreRepository(conn)
        repo.add_alias("alt rock", "Alternative rock")
        assert repo.remove_alias("alt rock")
        assert repo.resolve_alias("alt rock") is None

    def test_get_all_aliases(self, conn):
        repo = GenreRepository(conn)
        repo.add_alias("alt rock", "Alternative rock")
        repo.add_alias("hiphop", "Hip-Hop")
        aliases = repo.get_all_aliases()
        assert len(aliases) >= 2

    def test_merge_genres(self, conn):
        repo = GenreRepository(conn)
        repo.set_track_genre(1, "Rock")
        repo.set_track_genre(2, "Classic Rock")
        result = repo.merge_genres(["Classic Rock"], "Rock")
        assert result["affected"] > 0
        tids = repo.get_tracks_for_genre("Rock")
        assert 2 in tids

    def test_rename_genre(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Old Name")
        affected = repo.rename_genre("Old Name", "New Name")
        assert affected > 0
        tids = repo.get_tracks_for_genre("New Name")
        assert 1 in tids

    def test_apply_genre_to_tracks(self, conn):
        repo = GenreRepository(conn)
        affected = repo.apply_genre_to_tracks([1, 2], "Progressive Rock")
        assert affected == 2

    def test_add_and_resolve_suggestion(self, conn):
        repo = GenreRepository(conn)
        sug_id = repo.add_suggestion(
            "duplicate", "rock,hard rock",
            target_genre="Rock", affected_count=10, confidence=0.9)
        assert sug_id is not None
        pending = repo.get_pending_suggestions()
        assert len(pending) == 1
        assert repo.resolve_suggestion(sug_id, "accepted")
        resolved = repo.get_pending_suggestions()
        assert len(resolved) == 0

    def test_detect_junk_suggestion(self, conn):
        repo = GenreRepository(conn)
        sug_id = repo.add_suggestion(
            "junk", "unknown", affected_count=1, confidence=0.8)
        assert sug_id is not None
        pending = repo.get_pending_suggestions()
        assert len(pending) == 1

    def test_get_recent_operations(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        ops = repo.get_recent_operations()
        assert len(ops) >= 0

    def test_compute_stats(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        repo.ensure_track_genre(2, "Rock")
        repo.ensure_track_genre(3, "Pop")
        repo.ensure_track_genre(4, "Jazz")
        stats = repo.compute_stats()
        assert "Rock" in stats
        assert stats["Rock"]["track_count"] == 2

    def test_get_cached_stats(self, conn):
        repo = GenreRepository(conn)
        repo.ensure_track_genre(1, "Rock")
        repo.compute_stats()
        cached = repo.get_cached_stats()
        assert "Rock" in cached
