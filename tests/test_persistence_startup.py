"""M11.2D startup preflight + recovery routing tests — real SQLite + tmp files."""

import errno
import logging
import os
import sqlite3
from pathlib import Path

import pytest

import michi.bootstrap as bootstrap
from michi.bootstrap import ApplicationContainer
from michi.domain.persistence_health import (
    PersistenceDiagnostic,
    PersistenceHealth,
)
from michi.domain.settings import SettingsState
from michi.infrastructure import sqlite_settings as sqlite_settings_mod
from michi.infrastructure.sqlite_settings import (
    PersistenceStartupError,
    SQLiteSettingsRepository,
)
from tests.conftest import FakeSettingsRepo


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


def _corrupt_primary(db_path, payload=b"THIS IS NOT SQLITE"):
    """Overwrite the primary with garbage on a NEW inode (os.replace).

    A lingering WAL-mode connection from a preceding test in the same
    process may finalize (GC) after the corruption and checkpoint through
    its OLD inode, resurrecting a healthy DB over in-place write_bytes.
    Replacing the path with a fresh inode makes such close-time writes
    harmless (they land on the unlinked old inode)."""
    _remove_wal_sidecars(db_path)
    tmp = Path(str(db_path) + ".corrupt-tmp")
    tmp.write_bytes(payload)
    os.replace(tmp, db_path)
    return payload


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


class CallSpy:
    def __init__(self, result=None):
        self.calls = []
        self.result = result

    def __call__(self, *args, **kwargs):
        self.calls.append((args, kwargs))
        return self.result


class TestHealthyStartup:
    def test_healthy_primary_startup_order_and_settings(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        SQLiteSettingsRepository(db).save(_healthy_state(volume=73, muted=False))
        events = []

        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)

        orig_refresh = SQLiteSettingsRepository.refresh_last_known_good

        def spy_refresh(path):
            events.append("refresh")
            return orig_refresh(path)

        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", spy_refresh
        )

        orig_inspect = SQLiteSettingsRepository.inspect_path

        def spy_inspect(path):
            events.append("inspect")
            return orig_inspect(path)

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", spy_inspect)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        state = repo.load()
        assert state.volume == 73
        assert state.muted is False
        assert events[0] == "inspect"
        assert events[-1] == "writable-init"
        assert events.index("refresh") < events.index("writable-init")
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert lkg.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(lkg).health
            is PersistenceHealth.HEALTHY
        )

    def test_refresh_failure_warns_and_continues(self, tmp_path, monkeypatch, caplog):
        db = tmp_path / "michi.db"
        SQLiteSettingsRepository(db).save(_healthy_state(volume=55, muted=False))
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()

        def fail_refresh(path):
            return PersistenceDiagnostic(
                PersistenceHealth.IO_FAILURE, "forced I/O failure"
            )

        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", fail_refresh
        )
        with caplog.at_level(logging.WARNING):
            repo = SQLiteSettingsRepository.open_for_startup(db)

        assert repo.load().volume == 55
        assert lkg.read_bytes() == lkg_before
        warning_messages = [
            r.message for r in caplog.records if "last-known-good" in r.message
        ]
        assert warning_messages
        assert "IO_FAILURE" in warning_messages[0]
        assert "forced I/O failure" in warning_messages[0]


class TestTrueFirstRun:
    def test_missing_everything_creates_primary(self, tmp_path):
        db = tmp_path / "michi.db"
        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert lkg.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(lkg).health
            is PersistenceHealth.HEALTHY
        )
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        state = repo.load()
        assert state.volume == 80
        assert state.muted is False


