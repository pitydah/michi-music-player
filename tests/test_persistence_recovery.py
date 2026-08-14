"""M11.2B last-known-good backup and non-destructive recovery staging tests."""

import errno
import json
import os
import sqlite3
from pathlib import Path

import pytest

from michi.domain.persistence_health import PersistenceHealth
from michi.domain.settings import SettingsState
from michi.infrastructure import sqlite_settings
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository


def _checkpoint_wal(db_path: Path) -> None:
    """Flush WAL frames into the main file so byte-level snapshots are stable."""

    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA wal_checkpoint(FULL)")


def _write_raw_rows(db_path: Path, rows) -> None:
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_settings(db_path: Path) -> dict[str, str]:
    """Read settings rows read-only without mutating the database."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return dict(conn.execute("SELECT key, value FROM settings").fetchall())


def _remove_wal_sidecars(db_path: Path) -> None:
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def _healthy_state(**overrides):
    fields = {
        "volume": 42,
        "muted": True,
        "last_directory": "/m",
        "recent_files": ["a.mp3", "b.mp3"],
    }
    fields.update(overrides)
    return SettingsState(**fields)


class TestLastKnownGoodPath:
    def test_suffix_convention(self):
        assert SQLiteSettingsRepository.last_known_good_path(
            Path("/data/michi.db")
        ) == Path("/data/michi.db.lkg")


class TestRefreshLastKnownGood:
    def test_healthy_primary_backed_up(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        result = SQLiteSettingsRepository.refresh_last_known_good(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert result.health is PersistenceHealth.HEALTHY
        assert lkg.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(lkg).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(lkg) == _read_raw_settings(db)
        assert _read_raw_settings(lkg)["recent_files"] == json.dumps(["a.mp3", "b.mp3"])

    def test_wal_consistency_latest_committed_values(self, tmp_path):
        db = tmp_path / "wal.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(volume=10, muted=False, last_directory="/old"))
        with sqlite3.connect(str(db)) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        holder = sqlite3.connect(str(db))
        try:
            holder.execute("SELECT key, value FROM settings").fetchall()
            repo.save(SettingsState(volume=99, muted=True, last_directory="/new"))
            scratch = tmp_path / "main_only.db"
            scratch.write_bytes(db.read_bytes())
            assert _read_raw_settings(scratch)["volume"] == "10"
            result = SQLiteSettingsRepository.refresh_last_known_good(db)
            assert result.health is PersistenceHealth.HEALTHY
            lkg = SQLiteSettingsRepository.last_known_good_path(db)
            recovered = _read_raw_settings(lkg)
            assert recovered["volume"] == "99"
            assert recovered["muted"] == "true"
            assert recovered["last_directory"] == "/new"
        finally:
            holder.close()

    def test_missing_primary_returns_missing_no_artifacts(self, tmp_path):
        db = tmp_path / "absent.db"
        result = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert result.health is PersistenceHealth.MISSING
        assert not SQLiteSettingsRepository.last_known_good_path(db).exists()
        assert list(tmp_path.iterdir()) == []

    def test_corrupt_primary_preserves_existing_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        result = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert result.health is PersistenceHealth.CORRUPT_DATABASE
        assert lkg.read_bytes() == lkg_before
        assert (
            SQLiteSettingsRepository.inspect_path(lkg).health
            is PersistenceHealth.HEALTHY
        )

    def test_malformed_primary_preserves_existing_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()
        _write_raw_rows(db, [("volume", "abc")])
        result = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert result.health is PersistenceHealth.MALFORMED_DATA
        assert lkg.read_bytes() == lkg_before

    def test_healthy_refresh_advances_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(volume=10, muted=False))
        first = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert first.health is PersistenceHealth.HEALTHY
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_raw_settings(lkg)["volume"] == "10"
        repo.save(SettingsState(volume=99, muted=True))
        second = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert second.health is PersistenceHealth.HEALTHY
        assert _read_raw_settings(lkg)["volume"] == "99"
        assert _read_raw_settings(lkg)["muted"] == "true"

    def test_failed_refresh_preserves_lkg_and_cleans_temp(self, tmp_path, monkeypatch):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()

        def _fail_backup(*_args, **_kwargs):
            raise sqlite3.OperationalError("forced backup failure")

        monkeypatch.setattr(sqlite_settings, "_sqlite_backup_to_new", _fail_backup)
        result = SQLiteSettingsRepository.refresh_last_known_good(db)
        assert result.health is not PersistenceHealth.HEALTHY
        assert lkg.read_bytes() == lkg_before
        assert [p for p in tmp_path.iterdir() if p.name.startswith("tmp")] == []


class TestStageRecovery:
    def test_stage_healthy_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.HEALTHY
        assert destination.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(destination).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(destination) == _read_raw_settings(lkg)
        assert db.read_bytes() == primary_before
        assert lkg.read_bytes() == lkg_before

    def test_corrupt_primary_stage_from_lkg_is_non_destructive(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        primary_bytes = db.read_bytes()
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.HEALTHY
        assert _read_raw_settings(destination) == _read_raw_settings(lkg)
        assert db.read_bytes() == primary_bytes
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.CORRUPT_DATABASE
        )
        assert (
            SQLiteSettingsRepository.inspect_path(lkg).health
            is PersistenceHealth.HEALTHY
        )

    def test_stage_missing_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.MISSING
        assert not destination.exists()
        assert db.read_bytes() == primary_before

    def test_stage_corrupt_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        _remove_wal_sidecars(lkg)
        lkg.write_bytes(b"THIS IS NOT SQLITE")
        lkg_bytes = lkg.read_bytes()
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.CORRUPT_DATABASE
        assert not destination.exists()
        assert db.read_bytes() == primary_before
        assert lkg.read_bytes() == lkg_bytes

    def test_stage_malformed_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        _remove_wal_sidecars(lkg)
        lkg.unlink()
        _write_raw_rows(lkg, [("volume", "abc")])
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.MALFORMED_DATA
        assert not destination.exists()

    def test_stage_destination_exists(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        destination = tmp_path / "recovered.db"
        destination.write_bytes(b"existing content")
        destination_before = destination.read_bytes()
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        lkg_before = lkg.read_bytes()
        with pytest.raises(FileExistsError):
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(
                db, destination
            )
        assert destination.read_bytes() == destination_before
        assert db.read_bytes() == primary_before
        assert lkg.read_bytes() == lkg_before

    def test_stage_destination_is_primary(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        with pytest.raises(ValueError):
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(db, db)
        assert db.read_bytes() == primary_before

    def test_stage_destination_is_lkg(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        with pytest.raises(ValueError):
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(db, lkg)
        assert lkg.read_bytes() == lkg_before

    def test_stage_alias_protection(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        aliased = db.parent / "." / db.name
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        with pytest.raises(ValueError):
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(db, aliased)
        assert db.read_bytes() == primary_before

    def test_failed_stage_cleans_candidate(self, tmp_path, monkeypatch):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _checkpoint_wal(db)
        primary_before = db.read_bytes()

        def _fail_backup(source_path, dest_path, *_args, **_kwargs):
            # The reservation must already have happened: the destination
            # exists (reserved) before the backup runs.
            assert dest_path.exists(), "destination must be reserved before backup"
            dest_path.write_bytes(b"partial sqlite bytes")
            raise sqlite3.OperationalError("forced backup failure")

        monkeypatch.setattr(sqlite_settings, "_sqlite_backup_to_new", _fail_backup)
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is not PersistenceHealth.HEALTHY
        assert not destination.exists()
        assert lkg.read_bytes() == lkg_before
        assert db.read_bytes() == primary_before

    def test_foreign_writer_wins_reservation(self, tmp_path, monkeypatch):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        lkg_before = lkg.read_bytes()
        destination = tmp_path / "recovered.db"
        backup_calls: list[tuple] = []

        def _other_wins(path):
            fd = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, b"foreign data")
            os.close(fd)
            raise FileExistsError(f"another actor created {path}")

        def _spy_backup(source_path, dest_path, *_args, **_kwargs):
            backup_calls.append((source_path, dest_path))

        monkeypatch.setattr(sqlite_settings, "_reserve_new_file", _other_wins)
        monkeypatch.setattr(sqlite_settings, "_sqlite_backup_to_new", _spy_backup)
        with pytest.raises(FileExistsError):
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(
                db, destination
            )
        assert destination.read_bytes() == b"foreign data"
        assert backup_calls == []
        assert db.read_bytes() == primary_before
        assert lkg.read_bytes() == lkg_before

    def test_reservation_access_failure_returns_diagnostic(self, tmp_path, monkeypatch):
        db = tmp_path / "settings.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state())
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        _checkpoint_wal(db)
        primary_before = db.read_bytes()
        lkg_before = lkg.read_bytes()

        def _deny_reservation(path):
            raise PermissionError(errno.EACCES, "permission denied")

        monkeypatch.setattr(sqlite_settings, "_reserve_new_file", _deny_reservation)
        destination = tmp_path / "recovered.db"
        result = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, destination
        )
        assert result.health is PersistenceHealth.ACCESS_FAILURE
        assert not destination.exists()
        assert db.read_bytes() == primary_before
        assert lkg.read_bytes() == lkg_before
