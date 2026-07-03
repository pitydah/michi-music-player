"""Integration tests for the full genre pipeline: backfill → stats → cleanup → merge → rollback."""
import sqlite3
import pytest

from library.genre_repository import GenreRepository


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.execute("PRAGMA foreign_keys=ON")
    c.executescript("""
        CREATE TABLE IF NOT EXISTS media_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            filepath TEXT UNIQUE NOT NULL,
            filename TEXT NOT NULL,
            directory TEXT NOT NULL,
            ext TEXT NOT NULL DEFAULT '.flac',
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
            deleted_at REAL,
            year INTEGER DEFAULT 0
        );
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
        );
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
        );
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
            health_status TEXT DEFAULT 'ok',
            last_computed_at REAL DEFAULT 0
        );
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
        );
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
        );
    """)
    # Insert test data with various genre formats
    c.executemany(
        "INSERT INTO media_items (filepath, filename, directory, title, artist, album, genre, ext) "
        "VALUES (?,?,?,?,?,?,?,?)",
        [
            ("/rock/01.flac", "01.flac", "/rock", "Rock Song", "Rock Band", "Rock Album", "Rock", ".flac"),
            ("/rock/02.flac", "02.flac", "/rock", "Rock Anthem", "Rock Band", "Rock Album", "Rock", ".flac"),
            ("/alt/01.flac", "01.flac", "/alt", "Alt Track", "Alt Band", "Alt Album", "Alternative Rock", ".flac"),
            ("/hiphop/01.mp3", "01.mp3", "/hiphop", "Hip Hop Track", "MC Flow", "Hip Album", "Hip-Hop", ".mp3"),
            ("/hiphop/02.mp3", "02.mp3", "/hiphop", "Rap Song", "MC Flow", "Hip Album", "hiphop", ".mp3"),
            ("/hiphop/03.mp3", "03.mp3", "/hiphop", "Old School", "MC Old", "Classic", "Hip Hop", ".mp3"),
            ("/pop/01.flac", "01.flac", "/pop", "Pop Hit", "Pop Star", "Pop Album", "Pop", ".flac"),
            ("/jazz/01.flac", "01.flac", "/jazz", "Jazz Standard", "Jazz Trio", "Jazz Live", "Jazz", ".flac"),
            ("/multi/01.flac", "01.flac", "/multi", "Mixed Genre", "Mix Artist", "Mix Album", "Rock; Pop", ".flac"),
            ("/empty/01.flac", "01.flac", "/empty", "No Genre", "Unknown", "Unknown", "", ".flac"),
        ]
    )
    c.commit()
    yield c
    c.close()


class TestGenreIntegration:
    def test_full_pipeline(self, conn):
        """Complete integration test: backfill → stats → cleanup → merge → rollback."""
        repo = GenreRepository(conn)

        # Step 1: Backfill
        count = repo.backfill_from_media_items()
        assert count > 0, "Backfill should populate track_genres"

        # Verify backfill is idempotent
        count2 = repo.backfill_from_media_items()
        assert count2 == 0, "Backfill should be idempotent"

        # Step 2: Stats
        stats = repo.compute_stats()
        assert "Rock" in stats
        assert "Hip-Hop" in stats
        assert stats["Rock"]["track_count"] >= 2

        # Step 3: Aliases
        repo.add_alias("hiphop", "Hip-Hop", source="user")
        resolved = repo.resolve_alias("hiphop")
        assert resolved == "Hip-Hop"

        # Step 4: Detect duplicates
        class MockItem:
            def __init__(self, genre):
                self.genre = genre
        items = [MockItem("Hip-Hop"), MockItem("hiphop"), MockItem("Hip Hop")]
        from metadata.genre_normalizer import detect_duplicate_genres
        dups = detect_duplicate_genres(items)
        assert len(dups) >= 1

        # Step 5: Merge
        result = repo.merge_genres(["Hip Hop", "hiphop"], "Hip-Hop")
        assert result["affected"] > 0
        # Rock/Alternative Rock should not be affected
        rock_tids = repo.get_tracks_for_genre("Rock")
        assert len(rock_tids) >= 2

        # Step 6: Rename
        affected = repo.rename_genre("Jazz", "Jazz Fusion")
        assert affected > 0
        jazz_tids = repo.get_tracks_for_genre("Jazz Fusion")
        assert len(jazz_tids) >= 1

        # Step 7: Apply genre to tracks
        result_detailed = repo.apply_genre_to_tracks_detailed(
            [10], "Applied Genre", write_tags=False
        )
        assert result_detailed["success"] is True
        assert result_detailed["db_updated"] == 1

        # Step 8: Operation log
        ops = repo.get_recent_operations()
        assert len(ops) >= 3  # merge, rename, apply ops

        # Step 9: Rollback rename
        rename_op = None
        for op in ops:
            if op["operation_type"] == "rename":
                rename_op = op
                break
        if rename_op:
            result = repo.rollback_operation(rename_op["id"])
            assert result["success"] is True
            jazz_restored = repo.get_tracks_for_genre("Jazz")
            assert len(jazz_restored) >= 1

        # Step 10: Cleanup suggestions
        repo.add_suggestion("duplicate", "rock,hard rock",
                             target_genre="Rock", affected_count=5, confidence=0.9)
        suggestions = repo.get_pending_suggestions()
        assert len(suggestions) >= 1

    def test_stats_and_health(self, conn):
        """Trigger stats service which should use backfill + compute."""
        repo = GenreRepository(conn)
        repo.backfill_from_media_items()
        repo.compute_stats()
        cached = repo.get_cached_stats()
        assert len(cached) > 0
        rock_stats = cached.get("Rock", {})
        assert rock_stats.get("track_count", 0) >= 2

    def test_mix_service(self, conn):
        """GenreMixService can retrieve tracks via repo."""
        repo = GenreRepository(conn)
        repo.backfill_from_media_items()
        track_ids = repo.get_tracks_for_genre("Rock")
        assert len(track_ids) >= 2
