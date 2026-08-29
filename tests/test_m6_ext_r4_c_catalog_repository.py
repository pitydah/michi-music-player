"""M6-EXT-R4-C — authoritative catalog repository contracts."""

import sqlite3

import pytest

from michi.application.library_port import (
    LibraryCatalogSchemaError,
    LibraryCatalogStorageError,
)
from michi.domain.library_catalog import (
    LibrarySource,
    MediaAvailability,
    MediaFileRecord,
    SourceLifecycle,
    TrackRecord,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
)
from michi.infrastructure.library_catalog import (
    CATALOG_SCHEMA_VERSION,
    SqliteLibraryCatalogRepository,
)


@pytest.fixture
def repo(tmp_path):
    return SqliteLibraryCatalogRepository(tmp_path / "michi.db")


def _source(
    name="Local Music",
    root="/Music",
    enabled=True,
    lifecycle=SourceLifecycle.ACTIVE,
):
    return LibrarySource(
        library_source_id=new_library_source_id(),
        display_name=name,
        root_path=root,
        enabled=enabled,
        lifecycle=lifecycle,
    )


def _media(source, relative="Album/Song.flac", availability=MediaAvailability.UNKNOWN):
    return MediaFileRecord(
        media_file_id=new_media_file_id(),
        library_source_id=source.library_source_id,
        relative_path=relative,
        last_known_path=f"{source.root_path}/{relative}",
        availability=availability,
    )


class TestSchemaFailClosed:
    def test_brand_new_database_initializes_transactionally(self, repo) -> None:
        assert repo.schema_version() == CATALOG_SCHEMA_VERSION
        assert repo.load_sources() == ()

    def test_current_schema_validates_and_loads(self, repo) -> None:
        repo.schema_version()  # initialize
        repo2 = SqliteLibraryCatalogRepository(repo._db_path)
        assert repo2.schema_version() == CATALOG_SCHEMA_VERSION

    def test_future_version_fails_closed(self, tmp_path) -> None:
        db_path = tmp_path / "future.db"
        repo = SqliteLibraryCatalogRepository(db_path)
        repo.schema_version()  # initialize at current version
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE library_catalog_meta SET value = '999' WHERE key = 'schema_version'"
        )
        conn.commit()
        conn.close()
        with pytest.raises(LibraryCatalogSchemaError):
            SqliteLibraryCatalogRepository(db_path).load_sources()

    def test_malformed_version_fails_closed(self, tmp_path) -> None:
        db_path = tmp_path / "malformed.db"
        repo = SqliteLibraryCatalogRepository(db_path)
        repo.schema_version()
        conn = sqlite3.connect(str(db_path))
        conn.execute(
            "UPDATE library_catalog_meta SET value = 'not-a-number' "
            "WHERE key = 'schema_version'"
        )
        conn.commit()
        conn.close()
        with pytest.raises(LibraryCatalogSchemaError):
            SqliteLibraryCatalogRepository(db_path).load_sources()

    def test_missing_meta_with_catalog_tables_fails_closed(self, tmp_path) -> None:
        db_path = tmp_path / "orphan.db"
        conn = sqlite3.connect(str(db_path))
        conn.execute("CREATE TABLE library_sources (x TEXT)")
        conn.commit()
        conn.close()
        with pytest.raises(LibraryCatalogSchemaError):
            SqliteLibraryCatalogRepository(db_path).load_sources()

    def test_missing_table_at_current_version_fails_closed(self, tmp_path) -> None:
        db_path = tmp_path / "incomplete.db"
        repo = SqliteLibraryCatalogRepository(db_path)
        repo.schema_version()
        conn = sqlite3.connect(str(db_path))
        conn.execute("DROP TABLE library_tracks")
        conn.commit()
        conn.close()
        with pytest.raises(LibraryCatalogSchemaError):
            SqliteLibraryCatalogRepository(db_path).load_tracks()


