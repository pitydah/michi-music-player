"""M6-EXT-R4 freeze gate — P0: atomic source reconciliation.

A MediaFileRecord can NEVER persist without its TrackRecord: media + track
mutations land in ONE transaction. Failure → full rollback; retry succeeds;
restart sees coherent catalog; partial authoritative state is impossible.
"""

import sqlite3

import pytest

from michi.application.library_port import LibraryCatalogStorageError
from michi.domain.library_catalog import (
    LibrarySource,
    MediaFileRecord,
    TrackRecord,
    new_library_source_id,
    new_media_file_id,
    new_track_id,
)
from michi.infrastructure.library_catalog import SqliteLibraryCatalogRepository


@pytest.fixture
def repo(tmp_path):
    return SqliteLibraryCatalogRepository(tmp_path / "michi.db")


@pytest.fixture
def source(repo):
    src = LibrarySource(
        library_source_id=new_library_source_id(),
        display_name="Local",
        root_path="/Music",
    )
    repo.upsert_source(src)
    return src


def _media(source, relative="A/song.flac"):
    return MediaFileRecord(
        media_file_id=new_media_file_id(),
        library_source_id=source.library_source_id,
        relative_path=relative,
        last_known_path=f"/Music/{relative}",
        availability="available",  # placeholder; normalized below
    )


def _media_record(source, relative="A/song.flac"):
    from michi.domain.library_catalog import MediaAvailability

    record = _media(source, relative)
    return MediaFileRecord(
        media_file_id=record.media_file_id,
        library_source_id=record.library_source_id,
        relative_path=record.relative_path,
        last_known_path=record.last_known_path,
        availability=MediaAvailability.AVAILABLE,
    )


def _track(media_id):
    return TrackRecord(track_id=new_track_id(), media_file_id=media_id)


class TestAtomicReconciliation:
    def test_a_media_then_track_failure_persists_zero(self, repo, source) -> None:
        media = _media_record(source)
        bad_track = TrackRecord(  # FK violation: media not in the batch
            track_id=new_track_id(), media_file_id="no-such-media"
        )
        with pytest.raises(LibraryCatalogStorageError):
            repo.apply_source_reconciliation((media,), (bad_track,))
        # ZERO media persisted, ZERO tracks persisted.
        assert repo.load_media() == ()
        assert repo.load_tracks() == ()

    def test_b_existing_state_intact_after_failure(self, repo, source) -> None:
        # Pre-existing coherent state.
        existing_media = _media_record(source, "B/old.flac")
        existing_track = _track(existing_media.media_file_id)
        repo.apply_source_reconciliation((existing_media,), (existing_track,))
        before_media = repo.load_media()
        before_tracks = repo.load_tracks()

        # Failing batch (orphan track) must not disturb it.
        new_media = _media_record(source, "A/new.flac")
        bad_track = TrackRecord(track_id=new_track_id(), media_file_id="no-such-media")
        with pytest.raises(LibraryCatalogStorageError):
            repo.apply_source_reconciliation((new_media,), (bad_track,))

        assert repo.load_media() == before_media
        assert repo.load_tracks() == before_tracks

    def test_c_retry_succeeds_cleanly(self, repo, source) -> None:
        media = _media_record(source)
        bad_track = TrackRecord(track_id=new_track_id(), media_file_id="missing")
        with pytest.raises(LibraryCatalogStorageError):
            repo.apply_source_reconciliation((media,), (bad_track,))

        good_track = _track(media.media_file_id)
        repo.apply_source_reconciliation((media,), (good_track,))
        assert len(repo.load_media()) == 1
        assert len(repo.load_tracks()) == 1
        assert repo.load_tracks()[0].media_file_id == media.media_file_id

    def test_d_restart_sees_coherent_catalog(self, tmp_path, source) -> None:
        db_path = tmp_path / "michi.db"
        repo = SqliteLibraryCatalogRepository(db_path)
        repo.upsert_source(source)
        media = _media_record(source)
        track = _track(media.media_file_id)
        repo.apply_source_reconciliation((media,), (track,))

        restarted = SqliteLibraryCatalogRepository(db_path)
        media_rows = restarted.load_media()
        track_rows = restarted.load_tracks()
        assert len(media_rows) == 1 and len(track_rows) == 1
        assert track_rows[0].media_file_id == media_rows[0].media_file_id

    def test_e_partial_state_impossible_by_construction(self, repo, source) -> None:
        # Every successful reconciliation leaves media/track counts equal;
        # every failed one leaves BOTH untouched — never one without the
        # other (invariant probe after random-ish sequences).
        for i in range(3):
            media = _media_record(source, f"A/t{i}.flac")
            good = _track(media.media_file_id)
            repo.apply_source_reconciliation((media,), (good,))
        for i in range(3):
            media = _media_record(source, f"B/t{i}.flac")
            bad = TrackRecord(track_id=new_track_id(), media_file_id="missing")
            with pytest.raises(LibraryCatalogStorageError):
                repo.apply_source_reconciliation((media,), (bad,))
        media_count = len(repo.load_media())
        track_count = len(repo.load_tracks())
        assert media_count == track_count == 3

    def test_media_without_tracks_batch_is_allowed(self, repo, source) -> None:
        # Availability-only updates (no new tracks) are a legitimate
        # reconciliation (marking MISSING) — media upserts alone are fine.
        media = _media_record(source)
        repo.apply_source_reconciliation((media,), ())
        assert len(repo.load_media()) == 1
        assert repo.load_tracks() == ()

    def test_sqlite_level_no_partial_rows_after_injected_failure(
        self, repo, source, monkeypatch
    ) -> None:
        # Inject a hard failure INSIDE the transaction after the media
        # statement ran — the rollback must still erase it.
        media = _media_record(source)
        track = _track(media.media_file_id)
        original = SqliteLibraryCatalogRepository._upsert_track_statement

        def boom(conn, track_record):
            original(conn, track_record)
            raise sqlite3.IntegrityError("injected track failure")

        monkeypatch.setattr(
            SqliteLibraryCatalogRepository,
            "_upsert_track_statement",
            staticmethod(boom),
        )
        with pytest.raises(LibraryCatalogStorageError):
            repo.apply_source_reconciliation((media,), (track,))
        assert repo.load_media() == ()
        assert repo.load_tracks() == ()
