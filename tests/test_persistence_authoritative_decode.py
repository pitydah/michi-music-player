"""M6-AUTHORITATIVE-DATA-DECODE-GATE — Phase-1 RED tests.

AUTHORITATIVE user library state (library_prefs: favorites/history/
recently_added; playlists under the same table) must be decoded STRICTLY:

- VALID shapes only: list[str] for the string-list values; a JSON list of
  {"name": str, "track_paths": list[str]} entries for playlists;
- malformed authoritative data NEVER crashes (LOAD NEVER RAISES),
  NEVER fabricates state (a JSON string must never iterate into characters,
  a JSON object must never yield its keys as paths), NEVER partially
  salvages (["A", 42, "B"] -> () — not ("A", "B"));
- provenance table optionality is EXPLICIT: settings is REQUIRED (missing
  -> fail closed), library_prefs is OPTIONAL (pre-M6 compatibility: absent
  == empty); the cache tables stay excluded.

Also encodes the production goldens: malformed favorites/playlists rows in
a healthy database (and after LKG recovery) must let
bootstrap._build_services construct the graph with safe empty fallbacks —
no crash, no fabricated user state.

On the current baseline the scalar/string/object/mixed cases fail at
runtime with TypeError/partial salvage, and a missing settings table is
silently treated as empty — that IS the expected Phase-1 red evidence.
"""

import json
import logging
import sqlite3
from pathlib import Path

import pytest

from michi.domain.library import LibraryPrefs
from michi.domain.persistence_health import PersistenceHealth
from michi.infrastructure import sqlite_settings as sqlite_settings_mod
from michi.infrastructure.library_prefs import SqliteLibraryPrefsRepository
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.infrastructure.sqlite_settings import (
    SQLiteSettingsRepository,
    _candidate_matches_lkg,
    _read_authoritative_state,
)
from tests.conftest import FakeAudioPort
from tests.test_library_incremental import StatScanner

_HEALTHY_SETTINGS = [
    ("schema_version", "1"),
    ("volume", "37"),
    ("theme", "dark"),
    ("muted", "false"),
    ("last_directory", "/m"),
    ("recent_files", json.dumps([])),
]