class TestAuthoritativeWrites:
    def test_source_roundtrip(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        assert repo.load_sources() == (source,)

    def test_source_upsert_updates_in_place(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        updated = LibrarySource(
            library_source_id=source.library_source_id,
            display_name="Renamed",
            root_path="/New/Root",
        )
        repo.upsert_source(updated)
        assert repo.load_sources() == (updated,)

    def test_retire_and_disable_preserve_record(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        repo.retire_source(source.library_source_id)
        repo.set_source_enabled(source.library_source_id, False)
        loaded = repo.load_sources()[0]
        assert loaded.lifecycle is SourceLifecycle.RETIRED
        assert loaded.enabled is False

    def test_media_and_track_roundtrip(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        media = _media(source)
        track = TrackRecord(
            track_id=new_track_id(),
            media_file_id=media.media_file_id,
            created_at_ms=1234,
        )
        repo.upsert_media((media,))
        repo.upsert_tracks((track,))
        assert repo.load_media() == (media,)
        assert repo.load_tracks() == (track,)
        assert repo.media_for_source(source.library_source_id) == (media,)

    def test_mark_media_availability(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        media = _media(source)
        repo.upsert_media((media,))
        repo.mark_media_availability(media.media_file_id, MediaAvailability.MISSING)
        assert repo.load_media()[0].availability is MediaAvailability.MISSING

    def test_batch_media_write_is_atomic(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        good = _media(source, "Good.flac")
        bad = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id="unknown-source",  # violates FK
            relative_path="Bad.flac",
            last_known_path="/Bad.flac",
        )
        with pytest.raises(LibraryCatalogStorageError):
            repo.upsert_media((good, bad))
        # The whole batch rolled back: nothing persisted.
        assert repo.load_media() == ()

    def test_fk_restrict_prevents_orphan_media(self, repo) -> None:
        orphan = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id="no-such-source",
            relative_path="x.flac",
            last_known_path="/x.flac",
        )
        with pytest.raises(LibraryCatalogStorageError):
            repo.upsert_media((orphan,))

    def test_fk_restrict_prevents_orphan_track(self, repo) -> None:
        track = TrackRecord(track_id=new_track_id(), media_file_id="no-such-media")
        with pytest.raises(LibraryCatalogStorageError):
            repo.upsert_tracks((track,))

    def test_unique_source_relative_path_enforced(self, repo) -> None:
        source = _source()
        repo.upsert_source(source)
        repo.upsert_media((_media(source, "Same.flac"),))
        with pytest.raises(LibraryCatalogStorageError):
            repo.upsert_media((_media(source, "Same.flac"),))

    def test_missing_media_availability_mark_raises(self, repo) -> None:
        with pytest.raises(LibraryCatalogStorageError):
            repo.mark_media_availability("nope", MediaAvailability.MISSING)

    def test_missing_source_update_raises(self, repo) -> None:
        with pytest.raises(LibraryCatalogStorageError):
            repo.retire_source("nope")


class TestUnresolvedLegacyMedia:
    def test_orphan_media_without_source_is_persistable(self, repo) -> None:
        orphan = MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=None,
            relative_path=None,
            last_known_path="/old/Music/gone.flac",
            availability=MediaAvailability.MISSING,
        )
        repo.upsert_media((orphan,))
        loaded = repo.load_media()[0]
        assert loaded.library_source_id is None
        assert loaded.relative_path is None
        assert loaded.availability is MediaAvailability.MISSING

    def test_two_orphans_share_null_unique_key(self, repo) -> None:
        # UNIQUE(library_source_id, relative_path) must not reject multiple
        # unresolved orphans (NULLs are distinct in SQLite unique indexes).
        repo.upsert_media(
            (
                MediaFileRecord(
                    media_file_id=new_media_file_id(),
                    library_source_id=None,
                    relative_path=None,
                    last_known_path="/a.flac",
                ),
                MediaFileRecord(
                    media_file_id=new_media_file_id(),
                    library_source_id=None,
                    relative_path=None,
                    last_known_path="/b.flac",
                ),
            )
        )
        assert len(repo.load_media()) == 2
