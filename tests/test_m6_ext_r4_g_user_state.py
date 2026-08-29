"""M6-EXT-R4-G — truthful user-state persistence by TrackId."""

import pytest

from michi.application.library_port import (
    LibraryCatalogStorageError,
    LibraryUserStatePort,
)
from michi.domain.library_catalog import (
    LibrarySource,
    MediaFileRecord,
    TrackRecord,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository
from michi.infrastructure.library_user_state import (
    SqliteLibraryUserStateRepository,
)


@pytest.fixture
def catalog(tmp_path):
    return SqliteLibraryCatalogRepository(tmp_path / "michi.db")


@pytest.fixture
def user_state(tmp_path):
    return SqliteLibraryUserStateRepository(tmp_path / "michi.db")


@pytest.fixture
def tracks(catalog):
    """One source, three media, three tracks."""
    source = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name="Local",
        root_path="/Music",
    )
    catalog.upsert_source(source)
    media = [
        MediaFileRecord(
            media_file_id=new_media_file_id(),
            library_source_id=source.library_source_id,
            relative_path=f"song{i}.flac",
            last_known_path=f"/Music/song{i}.flac",
        )
        for i in range(3)
    ]
    catalog.upsert_media(tuple(media))
    records = [
        TrackRecord(track_id=new_track_id(), media_file_id=m.media_file_id)
        for m in media
    ]
    catalog.upsert_tracks(tuple(records))
    return tuple(r.track_id for r in records)


class TestUserStatePersistence:
    def test_port_is_abstract_boundary(self) -> None:
        assert LibraryUserStatePort.__abstractmethods__  # noqa: B018

    def test_favorites_roundtrip_sorted(self, user_state, tracks) -> None:
        favorites = (tracks[2], tracks[0], tracks[1])
        user_state.set_favorites(favorites)
        assert user_state.load_favorites() == tuple(sorted(favorites))

    def test_history_roundtrip_preserves_order(self, user_state, tracks) -> None:
        history = (tracks[1], tracks[0], tracks[2])
        user_state.set_history(history)
        assert user_state.load_history() == history

    def test_recently_added_roundtrip_preserves_order(self, user_state, tracks) -> None:
        recent = (tracks[2], tracks[1])
        user_state.set_recently_added(recent)
        assert user_state.load_recently_added() == recent

    def test_empty_collections(self, user_state) -> None:
        assert user_state.load_favorites() == ()
        assert user_state.load_history() == ()
        assert user_state.load_recently_added() == ()

    def test_replace_clears_previous(self, user_state, tracks) -> None:
        user_state.set_favorites((tracks[0], tracks[1]))
        user_state.set_favorites((tracks[2],))
        assert user_state.load_favorites() == (tracks[2],)

    def test_unknown_track_id_rejected_by_fk(self, user_state) -> None:
        with pytest.raises(LibraryCatalogStorageError):
            user_state.set_favorites(("no-such-track",))

    def test_unknown_track_id_rejected_in_history(self, user_state) -> None:
        with pytest.raises(LibraryCatalogStorageError):
            user_state.set_history(("no-such-track",))

    def test_batch_write_is_atomic(self, user_state, tracks) -> None:
        user_state.set_favorites((tracks[0],))
        with pytest.raises(LibraryCatalogStorageError):
            user_state.set_recently_added((tracks[0], "no-such-track"))
        # The failed write rolled back entirely.
        assert user_state.load_recently_added() == ()
        assert user_state.load_favorites() == (tracks[0],)

    def test_restart_preserves_state(self, tmp_path, tracks) -> None:
        repo = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
        repo.set_history((tracks[0],))
        repo2 = SqliteLibraryUserStateRepository(tmp_path / "michi.db")
        assert repo2.load_history() == (tracks[0],)

    def test_shared_schema_with_catalog(self, tmp_path, catalog, tracks) -> None:
        # User state and catalog share one fail-closed schema: dropping a
        # user-state table fails the catalog open too.
        import sqlite3

        db_path = tmp_path / "michi.db"
        catalog.schema_version()
        conn = sqlite3.connect(str(db_path))
        conn.execute("DROP TABLE library_favorites")
        conn.commit()
        conn.close()
        from michi.application.library_port import LibraryCatalogSchemaError

        with pytest.raises(LibraryCatalogSchemaError):
            catalog.load_sources()
