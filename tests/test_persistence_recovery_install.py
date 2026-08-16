"""M11.2E automatic persistence recovery + quarantine + safe install — RED tests.

These tests encode the M11.2E contract (WP §53-§74): recoverable primaries
(MISSING / CORRUPT_DATABASE / structural MALFORMED_DATA with a healthy LKG)
are auto-restored by validating a trusted candidate, quarantining the original
primary artifacts byte-exact, strictly removing original sidecars, and
installing the candidate via os.replace. Untrusted material (foreign
candidates, unhealthy LKG, orphan sidecars) and terminal states are blocked
with PersistenceStartupError.
"""

import errno
import hashlib
import json
import logging
import os
import sqlite3
import stat
from pathlib import Path

import pytest

from michi.domain.persistence_health import PersistenceDiagnostic, PersistenceHealth
from michi.domain.settings import SettingsState
from michi.infrastructure import sqlite_settings as sqlite_settings_mod
from michi.infrastructure.sqlite_settings import (
    PersistenceStartupError,
    SQLiteSettingsRepository,
)


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_settings(db_path):
    """Read settings rows read-only without mutating the database."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return dict(conn.execute("SELECT key, value FROM settings").fetchall())


def _remove_wal_sidecars(db_path):
    for suffix in ("-wal", "-shm"):
        sidecar = Path(str(db_path) + suffix)
        if sidecar.exists():
            sidecar.unlink()


def _sha256(path):
    """Streaming SHA-256 of a file (chunked reads, no full load)."""
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        while True:
            chunk = fh.read(64 * 1024)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def _healthy_state(**overrides):
    fields = {
        "volume": 42,
        "muted": True,
        "last_directory": "/m",
        "recent_files": ["a.mp3", "b.mp3"],
    }
    fields.update(overrides)
    return SettingsState(**fields)


def _make_healthy_with_lkg(db_path):
    repo = SQLiteSettingsRepository(db_path)
    repo.save(_healthy_state())
    diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
    assert diag.health is PersistenceHealth.HEALTHY
    return repo


def _foreign_candidate_rows():
    """A healthy but foreign candidate (volume=90) never equal to the LKG."""
    return [
        ("volume", "90"),
        ("muted", "true"),
        ("last_directory", "/x"),
        ("recent_files", json.dumps([])),
    ]


def _quarantine_generations(db_path):
    """Sorted recovery-* generations under <db>.quarantine, if the root exists."""
    qroot = Path(str(db_path) + ".quarantine")
    if not qroot.is_dir():
        return []
    return sorted(p for p in qroot.iterdir() if p.name.startswith("recovery-"))


class CallSpy:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


class TestAutoRecoveryInstall:
    def test_missing_healthy_lkg_auto_recovers(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        # LKG preserved: logical rows and bytes unchanged.
        assert _read_raw_settings(lkg) == lkg_rows
        assert lkg.read_bytes() == lkg_before
        # No primary artifacts existed, so no quarantine generation was created.
        assert not Path(str(db) + ".quarantine").exists()

    def test_corrupt_healthy_lkg_auto_recovers(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        assert not Path(str(db) + "-wal").exists()
        assert not Path(str(db) + "-shm").exists()
        corrupt = b"THIS IS NOT SQLITE"
        db.write_bytes(corrupt)
        corrupt_sha = _sha256(db)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        assert _read_raw_settings(lkg) == lkg_rows

        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == corrupt
        assert _sha256(files[0]) == corrupt_sha

    def test_structural_malformed_healthy_lkg_recovers(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        db.unlink()
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE other (x INTEGER)")
        primary_before = db.read_bytes()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()

        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert files[0].read_bytes() == primary_before


class TestFieldMalformedNoRecovery:
    def test_field_malformed_does_not_auto_recover(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state(volume=20))
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_raw_settings(lkg)["volume"] == "20"
        _remove_wal_sidecars(db)
        db.unlink()
        _write_raw_rows(db, [("volume", "broken"), ("muted", "true")])
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.MALFORMED_DATA
        )

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        # M11.2C default (80), NOT the LKG's 20 — field recovery only.
        assert repo.load().volume == 80
        assert not Path(str(db) + ".quarantine").exists()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        assert _read_raw_settings(db)["volume"] == "broken"


class TestCandidateTrust:
    def test_trusted_preexisting_candidate_resumes(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        assert (
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(
                db, candidate
            ).health
            is PersistenceHealth.HEALTHY
        )
        assert not Path(str(candidate) + "-wal").exists()
        assert not Path(str(candidate) + "-shm").exists()
        _remove_wal_sidecars(db)
        db.unlink()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert repo.load() == _healthy_state()
        assert _read_raw_settings(db) == lkg_rows
        assert not candidate.exists()
        assert _read_raw_settings(lkg) == lkg_rows

    def test_foreign_healthy_candidate_rejected(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state(volume=20))
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_raw_settings(lkg)["volume"] == "20"
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _write_raw_rows(candidate, _foreign_candidate_rows())
        assert (
            SQLiteSettingsRepository.inspect_path(candidate).health
            is PersistenceHealth.HEALTHY
        )
        candidate_before = candidate.read_bytes()
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()
        assert not db.exists()

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.read_bytes() == candidate_before
        assert lkg.read_bytes() == lkg_before
        assert not db.exists()
        assert not Path(str(db) + ".quarantine").exists()

    def test_healthy_candidate_without_lkg_blocked(self, tmp_path):
        db = tmp_path / "michi.db"
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _write_raw_rows(candidate, _foreign_candidate_rows())
        assert (
            SQLiteSettingsRepository.inspect_path(candidate).health
            is PersistenceHealth.HEALTHY
        )
        candidate_before = candidate.read_bytes()
        assert not SQLiteSettingsRepository.last_known_good_path(db).exists()

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.exists()
        assert candidate.read_bytes() == candidate_before
        assert not db.exists()

    def test_candidate_with_unhealthy_lkg_blocked(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _write_raw_rows(candidate, _foreign_candidate_rows())
        candidate_before = candidate.read_bytes()
        _remove_wal_sidecars(lkg)
        lkg.write_bytes(b"THIS IS NOT SQLITE")
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.read_bytes() == candidate_before
        assert lkg.read_bytes() == lkg_before
        assert not db.exists()

    def test_candidate_with_sidecars_blocked(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _write_raw_rows(candidate, _foreign_candidate_rows())
        candidate_wal = Path(str(candidate) + "-wal")
        candidate_wal.write_bytes(b"NOT A WAL FILE")
        wal_before = candidate_wal.read_bytes()
        candidate_before = candidate.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate_wal.exists()
        assert candidate_wal.read_bytes() == wal_before
        assert candidate.exists()
        assert candidate.read_bytes() == candidate_before
        assert not db.exists()

    def test_logical_equality_physical_difference_accepted(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        conn = sqlite3.connect(str(candidate))
        try:
            conn.execute("PRAGMA page_size=512")
            conn.execute(
                "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT OR REPLACE INTO settings VALUES (?, ?)",
                list(lkg_rows.items()),
            )
            conn.commit()
        finally:
            conn.close()
        assert (
            SQLiteSettingsRepository.inspect_path(candidate).health
            is PersistenceHealth.HEALTHY
        )
        assert candidate.read_bytes() != lkg.read_bytes()
        assert _read_raw_settings(candidate) == _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        db.unlink()
        assert not db.exists()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == _read_raw_settings(lkg)
        assert not candidate.exists()


class TestQuarantine:
    def test_quarantine_multiple_generations(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        qroot = Path(str(db) + ".quarantine")
        old_gen = qroot / "recovery-old"
        old_gen.mkdir(parents=True)
        keep = old_gen / "keep.txt"
        keep.write_text("precious")
        keep_before = keep.read_bytes()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        generations = _quarantine_generations(db)
        names = [g.name for g in generations]
        assert "recovery-old" in names
        assert len(generations) == 2
        assert keep.read_bytes() == keep_before
        new_gens = [g for g in generations if g.name != "recovery-old"]
        assert len(new_gens) == 1

    def test_quarantine_main_byte_exact(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        original_sha = _sha256(db)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        assert _sha256(files[0]) == original_sha

    def test_quarantine_wal_shm_byte_exact(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        # Flush the primary's WAL into the main file first so the holder's
        # committed frames are the ONLY WAL content (pages other than page 1).
        # Otherwise a complete WAL would heal the corrupted main file and the
        # primary would classify HEALTHY instead of CORRUPT_DATABASE.
        with sqlite3.connect(str(db)) as conn:
            conn.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        holder = sqlite3.connect(str(db))
        try:
            holder.execute("INSERT OR REPLACE INTO settings VALUES ('probe', '1')")
            holder.commit()
            wal = Path(str(db) + "-wal")
            shm = Path(str(db) + "-shm")
            assert wal.exists()
            assert shm.exists()
            wal_sha = _sha256(wal)
            db.write_bytes(b"THIS IS NOT SQLITE - corrupt after WAL snapshot")
            corrupt_sha = _sha256(db)

            replace_calls = []
            orig_replace = os.replace

            def spy_replace(src, dst):
                replace_calls.append((src, dst))
                assert not Path(str(db) + "-wal").exists()
                assert not Path(str(db) + "-shm").exists()
                return orig_replace(src, dst)

            monkeypatch.setattr(sqlite_settings_mod.os, "replace", spy_replace)

            repo = SQLiteSettingsRepository.open_for_startup(db)

            assert isinstance(repo, SQLiteSettingsRepository)
            assert (
                SQLiteSettingsRepository.inspect_path(db).health
                is PersistenceHealth.HEALTHY
            )
            assert repo.load() == _healthy_state()
            # NOTE (M11.2E deviation): no post-recovery -wal/-shm absence assert
            # here. The installed primary is WAL-mode by construction (the
            # backup API copies the WAL header bit end-to-end), so ANY open —
            # including the test's own inspect_path/load above — recreates
            # legitimate WAL sidecars. WP §64 scopes stale-sidecar absence to
            # the install boundary, which is proven by the asserts inside the
            # os.replace spy above.
            assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
            assert len(replace_calls) == 1
            assert _read_raw_settings(lkg) == lkg_rows

            generations = _quarantine_generations(db)
            assert len(generations) == 1
            gen_files = [p for p in generations[0].iterdir() if p.is_file()]
            assert len(gen_files) == 3
            shas = {_sha256(p) for p in gen_files}
            assert corrupt_sha in shas
            assert wal_sha in shas
            # NOTE (M11.2E deviation): the quarantined -shm is NOT asserted
            # byte-exact. SQLite rewrites the shared-memory index (-shm) on
            # ANY open of a WAL-mode database — including the read-only
            # inspect_path() that classifies the corrupt primary, even when
            # the main header fails. The quarantine preserves the -shm as it
            # exists at quarantine time (verified size+SHA against the live
            # artifact), but the pre-open bytes are unrecoverable by
            # construction. Byte-exact evidence is asserted for the main
            # database (corrupt_sha) and the -wal committed frames (wal_sha).
        finally:
            holder.close()

    def test_quarantine_copy_failure_aborts(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        primary_before = db.read_bytes()
        assert not Path(str(db) + "-wal").exists()
        assert not Path(str(db) + "-shm").exists()
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        assert not candidate.exists()

        def fail_copy(*_args, **_kwargs):
            raise OSError(errno.EIO, "forced")

        monkeypatch.setattr(
            sqlite_settings_mod, "_copy_file_exclusive", fail_copy, raising=False
        )
        replace_calls = []
        orig_replace = os.replace

        def spy_replace(src, dst):
            replace_calls.append((src, dst))
            return orig_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert db.read_bytes() == primary_before
        assert not Path(str(db) + "-wal").exists()
        assert not Path(str(db) + "-shm").exists()
        assert not candidate.exists()
        assert lkg.read_bytes() == lkg_before
        assert replace_calls == []

    def test_sidecar_strict_removal_failure_aborts(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        primary_before = db.read_bytes()
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        assert not candidate.exists()

        def fail_strict(*_args, **_kwargs):
            raise OSError(errno.EIO, "forced")

        monkeypatch.setattr(
            sqlite_settings_mod,
            "_remove_sqlite_sidecars_strict",
            fail_strict,
            raising=False,
        )

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.exists()
        assert db.read_bytes() == primary_before
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        assert lkg.read_bytes() == lkg_before

    def test_os_replace_failure_aborts(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        primary_before = db.read_bytes()
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        assert not candidate.exists()

        replace_calls = []

        def fail_replace(src, dst):
            replace_calls.append((src, dst))
            raise OSError(errno.EIO, "forced replace failure")

        monkeypatch.setattr(os, "replace", fail_replace)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.exists()
        assert db.read_bytes() == primary_before
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        assert lkg.read_bytes() == lkg_before
        assert len(replace_calls) == 1


class TestInstallOrdering:
    def test_post_install_ordering(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        events = []

        orig_inspect = SQLiteSettingsRepository.inspect_path

        def spy_inspect(path):
            events.append(("inspect", path))
            return orig_inspect(path)

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", spy_inspect)

        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)

        def spy_quarantine(*_args, **_kwargs):
            events.append("quarantine")

        monkeypatch.setattr(
            sqlite_settings_mod,
            "_quarantine_primary_artifacts",
            spy_quarantine,
            raising=False,
        )

        def spy_strict_remove(*_args, **_kwargs):
            events.append("strict-remove")

        monkeypatch.setattr(
            sqlite_settings_mod,
            "_remove_sqlite_sidecars_strict",
            spy_strict_remove,
            raising=False,
        )

        orig_replace = os.replace

        def spy_replace(src, dst):
            events.append("replace")
            return orig_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert events[0] == ("inspect", db)
        final_inspect_primary = max(
            i for i, e in enumerate(events) if e == ("inspect", db)
        )
        assert (
            events.index("quarantine")
            < events.index("strict-remove")
            < events.index("replace")
            < final_inspect_primary
            < events.index("writable-init")
        )


class TestMissingOrphanSidecars:
    def test_missing_orphan_sidecars_no_lkg_blocked(self, tmp_path):
        db = tmp_path / "michi.db"
        assert not db.exists()
        wal = Path(str(db) + "-wal")
        shm = Path(str(db) + "-shm")
        wal.write_bytes(b"ORPHAN WAL BYTES")
        shm.write_bytes(b"ORPHAN SHM BYTES")
        wal_before = wal.read_bytes()
        shm_before = shm.read_bytes()
        assert not SQLiteSettingsRepository.last_known_good_path(db).exists()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert not db.exists()
        assert wal.read_bytes() == wal_before
        assert shm.read_bytes() == shm_before
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_missing_orphan_sidecars_with_lkg_recovers(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        wal = Path(str(db) + "-wal")
        shm = Path(str(db) + "-shm")
        wal.write_bytes(b"ORPHAN WAL BYTES")
        shm.write_bytes(b"ORPHAN SHM BYTES")
        wal_sha = _sha256(wal)
        shm_sha = _sha256(shm)
        db.unlink()
        assert not db.exists()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert repo.load() == _healthy_state()
        # NOTE (M11.2E deviation): no post-recovery -wal/-shm absence assert
        # here. The installed primary is WAL-mode by construction (the backup
        # API copies the WAL header bit end-to-end), so ANY open — including
        # the test's own inspect_path/load above — recreates legitimate WAL
        # sidecars. WP §64 scopes stale-sidecar absence to the install
        # boundary (proven by the os.replace spy in the WAL/shm test); here
        # the orphan sidecars are quarantined byte-exact and strictly removed
        # before install.
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        assert _read_raw_settings(lkg) == lkg_rows
        assert lkg.read_bytes() == lkg_before

        generations = _quarantine_generations(db)
        assert len(generations) == 1
        gen_files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(gen_files) == 2
        shas = {_sha256(p) for p in gen_files}
        assert wal_sha in shas
        assert shm_sha in shas


class TestTerminalStates:
    @pytest.mark.parametrize(
        "health",
        [
            PersistenceHealth.LOCKED,
            PersistenceHealth.ACCESS_FAILURE,
            PersistenceHealth.IO_FAILURE,
            PersistenceHealth.UNKNOWN_FAILURE,
        ],
        ids=["locked", "access", "io", "unknown"],
    )
    def test_terminal_states_never_recover_even_with_material(
        self, tmp_path, monkeypatch, health
    ):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        assert (
            SQLiteSettingsRepository.stage_recovery_from_last_known_good(
                db, candidate
            ).health
            is PersistenceHealth.HEALTHY
        )
        candidate_before = candidate.read_bytes()
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")

        def forced_inspect(path):
            return PersistenceDiagnostic(health, "forced")

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", forced_inspect)
        stage_spy = CallSpy()
        quarantine_spy = CallSpy()
        init_spy = CallSpy()
        replace_calls = []

        def spy_replace(src, dst):
            replace_calls.append((src, dst))

        monkeypatch.setattr(
            SQLiteSettingsRepository, "stage_recovery_from_last_known_good", stage_spy
        )
        monkeypatch.setattr(
            sqlite_settings_mod,
            "_quarantine_primary_artifacts",
            quarantine_spy,
            raising=False,
        )
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)
        monkeypatch.setattr(os, "replace", spy_replace)

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert exc_info.value.primary_diagnostic.health is health
        assert stage_spy.calls == []
        assert quarantine_spy.calls == []
        assert replace_calls == []
        assert init_spy.calls == []
        assert candidate.read_bytes() == candidate_before
        assert lkg.read_bytes() == lkg_before
        assert not Path(str(db) + ".quarantine").exists()


class TestRecoveryWarningsAndPreservation:
    def test_recovery_warning_emitted(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")

        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.sqlite_settings"
        ):
            repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        quarantine_root = str(SQLiteSettingsRepository.quarantine_root_path(db))
        warnings = [r.message for r in caplog.records if r.levelno >= logging.WARNING]
        assert any("CORRUPT_DATABASE" in m and quarantine_root in m for m in warnings)

    @pytest.mark.parametrize(
        "scenario", ["corrupt", "missing"], ids=["corrupt", "missing"]
    )
    def test_lkg_preserved_all_paths(self, tmp_path, scenario):
        db = tmp_path / f"michi-{scenario}.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        if scenario == "corrupt":
            db.write_bytes(b"THIS IS NOT SQLITE")
        else:
            db.unlink()

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(lkg) == lkg_rows
        assert lkg.read_bytes() == lkg_before


class TestLkgWalPreservation:
    def test_recovery_preserves_committed_uncheckpointed_lkg_wal_state(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(_healthy_state(volume=20))
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_raw_settings(lkg)["volume"] == "20"

        # Commit a NEWER LKG state into its WAL, held uncheckpointed. The
        # holder stays open through the whole recovery (established pattern:
        # see test_quarantine_wal_shm_byte_exact), so the committed view never
        # checkpoints into the LKG main file.
        holder = sqlite3.connect(str(lkg))
        try:
            holder.execute("PRAGMA journal_mode=WAL")
            holder.execute("PRAGMA wal_autocheckpoint=0")
            holder.execute("UPDATE settings SET value='80' WHERE key='volume'")
            holder.commit()
            wal = Path(str(lkg) + "-wal")
            assert wal.exists()
            assert wal.stat().st_size > 0
            assert (
                holder.execute(
                    "SELECT value FROM settings WHERE key='volume'"
                ).fetchone()[0]
                == "80"
            )
            # Read-only connections see the WAL view; the LKG is still healthy.
            assert _read_raw_settings(lkg)["volume"] == "80"
            assert (
                SQLiteSettingsRepository.inspect_path(lkg).health
                is PersistenceHealth.HEALTHY
            )

            # Make the primary recoverable (CORRUPT_DATABASE).
            _remove_wal_sidecars(db)
            db.write_bytes(b"THIS IS NOT SQLITE")

            recovered = SQLiteSettingsRepository.open_for_startup(db)

            assert (
                SQLiteSettingsRepository.inspect_path(db).health
                is PersistenceHealth.HEALTHY
            )
            # KEY ASSERTION: recovery must restore the WAL-visible LKG state
            # (80), NOT the stale LKG main-file state (20).
            assert recovered.load().volume == 80
            assert _read_raw_settings(db)["volume"] == "80"
            # Candidate consumed on success.
            assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
            # LKG logical state survives recovery (WAL never deleted).
            assert _read_raw_settings(lkg)["volume"] == "80"
            # NOTE: pre-fix SQLite may RECREATE an empty wal file here, so the
            # state asserts above are the discriminators; this existence assert
            # documents that recovery must not delete the LKG WAL as
            # housekeeping.
            assert wal.exists()
        finally:
            holder.close()


class TestQuarantineRootContract:
    def test_quarantine_root_regular_file_blocks(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")
        primary_before = db.read_bytes()
        qroot = Path(str(db) + ".quarantine")
        qroot.write_text("I am a file, not a directory")
        qroot_before = qroot.read_bytes()

        replace_calls = []
        orig_replace = os.replace

        def spy_replace(src, dst):
            replace_calls.append((src, dst))
            return orig_replace(src, dst)

        monkeypatch.setattr(os, "replace", spy_replace)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert qroot.read_bytes() == qroot_before
        assert db.read_bytes() == primary_before
        assert replace_calls == []

    def test_quarantine_root_permissions(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _remove_wal_sidecars(db)
        db.write_bytes(b"THIS IS NOT SQLITE")

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        qroot = Path(str(db) + ".quarantine")
        assert qroot.is_dir()
        assert stat.S_IMODE(qroot.stat().st_mode) & 0o077 == 0
        generations = _quarantine_generations(db)
        assert len(generations) == 1
        assert stat.S_IMODE(generations[0].stat().st_mode) & 0o077 == 0
        files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(files) == 1
        for f in files:
            assert stat.S_IMODE(f.stat().st_mode) & 0o077 == 0