class TestMissingPrimaryRecovery:
    def test_missing_with_healthy_lkg_installs_and_starts(self, tmp_path):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        lkg_before = lkg.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()

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

    def test_missing_with_trusted_candidate_installs(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_rows = _read_raw_settings(lkg)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        diag = SQLiteSettingsRepository.stage_recovery_from_last_known_good(
            db, candidate
        )
        assert diag.health is PersistenceHealth.HEALTHY
        _remove_wal_sidecars(db)
        db.unlink()

        stage_spy = CallSpy(
            result=PersistenceDiagnostic(PersistenceHealth.HEALTHY, "spy")
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert db.exists()
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        # The pre-existing trusted candidate was installed and consumed.
        assert not candidate.exists()
        assert stage_spy.calls == []
        assert _read_raw_settings(lkg) == lkg_rows

    def test_missing_with_foreign_candidate_preserved(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        candidate.write_bytes(b"FOREIGN NOT SQLITE")
        candidate_before = candidate.read_bytes()
        _remove_wal_sidecars(db)
        db.unlink()

        stage_spy = CallSpy(
            result=PersistenceDiagnostic(PersistenceHealth.HEALTHY, "spy")
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )
        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert exc_info.value.recovery_candidate == candidate
        assert candidate.read_bytes() == candidate_before
        assert stage_spy.calls == []
        assert db.exists() is False


class TestFieldMalformedStartup:
    def test_field_malformed_volume_probe_passes(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _write_raw_rows(db, [("volume", "broken"), ("muted", "true")])
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.MALFORMED_DATA
        )

        refresh_spy = CallSpy()
        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
        )

        repo = SQLiteSettingsRepository.open_for_startup(db)
        assert refresh_spy.calls == []
        state = repo.load()
        assert state.volume == 80
        assert state.muted is True
        raw = _read_raw_settings(db)
        assert raw["volume"] == "broken"

    def test_field_malformed_muted_probe_passes(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _write_raw_rows(db, [("muted", "1")])
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.MALFORMED_DATA
        )

        with caplog.at_level(logging.WARNING):
            repo = SQLiteSettingsRepository.open_for_startup(db)
            state = repo.load()
        assert state.muted is False
        assert _read_raw_settings(db)["muted"] == "1"
        assert any("muted" in r.message for r in caplog.records)


class TestStructuralMalformedRouting:
    def test_missing_settings_table_no_lkg_errors(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE other (x INTEGER)")
        primary_before = db.read_bytes()

        init_spy = CallSpy()
        refresh_spy = CallSpy()
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)
        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
        )

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health is PersistenceHealth.MALFORMED_DATA
        )
        assert db.read_bytes() == primary_before
        assert init_spy.calls == []
        assert refresh_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_missing_settings_table_with_lkg_recovers(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        lkg_rows = _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        db.unlink()
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE other (x INTEGER)")
        primary_before = db.read_bytes()

        events = []
        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        # Constructor fired exactly once, only after a healthy verified install.
        assert events == ["writable-init"]
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        assert lkg.read_bytes() == lkg_before
        # The malformed primary was quarantined byte-exact (one generation).
        qroot = Path(str(db) + ".quarantine")
        generations = [p for p in qroot.iterdir() if p.name.startswith("recovery-")]
        assert len(generations) == 1
        gen_files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(gen_files) == 1
        assert gen_files[0].read_bytes() == primary_before

    def test_wrong_columns_no_lkg_errors(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY)")
        primary_before = db.read_bytes()

        init_spy = CallSpy()
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health is PersistenceHealth.MALFORMED_DATA
        )
        assert db.read_bytes() == primary_before
        assert init_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_wrong_columns_with_lkg_recovers(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        lkg_rows = _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        db.unlink()
        with sqlite3.connect(str(db)) as conn:
            conn.execute("CREATE TABLE settings (key TEXT PRIMARY KEY)")
        primary_before = db.read_bytes()

        events = []
        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        # Constructor fired exactly once, only after a healthy verified install.
        assert events == ["writable-init"]
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        assert lkg.read_bytes() == lkg_before
        # The malformed primary was quarantined byte-exact (one generation).
        qroot = Path(str(db) + ".quarantine")
        generations = [p for p in qroot.iterdir() if p.name.startswith("recovery-")]
        assert len(generations) == 1
        gen_files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(gen_files) == 1
        assert gen_files[0].read_bytes() == primary_before


class TestMalformedProbeOperationalFailure:
    """MALFORMED_DATA primary whose structural probe hits an operational failure.

    The probe failure must be reclassified through the taxonomy (LOCKED /
    ACCESS_FAILURE / IO_FAILURE / UNKNOWN_FAILURE) and must NOT fall back to
    recovery routing or a writable open.
    """

    def test_probe_lock_routes_locked(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _write_raw_rows(db, [("volume", "ok")])
        holder = sqlite3.connect(str(db))
        holder.execute("BEGIN EXCLUSIVE")
        try:

            def forced_inspect(path):
                return PersistenceDiagnostic(PersistenceHealth.MALFORMED_DATA, "forced")

            monkeypatch.setattr(
                SQLiteSettingsRepository, "inspect_path", forced_inspect
            )
            refresh_spy = CallSpy()
            stage_spy = CallSpy()
            init_spy = CallSpy()
            monkeypatch.setattr(
                SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
            )
            monkeypatch.setattr(
                SQLiteSettingsRepository,
                "stage_recovery_from_last_known_good",
                stage_spy,
            )
            monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

            with pytest.raises(PersistenceStartupError) as exc_info:
                SQLiteSettingsRepository.open_for_startup(db)

            assert exc_info.value.primary_diagnostic.health is PersistenceHealth.LOCKED
            assert refresh_spy.calls == []
            assert stage_spy.calls == []
            assert init_spy.calls == []
            assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()
        finally:
            holder.close()

    def test_probe_missing_file_routes_access_failure(self, tmp_path, monkeypatch):
        db = tmp_path / "does-not-exist.db"

        def forced_inspect(path):
            return PersistenceDiagnostic(PersistenceHealth.MALFORMED_DATA, "forced")

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", forced_inspect)
        refresh_spy = CallSpy()
        stage_spy = CallSpy()
        init_spy = CallSpy()
        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health is PersistenceHealth.ACCESS_FAILURE
        )
        assert refresh_spy.calls == []
        assert stage_spy.calls == []
        assert init_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_probe_os_error_routes_io_failure(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _write_raw_rows(db, [("volume", "ok")])

        def forced_inspect(path):
            return PersistenceDiagnostic(PersistenceHealth.MALFORMED_DATA, "forced")

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", forced_inspect)

        def fail_uri(path):
            raise OSError(errno.EIO, "forced I/O failure")

        monkeypatch.setattr(sqlite_settings_mod, "_read_only_uri", fail_uri)
        refresh_spy = CallSpy()
        stage_spy = CallSpy()
        init_spy = CallSpy()
        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert exc_info.value.primary_diagnostic.health is PersistenceHealth.IO_FAILURE
        assert refresh_spy.calls == []
        assert stage_spy.calls == []
        assert init_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_probe_symlink_loop_routes_unknown_failure(self, tmp_path, monkeypatch):
        # NOTE: on Python 3.11, Path.resolve() turns a symlink loop into a
        # RuntimeError (not OSError ELOOP), so the real loop would escape the
        # probe's `except OSError`. Per the M11.2D design fallback, force the
        # same real OSError(ELOOP) that the loop would produce.
        db = tmp_path / "loop.db"

        def forced_inspect(path):
            return PersistenceDiagnostic(PersistenceHealth.MALFORMED_DATA, "forced")

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", forced_inspect)

        def fail_uri(path):
            raise OSError(errno.ELOOP, "Too many levels of symbolic links")

        monkeypatch.setattr(sqlite_settings_mod, "_read_only_uri", fail_uri)
        refresh_spy = CallSpy()
        stage_spy = CallSpy()
        init_spy = CallSpy()
        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health
            is PersistenceHealth.UNKNOWN_FAILURE
        )
        assert refresh_spy.calls == []
        assert stage_spy.calls == []
        assert init_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()


class TestCorruptRouting:
    def test_corrupt_with_lkg_recovers_and_quarantines(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        lkg_before = lkg.read_bytes()
        lkg_rows = _read_raw_settings(lkg)
        _remove_wal_sidecars(db)
        _corrupt_primary(db)
        primary_before = db.read_bytes()

        events = []
        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)
        orig_stage = SQLiteSettingsRepository.stage_recovery_from_last_known_good
        stage_calls = []

        def spy_stage(path, dest):
            stage_calls.append((path, dest))
            return orig_stage(path, dest)

        monkeypatch.setattr(
            SQLiteSettingsRepository, "stage_recovery_from_last_known_good", spy_stage
        )

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        # Constructor fired exactly once, only after a healthy verified install.
        assert events == ["writable-init"]
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        # No pre-existing candidate: recovery staged it, then installed it.
        assert stage_calls == [(db, candidate)]
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        assert repo.load() == _healthy_state()
        assert not candidate.exists()
        assert lkg.read_bytes() == lkg_before
        # The corrupt primary was quarantined byte-exact (one generation).
        qroot = Path(str(db) + ".quarantine")
        generations = [p for p in qroot.iterdir() if p.name.startswith("recovery-")]
        assert len(generations) == 1
        gen_files = [p for p in generations[0].iterdir() if p.is_file()]
        assert len(gen_files) == 1
        assert gen_files[0].read_bytes() == primary_before

    def test_corrupt_no_lkg_errors(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _corrupt_primary(db)
        primary_before = db.read_bytes()

        init_spy = CallSpy()
        stage_spy = CallSpy(
            result=PersistenceDiagnostic(PersistenceHealth.HEALTHY, "spy")
        )
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )

        with pytest.raises(PersistenceStartupError) as exc_info:
            SQLiteSettingsRepository.open_for_startup(db)

        assert (
            exc_info.value.primary_diagnostic.health
            is PersistenceHealth.CORRUPT_DATABASE
        )
        assert db.read_bytes() == primary_before
        assert init_spy.calls == []
        assert stage_spy.calls == []
        assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()

    def test_corrupt_with_trusted_candidate_recovers(self, tmp_path, monkeypatch):
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
        _corrupt_primary(db)

        stage_spy = CallSpy(
            result=PersistenceDiagnostic(PersistenceHealth.HEALTHY, "spy")
        )
        monkeypatch.setattr(
            SQLiteSettingsRepository,
            "stage_recovery_from_last_known_good",
            stage_spy,
        )

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert (
            SQLiteSettingsRepository.inspect_path(db).health
            is PersistenceHealth.HEALTHY
        )
        assert _read_raw_settings(db) == lkg_rows
        # The pre-existing trusted candidate was installed and consumed.
        assert not candidate.exists()
        assert stage_spy.calls == []
        assert _read_raw_settings(lkg) == lkg_rows


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
def test_terminal_health_never_falls_back(tmp_path, monkeypatch, health):
    db = tmp_path / "michi.db"
    db.write_text("placeholder")

    def forced_inspect(path):
        return PersistenceDiagnostic(health, "forced")

    monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", forced_inspect)
    refresh_spy = CallSpy()
    stage_spy = CallSpy()
    init_spy = CallSpy()
    monkeypatch.setattr(
        SQLiteSettingsRepository, "refresh_last_known_good", refresh_spy
    )
    monkeypatch.setattr(
        SQLiteSettingsRepository, "stage_recovery_from_last_known_good", stage_spy
    )
    monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)

    with pytest.raises(PersistenceStartupError) as exc_info:
        SQLiteSettingsRepository.open_for_startup(db)

    assert exc_info.value.primary_diagnostic.health is health
    assert refresh_spy.calls == []
    assert stage_spy.calls == []
    assert init_spy.calls == []
    assert not SQLiteSettingsRepository.recovery_candidate_path(db).exists()


