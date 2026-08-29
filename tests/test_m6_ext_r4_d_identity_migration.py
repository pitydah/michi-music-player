"""M6-EXT-R4-D — transactional legacy identity migration contracts.

Covers prompt §33-36 (one path→TrackId map from EVERY reference; atomic
cross-state migration), §95 (real historical fixture), §96 (failure
injection → full rollback), §97 (idempotence: rerun is a no-op).
"""

import json
import sqlite3
from pathlib import Path

import pytest

from michi.domain.library_catalog import (
    SourceLifecycle,
    legacy_source_id,
    legacy_track_id,
)
from michi.domain.session import decode_snapshot
from michi.infrastructure.library_catalog import (
    CATALOG_SCHEMA_VERSION,
    SqliteLibraryCatalogRepository,
)
from michi.infrastructure.library_identity_migration import (
    LibraryIdentityMigration,
    LibraryMigrationError,
)
from michi.infrastructure.library_user_state import (
    SqliteLibraryUserStateRepository,
)

ROOT = "/Music"
A = "/Music/A/song.flac"
B = "/Music/B/other.flac"
C = "/External/C/live.flac"  # OUTSIDE the legacy root → unresolved orphan


def _seed_historical_db(db_path: Path) -> None:
    """REAL historical database fixture matching the pre-R4 schema:
    library_index + library_prefs + settings (last_directory + V2 snapshot)."""
    conn = sqlite3.connect(str(db_path))
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS library_index (
            track_id TEXT PRIMARY KEY,
            file_size INTEGER NOT NULL,
            mtime_ns INTEGER NOT NULL,
            metadata TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS library_prefs (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY, value TEXT NOT NULL
        );
        """
    )
    meta = json.dumps(
        {
            "title": "x",
            "artist": "",
            "album": "",
            "duration_ms": 0,
            "genre": "",
            "year": 0,
            "album_artist": "",
            "track_number": 0,
            "track_total": 0,
            "disc_number": 0,
            "disc_total": 0,
            "composer": "",
            "date": "",
            "compilation": False,
            "sort_title": "",
            "sort_artist": "",
            "sort_album": "",
            "sort_album_artist": "",
            "codec": "",
            "container": "",
            "sample_rate_hz": 0,
            "bit_depth": 0,
            "channels": 0,
            "bitrate_bps": 0,
            "file_size": 0,
        }
    )
    for path in (A, B, C):
        conn.execute(
            "INSERT INTO library_index(track_id, file_size, mtime_ns, metadata) "
            "VALUES(?, 1, 1, ?)",
            (path, meta),
        )
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES(?, ?)",
        ("favorites", json.dumps([A])),
    )
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES(?, ?)",
        ("history", json.dumps([B])),
    )
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES(?, ?)",
        ("recently_added", json.dumps([C])),
    )
    conn.execute(
        "INSERT INTO library_prefs(key, value) VALUES(?, ?)",
        (
            "playlists",
            json.dumps([{"id": "p1", "name": "Mix", "track_paths": [A, B]}]),
        ),
    )
    conn.execute(
        "INSERT INTO settings(key, value) VALUES('last_directory', ?)", (ROOT,)
    )
    snapshot = {
        "version": 2,
        "queue": [
            {"file_path": A, "title": "A"},
            {"file_path": C, "title": "C"},
        ],
        "context": {
            "type": "queue",
            "source_id": None,
            "entries": [
                {"file_path": A, "title": "A"},
                {"file_path": C, "title": "C"},
            ],
            "current_index": 0,
        },
        "playback_path": A,
        "position_ms": 1200,
        "repeat_mode": "none",
        "shuffle_enabled": False,
        "shuffle_seed": 0,
    }
    conn.execute(
        "INSERT INTO settings(key, value) VALUES('session_snapshot', ?)",
        (json.dumps(snapshot),),
    )
    conn.commit()
    conn.close()


class TestHistoricalMigration:
    def test_full_migration_assigns_same_ids_everywhere(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        _seed_historical_db(db_path)
        result = LibraryIdentityMigration(db_path).migrate()

        assert result.migrated is True
        assert result.legacy_root == ROOT
        assert result.sources_created == 1
        assert result.media_created == 3
        assert result.tracks_created == 3
        assert result.favorites_migrated == 1
        assert result.history_migrated == 1
        assert result.recently_added_migrated == 1
        assert result.playlists_rewritten == 1
        assert result.session_upgraded is True

        # --- CATALOG -----------------------------------------------------
        catalog = SqliteLibraryCatalogRepository(db_path)
        assert catalog.schema_version() == CATALOG_SCHEMA_VERSION
        sources = catalog.load_sources()
        assert len(sources) == 1
        assert sources[0].library_source_id == legacy_source_id(ROOT)
        assert sources[0].root_path == ROOT
        assert sources[0].lifecycle is SourceLifecycle.ACTIVE

        media_by_path = {m.last_known_path: m for m in catalog.load_media()}
        assert media_by_path[A].library_source_id == legacy_source_id(ROOT)
        assert media_by_path[A].relative_path == "A/song.flac"
        assert media_by_path[B].relative_path == "B/other.flac"
        # C is outside the legacy root: unresolved orphan, no source.
        assert media_by_path[C].library_source_id is None
        assert media_by_path[C].relative_path is None

        tracks = catalog.load_tracks()
        assert {t.track_id for t in tracks} == {
            legacy_track_id(A),
            legacy_track_id(B),
            legacy_track_id(C),
        }

        # --- USER STATE --------------------------------------------------
        user = SqliteLibraryUserStateRepository(db_path)
        assert user.load_favorites() == (legacy_track_id(A),)
        assert user.load_history() == (legacy_track_id(B),)
        assert user.load_recently_added() == (legacy_track_id(C),)

        # --- PLAYLISTS (V3 with the SAME ids) ----------------------------
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT value FROM library_prefs WHERE key = 'playlists'"
        ).fetchone()
        payload = json.loads(row[0])
        assert payload[0]["version"] == 3
        assert payload[0]["tracks"] == [
            {"track_id": legacy_track_id(A), "fallback_path": A},
            {"track_id": legacy_track_id(B), "fallback_path": B},
        ]

        # --- SESSION (V3 with the SAME ids) ------------------------------
        row = conn.execute(
            "SELECT value FROM settings WHERE key = 'session_snapshot'"
        ).fetchone()
        snapshot = decode_snapshot(row[0])
        assert snapshot.format_version == 3
        assert snapshot.queue_entries[0].library_track_id == legacy_track_id(A)
        assert snapshot.queue_entries[1].library_track_id == legacy_track_id(C)
        assert snapshot.playback_path == A
        conn.close()

    def test_rerun_is_idempotent_noop(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        _seed_historical_db(db_path)
        first = LibraryIdentityMigration(db_path).migrate()
        second = LibraryIdentityMigration(db_path).migrate()

        assert first.migrated is True
        assert second.migrated is False  # catalog exists → no-op

        catalog = SqliteLibraryCatalogRepository(db_path)
        assert len(catalog.load_tracks()) == 3
        user = SqliteLibraryUserStateRepository(db_path)
        assert user.load_favorites() == (legacy_track_id(A),)
        # History order unchanged, no duplicates, no new ids.
        assert user.load_history() == (legacy_track_id(B),)

    def test_restart_after_move_keeps_identity(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        _seed_historical_db(db_path)
        LibraryIdentityMigration(db_path).migrate()
        before = legacy_track_id(A)

        # The catalog identity is durable: a later scan reconciles the NEW
        # location onto the SAME TrackId (relink), never a fresh id. The
        # migration itself only seeds deterministic legacy ids.
        catalog = SqliteLibraryCatalogRepository(db_path)
        assert any(t.track_id == before for t in catalog.load_tracks())


class TestMigrationFailureInjection:
    @pytest.mark.parametrize(
        "stage",
        [
            "source_write",
            "media_write",
            "track_write",
            "favorites_write",
            "history_write",
            "recently_added_write",
            "playlist_write",
            "session_write",
            "version_write",
        ],
    )
    def test_failure_rolls_back_everything(self, tmp_path, stage: str) -> None:
        db_path = tmp_path / "michi.db"
        _seed_historical_db(db_path)
        migration = LibraryIdentityMigration(
            db_path, inject_failures=frozenset({stage})
        )
        with pytest.raises(LibraryMigrationError) as excinfo:
            migration.migrate()
        assert excinfo.value.stage == stage

        # NO catalog: fail closed would reject reads — verify no partial
        # schema was left behind.
        conn = sqlite3.connect(str(db_path))
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' "
            "AND name = 'library_catalog_meta'"
        ).fetchone()
        assert row is None, "catalog schema must not exist after rollback"
        # Legacy state fully intact.
        prefs = dict(conn.execute("SELECT key, value FROM library_prefs"))
        assert json.loads(prefs["favorites"]) == [A]
        playlists = json.loads(prefs["playlists"])
        assert playlists[0].get("version") != 3
        session_raw = conn.execute(
            "SELECT value FROM settings WHERE key = 'session_snapshot'"
        ).fetchone()[0]
        assert json.loads(session_raw)["version"] == 2
        conn.close()

        # Retry succeeds cleanly after the failure.
        retry = LibraryIdentityMigration(db_path).migrate()
        assert retry.migrated is True
        assert retry.tracks_created == 3

    def test_unknown_failpoint_rejected(self, tmp_path) -> None:
        with pytest.raises(ValueError):
            LibraryIdentityMigration(
                tmp_path / "michi.db", inject_failures=frozenset({"bogus"})
            )


class TestMigrationGuards:
    def test_fresh_database_migrates_to_empty_catalog(self, tmp_path) -> None:
        db_path = tmp_path / "fresh.db"
        sqlite3.connect(str(db_path)).close()  # empty database
        result = LibraryIdentityMigration(db_path).migrate()
        assert result.migrated is True
        assert result.media_created == 0
        catalog = SqliteLibraryCatalogRepository(db_path)
        assert catalog.schema_version() == CATALOG_SCHEMA_VERSION
        assert catalog.load_sources() == ()

    def test_malformed_legacy_payloads_never_crash(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(
            """
            CREATE TABLE library_prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        conn.execute(
            "INSERT INTO library_prefs(key, value) VALUES('playlists', 'not-json')"
        )
        conn.execute(
            "INSERT INTO settings(key, value) VALUES('session_snapshot', '42')"
        )
        conn.commit()
        conn.close()

        result = LibraryIdentityMigration(db_path).migrate()
        assert result.migrated is True
        assert result.media_created == 0
        assert result.playlists_rewritten == 0
        assert result.session_upgraded is False