def _seed_library_prefs(db_path, key, raw):
    """Insert one raw library_prefs row (test-only controlled SQL)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS library_prefs ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute("INSERT OR REPLACE INTO library_prefs VALUES (?, ?)", (key, raw))


def _seed_settings(db_path, rows=_HEALTHY_SETTINGS):
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", rows)


def _prefs_repo(db_path):
    return SqliteLibraryPrefsRepository(db_path)


def _playlists_repo(db_path):
    return SqlitePlaylistsRepository(db_path)


class TestStringListStrict:
    @pytest.mark.parametrize("key", ["favorites", "history", "recently_added"])
    @pytest.mark.parametrize(
        "raw, expected",
        [
            (json.dumps(["A", "B"]), ("A", "B")),
            ("42", ()),  # scalar number
            ('"ABC"', ()),  # JSON string
            ('{"A": true}', ()),  # JSON object
            ("null", ()),
            ("true", ()),
            (json.dumps(["A", 42, "B"]), ()),  # mixed list: WHOLE value rejected
            (json.dumps(["A", None]), ()),
            ("{broken", ()),  # invalid JSON
            ("", ()),
        ],
    )
    def test_strict_decode(self, tmp_path, key, raw, expected):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, key, raw)
        prefs = _prefs_repo(db).load()  # MUST NOT raise
        attribute = {
            "favorites": "favorite_paths",
            "history": "history_paths",
            "recently_added": "recently_added_paths",
        }[key]
        assert getattr(prefs, attribute) == expected

    def test_string_json_never_iterates_characters(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", json.dumps("/music/song.flac"))
        prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()  # NEVER ("/", "m", "u", ...)

    def test_object_json_never_fabricates_paths(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", json.dumps({"fake/path": True}))
        prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()  # NEVER ("fake/path",)

    def test_mixed_list_rejected_whole(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "history", json.dumps(["A", 42, "B"]))
        prefs = _prefs_repo(db).load()
        assert prefs.history_paths == ()  # NO partial salvage ("A", "B")

    def test_all_keys_share_the_strict_decoder(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", "42")
        _seed_library_prefs(db, "history", "42")
        _seed_library_prefs(db, "recently_added", "42")
        prefs = _prefs_repo(db).load()
        assert prefs == LibraryPrefs()


class TestPlaylistRootStrict:
    @pytest.mark.parametrize(
        "raw",
        ["42", '"Road"', "{}", "null", "true", "{broken", ""],
    )
    def test_malformed_root_falls_back_empty(self, tmp_path, raw):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "playlists", raw)
        assert _playlists_repo(db).load() == ()  # MUST NOT raise


class TestPlaylistEntries:
    def test_valid_entry(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(
            db,
            "playlists",
            json.dumps([{"name": "Road", "track_paths": ["A", "B"]}]),
        )
        playlists = _playlists_repo(db).load()
        assert len(playlists) == 1
        assert playlists[0].name == "Road"
        assert playlists[0].track_paths == ("A", "B")

    def test_entry_name_not_string_discarded(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(
            db, "playlists", json.dumps([{"name": 42, "track_paths": ["A"]}])
        )
        assert _playlists_repo(db).load() == ()

    def test_entry_track_paths_not_list_discarded(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(
            db, "playlists", json.dumps([{"name": "Road", "track_paths": "A"}])
        )
        assert _playlists_repo(db).load() == ()

    def test_entry_mixed_track_paths_rejected_whole(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(
            db, "playlists", json.dumps([{"name": "Road", "track_paths": ["A", 42]}])
        )
        # NO partial salvage: the whole entry is malformed and rejected.
        assert _playlists_repo(db).load() == ()

    def test_valid_siblings_survive_invalid_entry(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(
            db,
            "playlists",
            json.dumps(
                [
                    {"name": "Valid 1", "track_paths": ["A"]},
                    {"name": "Broken", "track_paths": ["B", 42]},
                    {"name": "Valid 2", "track_paths": ["C"]},
                ]
            ),
        )
        playlists = _playlists_repo(db).load()
        assert [p.name for p in playlists] == ["Valid 1", "Valid 2"]
        assert playlists[0].track_paths == ("A",)
        assert playlists[1].track_paths == ("C",)


class TestAuthoritativeTableOptionality:
    def test_missing_optional_library_prefs_equals_empty(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_settings(db)
        state = _read_authoritative_state(db)
        assert state["library_prefs"] == []  # pre-M6: absent == empty

    def test_missing_required_settings_fails_authoritative_read(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", json.dumps(["A"]))
        with pytest.raises(sqlite3.OperationalError):
            _read_authoritative_state(db)  # settings REQUIRED: never == empty

    def test_missing_settings_fails_candidate_provenance(self, tmp_path):
        lkg = tmp_path / "michi.lkg"
        candidate = tmp_path / "michi.recovery"
        _seed_settings(lkg)
        _seed_library_prefs(lkg, "favorites", json.dumps(["A"]))
        _seed_library_prefs(candidate, "favorites", json.dumps(["A"]))  # no settings
        assert _candidate_matches_lkg(candidate, lkg) is False  # fail closed

    def test_library_index_still_excluded_from_authoritative_tables(self):
        assert "library_index" not in sqlite_settings_mod._AUTHORITATIVE_TABLES
        assert "library_meta" not in sqlite_settings_mod._AUTHORITATIVE_TABLES


class TestProductionMalformedGoldens:
    def test_production_graph_survives_malformed_library_prefs(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_settings(db)
        _seed_library_prefs(db, "favorites", "42")
        _seed_library_prefs(db, "history", '"ABC"')
        _seed_library_prefs(db, "recently_added", json.dumps(["A", 1]))
        SQLiteSettingsRepository.open_for_startup(db)  # healthy, no recovery
        graph = _production_graph(db)
        assert graph.library.state.favorite_paths == ()
        assert graph.library.state.history_paths == ()
        assert graph.library.state.recently_added_paths == ()

    def test_production_graph_survives_malformed_playlists(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_settings(db)
        _seed_library_prefs(db, "playlists", "42")
        SQLiteSettingsRepository.open_for_startup(db)
        graph = _production_graph(db)
        assert graph.playlist_service.playlists == ()
        assert graph.playlists_bridge.playlists == []

    def test_recovery_installs_malformed_prefs_safely(self, tmp_path):
        db = tmp_path / "michi.db"
        _seed_settings(db)
        _seed_library_prefs(db, "favorites", "42")
        _seed_library_prefs(db, "playlists", "42")
        assert (
            SQLiteSettingsRepository.refresh_last_known_good(db).health
            is PersistenceHealth.HEALTHY
        )
        for suffix in ("", "-wal", "-shm"):
            p = Path(str(db) + suffix)
            p.unlink(missing_ok=True)
        SQLiteSettingsRepository.open_for_startup(db)  # recovers from LKG
        graph = _production_graph(db)
        assert graph.library.state.favorite_paths == ()
        assert graph.playlist_service.playlists == ()
        assert graph.playlists_bridge.playlists == []


def _production_graph(db_path):
    from michi.bootstrap import _build_services

    return _build_services(
        db_path,
        backend=FakeAudioPort(),
        scanner=StatScanner([]),
        metadata_extractor=None,
        artwork_provider=None,
        artwork_cache=None,
    )


class TestDecodeLoggingAccuracy:
    """M6-FINAL-DECODE-LOGGING-MICROFIX: warnings must represent REAL
    malformed persisted data — a valid empty list and a missing row are
    NORMAL state, not corruption."""

    def _prefs_warnings(self, caplog):
        return [
            r.message
            for r in caplog.records
            if "Malformed library prefs value" in r.message
        ]

    def _playlist_warnings(self, caplog):
        return [r.message for r in caplog.records if "Malformed playlists" in r.message]

    def test_valid_empty_favorites_does_not_warn(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", "[]")
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()  # valid empty list
        assert self._prefs_warnings(caplog) == []

    def test_missing_favorites_does_not_warn(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()  # absent row: normal first-run state
        assert self._prefs_warnings(caplog) == []

    def test_malformed_scalar_favorites_warns(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", "42")
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()
        assert len(self._prefs_warnings(caplog)) == 1

    def test_mixed_list_warns(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "favorites", json.dumps(["A", 42]))
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()
        assert len(self._prefs_warnings(caplog)) == 1

    def test_non_text_sqlite_value_falls_back_safe(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO library_prefs VALUES (?, ?)",
                ("favorites", b'["A"]'),
            )
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.favorite_paths == ()  # strict TEXT contract: BLOB is malformed
        assert len(self._prefs_warnings(caplog)) == 1

    def test_history_and_recent_share_the_decoder(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "history", "[]")
        _seed_library_prefs(db, "recently_added", "[]")
        with caplog.at_level(
            logging.WARNING, logger="michi.infrastructure.library_prefs"
        ):
            prefs = _prefs_repo(db).load()
        assert prefs.history_paths == ()
        assert prefs.recently_added_paths == ()
        assert self._prefs_warnings(caplog) == []  # valid empties, no warnings

    def test_valid_empty_playlist_list_does_not_warn(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "playlists", "[]")
        with caplog.at_level(logging.WARNING, logger="michi.infrastructure.playlists"):
            playlists = _playlists_repo(db).load()
        assert playlists == ()  # valid empty root list
        assert self._playlist_warnings(caplog) == []

    def test_invalid_playlist_root_warns(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        _seed_library_prefs(db, "playlists", "42")
        with caplog.at_level(logging.WARNING, logger="michi.infrastructure.playlists"):
            playlists = _playlists_repo(db).load()
        assert playlists == ()
        assert len(self._playlist_warnings(caplog)) == 1

    def test_non_text_playlist_value_falls_back_safe(self, tmp_path, caplog):
        db = tmp_path / "michi.db"
        with sqlite3.connect(str(db)) as conn:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.execute(
                "INSERT OR REPLACE INTO library_prefs VALUES (?, ?)",
                ("playlists", b'[{"name": "Road", "track_paths": ["A"]}]'),
            )
        with caplog.at_level(logging.WARNING, logger="michi.infrastructure.playlists"):
            playlists = _playlists_repo(db).load()
        assert playlists == ()  # strict TEXT contract: BLOB is malformed
        assert len(self._playlist_warnings(caplog)) == 1
