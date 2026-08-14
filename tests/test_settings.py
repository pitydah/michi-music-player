"""Tests for SQLite settings persistence."""

import json
import logging
import sqlite3

import pytest

from michi.application.settings_service import SettingsService
from michi.domain.persistence_health import PersistenceHealth
from michi.domain.settings import SettingsState
from michi.infrastructure.sqlite_settings import SQLiteSettingsRepository

_LOGGER_NAME = "michi.infrastructure.sqlite_settings"


def _write_raw_rows(db_path, rows):
    """Fabricate DB state using controlled raw SQL (test-only)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _read_raw_rows(db_path):
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        return conn.execute("SELECT key, value FROM settings").fetchall()


def _warnings(caplog, key):
    return [r.getMessage() for r in caplog.records if f"'{key}'" in r.getMessage()]


def _expect_warning_logging(caplog):
    caplog.set_level(logging.WARNING, logger=_LOGGER_NAME)


class TestSQLiteSettings:
    def test_defaults_on_new_db(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "test.db")
        state = repo.load()
        assert state.volume == 80
        assert state.muted is False

    def test_save_and_reload(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "test.db")
        state = SettingsState(volume=42, muted=True, last_directory="/music")
        repo.save(state)

        loaded = repo.load()
        assert loaded.volume == 42
        assert loaded.muted is True
        assert loaded.last_directory == "/music"

    def test_reopen_preserves_data(self, tmp_path):
        db_path = tmp_path / "test.db"
        repo1 = SQLiteSettingsRepository(db_path)
        repo1.save(SettingsState(volume=33))

        repo2 = SQLiteSettingsRepository(db_path)
        assert repo2.load().volume == 33


class TestMalformedFieldRecovery:
    """M11.2C — per-field malformed-data recovery on load()."""

    def test_volume_malformed_isolated_siblings_preserved(self, tmp_path, caplog):
        db = tmp_path / "a.db"
        _write_raw_rows(
            db,
            [
                ("volume", "not-an-int"),
                ("muted", "true"),
                ("last_directory", "/music"),
                ("recent_files", json.dumps(["a.flac"])),
            ],
        )
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.volume == 80
        assert state.muted is True
        assert state.last_directory == "/music"
        assert state.recent_files == ["a.flac"]
        msgs = _warnings(caplog, "volume")
        assert len(msgs) == 1
        assert "80" in msgs[0]

    @pytest.mark.parametrize("raw", ["-1", "101"])
    def test_volume_out_of_range_falls_back(self, tmp_path, caplog, raw):
        db = tmp_path / "b.db"
        _write_raw_rows(db, [("volume", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.volume == 80
        msgs = _warnings(caplog, "volume")
        assert len(msgs) == 1
        assert "80" in msgs[0]

    @pytest.mark.parametrize("raw", ["", "80.5"])
    def test_volume_invalid_format_falls_back(self, tmp_path, caplog, raw):
        db = tmp_path / "c.db"
        _write_raw_rows(db, [("volume", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.volume == 80
        msgs = _warnings(caplog, "volume")
        assert len(msgs) == 1
        assert "80" in msgs[0]

    @pytest.mark.parametrize("raw,expected", [("0", 0), ("80", 80), ("100", 100)])
    def test_volume_boundaries_load(self, tmp_path, caplog, raw, expected):
        db = tmp_path / "d.db"
        _write_raw_rows(db, [("volume", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.volume == expected
        assert _warnings(caplog, "volume") == []

    @pytest.mark.parametrize("raw", ["", "1", "0", "2", "-1", "yes", "no"])
    def test_muted_invalid_falls_back_with_warning(self, tmp_path, caplog, raw):
        db = tmp_path / "e.db"
        _write_raw_rows(
            db,
            [
                ("muted", raw),
                ("volume", "55"),
                ("last_directory", "/music"),
                ("recent_files", json.dumps(["a.flac"])),
            ],
        )
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.muted is False
        assert state.volume == 55
        assert state.last_directory == "/music"
        assert state.recent_files == ["a.flac"]
        msgs = _warnings(caplog, "muted")
        assert len(msgs) == 1
        assert "False" in msgs[0]

    @pytest.mark.parametrize(
        "raw,expected",
        [("true", True), ("false", False)],
    )
    def test_muted_valid_values_load(self, tmp_path, caplog, raw, expected):
        db = tmp_path / "f.db"
        _write_raw_rows(db, [("muted", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.muted is expected
        assert _warnings(caplog, "muted") == []

    def test_last_directory_preserved_exactly(self, tmp_path, caplog):
        db = tmp_path / "g1.db"
        raw = "/media/  música/ñandú~files/"
        _write_raw_rows(db, [("last_directory", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.last_directory == raw
        assert _warnings(caplog, "last_directory") == []

    def test_last_directory_blob_falls_back(self, tmp_path, caplog):
        db = tmp_path / "g2.db"
        _write_raw_rows(db, [("last_directory", b"\xff\x00\x01binary")])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.last_directory == ""
        msgs = _warnings(caplog, "last_directory")
        assert len(msgs) == 1

    def test_recent_files_bad_json_falls_back(self, tmp_path, caplog):
        db = tmp_path / "h.db"
        _write_raw_rows(db, [("recent_files", "[broken")])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.recent_files == []
        assert len(_warnings(caplog, "recent_files")) == 1

    def test_recent_files_object_falls_back(self, tmp_path, caplog):
        db = tmp_path / "i.db"
        _write_raw_rows(db, [("recent_files", json.dumps({"a": 1}))])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.recent_files == []
        assert len(_warnings(caplog, "recent_files")) == 1

    def test_recent_files_scalar_falls_back(self, tmp_path, caplog):
        db = tmp_path / "j.db"
        _write_raw_rows(db, [("recent_files", json.dumps("just a string"))])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.recent_files == []
        assert len(_warnings(caplog, "recent_files")) == 1

    @pytest.mark.parametrize("raw", [json.dumps(["a.flac", 123]), json.dumps([None])])
    def test_recent_files_mixed_array_falls_back_no_coercion(
        self, tmp_path, caplog, raw
    ):
        db = tmp_path / "k.db"
        _write_raw_rows(db, [("recent_files", raw)])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.recent_files == []
        assert len(_warnings(caplog, "recent_files")) == 1

    def test_recent_files_valid_list_preserved(self, tmp_path, caplog):
        db = tmp_path / "l.db"
        _write_raw_rows(db, [("recent_files", json.dumps(["a.flac", "b.flac"]))])
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.recent_files == ["a.flac", "b.flac"]
        assert _warnings(caplog, "recent_files") == []

    @pytest.mark.parametrize(
        "missing_key", ["volume", "muted", "last_directory", "recent_files"]
    )
    def test_missing_key_uses_domain_default_no_warning(
        self, tmp_path, caplog, missing_key
    ):
        db = tmp_path / "m.db"
        decoded = {
            "volume": 42,
            "muted": True,
            "last_directory": "/x",
            "recent_files": ["a"],
        }
        raws = {
            "volume": "42",
            "muted": "true",
            "last_directory": "/x",
            "recent_files": json.dumps(["a"]),
        }
        defaults = {
            "volume": 80,
            "muted": False,
            "last_directory": "",
            "recent_files": [],
        }
        rows = [(k, raws[k]) for k in raws if k != missing_key]
        _write_raw_rows(db, rows)
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert getattr(state, missing_key) == defaults[missing_key]
        for key in decoded:
            if key != missing_key:
                assert getattr(state, key) == decoded[key]
        assert caplog.records == []

    def test_all_fields_malformed_each_recovers_with_one_warning(
        self, tmp_path, caplog
    ):
        db = tmp_path / "n.db"
        _write_raw_rows(
            db,
            [
                ("volume", "abc"),
                ("muted", "yes"),
                ("last_directory", b"\x00blob"),
                ("recent_files", "{broken"),
            ],
        )
        _expect_warning_logging(caplog)
        state = SQLiteSettingsRepository(db).load()
        assert state.volume == 80
        assert state.muted is False
        assert state.last_directory == ""
        assert state.recent_files == []
        for key in ("volume", "muted", "last_directory", "recent_files"):
            assert len(_warnings(caplog, key)) == 1

    def test_repeated_load_deterministic_no_mutation(self, tmp_path):
        db = tmp_path / "o.db"
        _write_raw_rows(
            db,
            [
                ("volume", "abc"),
                ("muted", "true"),
                ("recent_files", json.dumps(["x.flac"])),
            ],
        )
        repo = SQLiteSettingsRepository(db)
        before = _read_raw_rows(db)
        first = repo.load()
        second = repo.load()
        assert first == second
        assert first.volume == 80
        assert _read_raw_rows(db) == before

    def test_settings_service_state_identity_across_load(self, tmp_path):
        repo = SQLiteSettingsRepository(tmp_path / "p.db")
        service = SettingsService(repo)
        loaded = service.load()
        assert service.state is loaded

    def test_load_never_writes_back_malformed_values(self, tmp_path):
        db = tmp_path / "q.db"
        _write_raw_rows(
            db,
            [
                ("volume", "broken"),
                ("muted", "1"),
                ("last_directory", "/music"),
                ("recent_files", json.dumps(["a.flac"])),
            ],
        )
        repo = SQLiteSettingsRepository(db)
        before = _read_raw_rows(db)
        state = repo.load()
        assert state.volume == 80
        assert state.muted is False
        assert _read_raw_rows(db) == before
        assert dict(before)["volume"] == "broken"
        assert dict(before)["muted"] == "1"

    @pytest.mark.parametrize(
        "rows",
        [
            [("volume", "abc")],
            [("muted", "maybe")],
            [("recent_files", "{broken")],
        ],
    )
    def test_malformed_fields_still_classified_malformed_data(self, tmp_path, rows):
        db = tmp_path / "r.db"
        _write_raw_rows(db, rows)
        result = SQLiteSettingsRepository.inspect_path(db)
        assert result.health is PersistenceHealth.MALFORMED_DATA

    def test_operational_error_during_load_propagates(self, tmp_path):
        db = tmp_path / "s.db"
        repo = SQLiteSettingsRepository(db)
        with sqlite3.connect(str(db)) as conn:
            conn.execute("DROP TABLE settings")
        with pytest.raises(sqlite3.OperationalError):
            repo.load()


class TestMutedCanonicalContract:
    """M11.2C final — load() and inspect_path() agree on canonical muted."""

    _VALID_SIBLINGS = [
        ("volume", "55"),
        ("last_directory", "/music"),
        ("recent_files", json.dumps(["a.flac"])),
    ]

    @pytest.mark.parametrize("raw", ["1", "0"])
    def test_non_canonical_muted_disagrees_load_health(self, tmp_path, caplog, raw):
        db = tmp_path / "u1.db"
        _write_raw_rows(db, [("muted", raw)] + self._VALID_SIBLINGS)
        _expect_warning_logging(caplog)
        repo = SQLiteSettingsRepository(db)
        state = repo.load()
        assert state.muted is False
        assert state.volume == 55
        assert state.last_directory == "/music"
        assert state.recent_files == ["a.flac"]
        msgs = _warnings(caplog, "muted")
        assert len(msgs) == 1
        assert "False" in msgs[0]
        diag = SQLiteSettingsRepository.inspect_path(db)
        assert diag.health is PersistenceHealth.MALFORMED_DATA
        assert dict(_read_raw_rows(db))["muted"] == raw

    def test_canonical_true_roundtrip(self, tmp_path, caplog):
        db = tmp_path / "u2.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(muted=True))
        assert dict(_read_raw_rows(db))["muted"] == "true"
        _expect_warning_logging(caplog)
        state = repo.load()
        assert state.muted is True
        assert _warnings(caplog, "muted") == []
        diag = SQLiteSettingsRepository.inspect_path(db)
        assert diag.health is PersistenceHealth.HEALTHY

    def test_canonical_false_roundtrip(self, tmp_path, caplog):
        db = tmp_path / "u3.db"
        repo = SQLiteSettingsRepository(db)
        repo.save(SettingsState(muted=False))
        assert dict(_read_raw_rows(db))["muted"] == "false"
        _expect_warning_logging(caplog)
        state = repo.load()
        assert state.muted is False
        assert _warnings(caplog, "muted") == []
        diag = SQLiteSettingsRepository.inspect_path(db)
        assert diag.health is PersistenceHealth.HEALTHY

    @pytest.mark.parametrize(
        "raw,expected,healthy",
        [
            ("true", True, True),
            ("false", False, True),
            ("1", False, False),
            ("0", False, False),
        ],
    )
    def test_load_health_four_way_matrix(
        self, tmp_path, caplog, raw, expected, healthy
    ):
        db = tmp_path / "u4.db"
        _write_raw_rows(db, [("muted", raw)])
        _expect_warning_logging(caplog)
        repo = SQLiteSettingsRepository(db)
        state = repo.load()
        assert state.muted is expected
        assert len(_warnings(caplog, "muted")) == (0 if healthy else 1)
        diag = SQLiteSettingsRepository.inspect_path(db)
        expected_health = (
            PersistenceHealth.HEALTHY if healthy else PersistenceHealth.MALFORMED_DATA
        )
        assert diag.health is expected_health

    def test_zero_writeback_for_muted_raw_one(self, tmp_path):
        db = tmp_path / "u5.db"
        _write_raw_rows(db, [("muted", "1")] + self._VALID_SIBLINGS)
        repo = SQLiteSettingsRepository(db)
        before = _read_raw_rows(db)
        state = repo.load()
        assert state.muted is False
        assert _read_raw_rows(db) == before
        assert dict(before)["muted"] == "1"