class TestWriteOrder:
    def test_healthy_order_inspect_refresh_writable(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        SQLiteSettingsRepository(db).save(_healthy_state())
        events = []

        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)

        orig_refresh = SQLiteSettingsRepository.refresh_last_known_good

        def spy_refresh(path):
            events.append("refresh")
            return orig_refresh(path)

        monkeypatch.setattr(
            SQLiteSettingsRepository, "refresh_last_known_good", spy_refresh
        )

        orig_inspect = SQLiteSettingsRepository.inspect_path

        def spy_inspect(path):
            events.append("inspect")
            return orig_inspect(path)

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", spy_inspect)

        SQLiteSettingsRepository.open_for_startup(db)

        assert events[0] == "inspect"
        assert events[-1] == "writable-init"
        assert events.index("refresh") < events.index("writable-init")

    def test_corrupt_order_stages_then_writable(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _make_healthy_with_lkg(db)
        _corrupt_primary(db)
        events = []

        orig_init = SQLiteSettingsRepository.__init__

        def spy_init(self, path):
            events.append("writable-init")
            orig_init(self, path)

        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", spy_init)
        orig_stage = SQLiteSettingsRepository.stage_recovery_from_last_known_good

        def spy_stage(path, dest):
            events.append("stage")
            return orig_stage(path, dest)

        monkeypatch.setattr(
            SQLiteSettingsRepository, "stage_recovery_from_last_known_good", spy_stage
        )
        orig_inspect = SQLiteSettingsRepository.inspect_path

        def spy_inspect(path):
            events.append(("inspect", path))
            return orig_inspect(path)

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", spy_inspect)

        repo = SQLiteSettingsRepository.open_for_startup(db)

        assert isinstance(repo, SQLiteSettingsRepository)
        assert events[0] == ("inspect", db)
        assert "stage" in events
        # No premature writable open: the constructor fires exactly once,
        # strictly after staging and after the final post-install inspect.
        assert events.count("writable-init") == 1
        assert events.index("writable-init") > events.index("stage")
        final_inspect_primary = max(
            i for i, e in enumerate(events) if e == ("inspect", db)
        )
        assert events.index("writable-init") > final_inspect_primary
        assert events[-1] == "writable-init"

    def test_corrupt_no_lkg_order_never_writable(self, tmp_path, monkeypatch):
        db = tmp_path / "michi.db"
        _corrupt_primary(db)
        events = []

        init_spy = CallSpy()
        stage_spy = CallSpy()
        monkeypatch.setattr(SQLiteSettingsRepository, "__init__", init_spy)
        monkeypatch.setattr(
            SQLiteSettingsRepository, "stage_recovery_from_last_known_good", stage_spy
        )
        orig_inspect = SQLiteSettingsRepository.inspect_path

        def spy_inspect(path):
            events.append("inspect")
            return orig_inspect(path)

        monkeypatch.setattr(SQLiteSettingsRepository, "inspect_path", spy_inspect)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert events == ["inspect"]
        assert init_spy.calls == []
        assert stage_spy.calls == []


class FakeQGuiApplication:
    """Minimal QGuiApplication fake for bootstrap startup order tests."""

    @staticmethod
    def setAttribute(*_args, **_kwargs):  # noqa: N802 — Qt API name
        pass

    @staticmethod
    def instance():
        return None

    def __init__(self, _argv):
        pass

    def setApplicationName(self, _name):  # noqa: N802 — Qt API name
        pass

    def setApplicationVersion(self, _version):  # noqa: N802 — Qt API name
        pass

    def setOrganizationName(self, _name):  # noqa: N802 — Qt API name
        pass


class TestBootstrapStartup:
    def test_initialize_uses_open_for_startup_before_backend(
        self, tmp_path, monkeypatch
    ):
        events = []
        monkeypatch.setattr(bootstrap, "_data_dir", lambda: tmp_path)
        monkeypatch.setattr(bootstrap, "QGuiApplication", FakeQGuiApplication)

        def fake_open(db_path):
            events.append("open_for_startup")
            assert db_path == tmp_path / "michi.db"
            return FakeSettingsRepo()

        monkeypatch.setattr(SQLiteSettingsRepository, "open_for_startup", fake_open)

        class BackendBoomError(RuntimeError):
            pass

        def fake_backend():
            events.append("backend")
            raise BackendBoomError("stop here")

        monkeypatch.setattr(bootstrap, "QtMultimediaBackend", fake_backend)

        container = ApplicationContainer()
        with pytest.raises(BackendBoomError):
            container.initialize()
        assert events == ["open_for_startup", "backend"]

    def test_backend_not_constructed_when_preflight_fails(self, tmp_path, monkeypatch):
        monkeypatch.setattr(bootstrap, "_data_dir", lambda: tmp_path)
        monkeypatch.setattr(bootstrap, "QGuiApplication", FakeQGuiApplication)

        def failing_open(db_path):
            raise PersistenceStartupError(
                PersistenceDiagnostic(PersistenceHealth.LOCKED, "locked")
            )

        monkeypatch.setattr(SQLiteSettingsRepository, "open_for_startup", failing_open)

        backend_calls = []

        def fake_backend():
            backend_calls.append(1)
            return object()

        monkeypatch.setattr(bootstrap, "QtMultimediaBackend", fake_backend)

        container = ApplicationContainer()
        with pytest.raises(PersistenceStartupError):
            container.initialize()
        assert backend_calls == []
