"""M6-EXT-R4-O — M11 recovery protects the new library user authority."""

import sqlite3

from michi.domain.persistence_health import PersistenceHealth
from michi.infrastructure.library_catalog import (
    CATALOG_SCHEMA_VERSION,
    SqliteLibraryCatalogRepository,
)
from michi.infrastructure.library_identity_migration import LibraryIdentityMigration
from michi.infrastructure.library_user_state import SqliteLibraryUserStateRepository
from michi.infrastructure.sqlite_settings import (
    _AUTHORITATIVE_TABLES,
    SQLiteSettingsRepository,
    _candidate_matches_lkg,
    _read_authoritative_state,
)


class TestAuthoritativeTableSet:
    def test_catalog_and_user_state_are_authoritative(self) -> None:
        for table in (
            "library_catalog_meta",
            "library_sources",
            "library_media_files",
            "library_tracks",
            "library_favorites",
            "library_history",
            "library_recently_added",
        ):
            assert table in _AUTHORITATIVE_TABLES

    def test_cache_tables_never_authoritative(self) -> None:
        for table in ("library_index", "library_meta", "library_media_cache"):
            assert table not in _AUTHORITATIVE_TABLES

    def test_absent_r4_tables_are_optional_not_required(self, tmp_path) -> None:
        # A pre-R4 database (settings + library_prefs only) must not fail
        # closed: absent R4 authority is equivalent to empty.
        db_path = tmp_path / "legacy.db"
        conn = sqlite3.connect(str(db_path))
        conn.executescript(
            """
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            CREATE TABLE library_prefs (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """
        )
        conn.execute("INSERT INTO settings(key, value) VALUES('volume', '80')")
        conn.commit()
        conn.close()
        state = _read_authoritative_state(db_path)
        assert state["library_sources"] == []
        assert state["settings"] == [("volume", "80")]


class TestRecoveryPreservesIdentity:
    def test_full_recovery_cycle_preserves_catalog_ids(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        # 0. A real pre-R4 database has the settings table.
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.commit()
        conn.close()
        # 1. Migrate → catalog + user state exist (authoritative).
        LibraryIdentityMigration(db_path).migrate()
        catalog = SqliteLibraryCatalogRepository(db_path)
        assert catalog.schema_version() == CATALOG_SCHEMA_VERSION
        source_count = len(catalog.load_sources())

        # 2. Refresh the LKG so the current state is the recovery baseline.
        diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
        assert diag.health is PersistenceHealth.HEALTHY

        # 3. Corrupt the primary: drop the authoritative track table.
        conn = sqlite3.connect(str(db_path))
        conn.execute("DROP TABLE library_tracks")
        conn.commit()
        conn.close()
        import michi.infrastructure.sqlite_settings as _s

        _s._remove_sqlite_sidecars(db_path)

        # 4. Startup preflight detects the corruption…
        inspect = SQLiteSettingsRepository.inspect_path(db_path)
        assert inspect.health is not PersistenceHealth.HEALTHY

        # …and open_for_startup recovers from the LKG automatically.
        recovered = SQLiteSettingsRepository.open_for_startup(db_path)
        assert isinstance(recovered, SQLiteSettingsRepository)

        # 5. Catalog identity survived recovery intact (P0 protected).
        after = SqliteLibraryCatalogRepository(db_path)
        assert after.schema_version() == CATALOG_SCHEMA_VERSION
        assert len(after.load_sources()) == source_count
        assert after.load_sources() == catalog.load_sources()
        assert after.load_media() == catalog.load_media()
        assert after.load_tracks() == catalog.load_tracks()
        user = SqliteLibraryUserStateRepository(db_path)
        assert user.load_favorites() == ()

    def test_candidate_matches_lkg_includes_catalog_rows(self, tmp_path) -> None:
        db_path = tmp_path / "michi.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.commit()
        conn.close()
        LibraryIdentityMigration(db_path).migrate()
        # A rebuildable cache divergence must NEVER invalidate provenance.
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_index (track_id TEXT PRIMARY KEY, "
            "file_size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL, "
            "metadata TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO library_index VALUES('cache-only-row', 1, 1, '{}')")
        conn.commit()
        conn.close()

        diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
        assert diag.health is PersistenceHealth.HEALTHY
        lkg = SQLiteSettingsRepository.last_known_good_path(db_path)
        assert _candidate_matches_lkg(db_path, lkg) is True

    def test_catalog_row_divergence_rejects_candidate(self, tmp_path) -> None:
        # The catalog participates in provenance: a candidate whose
        # library_tracks differ from the LKG must be REJECTED (identity loss
        # is P0 and must never silently install).
        db_path = tmp_path / "michi.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.commit()
        conn.close()
        LibraryIdentityMigration(db_path).migrate()
        diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
        assert diag.health is PersistenceHealth.HEALTHY
        lkg = SQLiteSettingsRepository.last_known_good_path(db_path)

        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "INSERT INTO library_tracks(track_id, media_file_id, created_at_ms) "
            "VALUES('T-X', 'M-X', 0)"
        )
        conn.commit()
        conn.close()

        assert _candidate_matches_lkg(db_path, lkg) is False
