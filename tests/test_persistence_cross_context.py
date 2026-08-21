"""M6-FINAL-CROSS-PERSISTENCE-GATE — Phase-1 RED tests.

The transversal gate between M6 library persistence and M5/M11.2 SQLite
recovery: M6 introduced NEW authoritative durable state (library_prefs:
favorites/history/recently_added/playlists) inside the SAME michi.db, but
the recovery provenance compared only ``settings``. This file encodes the
final contract:

- PROVENANCE = logical equality of ALL authoritative tables
  (settings + library_prefs) — NEVER binary bytes, NEVER settings-only,
  NEVER cache equality;
- LKG = FULL database snapshot (SQLite backup API) — all tables included;
- library_index / library_meta = REBUILDABLE CACHE — excluded from the
  provenance identity, but preserved by the full-database install and
  rebuildable from the filesystem;
- pre-M6 compatibility: an ABSENT optional authoritative table is
  equivalent to an EMPTY one (and nothing more);
- after recovery, the PRODUCTION graph (bootstrap._build_services) loads
  the restored user state — RECOVERY + M6 PRODUCTION COMPOSITION work
  together.

On the current baseline (HEAD a3772bb) the module-level import of
``_read_authoritative_state`` fails at collection — that IS the expected
Phase-1 red evidence.

Also encodes the P2 honesty fix (album technical summary: known+unknown
must NEVER report a definitive album-wide label) and the P2/P3 immutable
scan-progress snapshot at the thread boundary (distinct instances, stable
values, owner-thread delivery preserved).
"""

import json
import os
import sqlite3
import sys
import threading
import time
from pathlib import Path

import pytest
from PySide6.QtCore import QCoreApplication
from PySide6.QtGui import QGuiApplication

from michi.application.ports import ScanProgressSnapshot
from michi.domain.library import LibraryScanStatus, TrackMetadata, TrackRef
from michi.domain.library_index import encode_index_metadata
from michi.domain.persistence_health import PersistenceHealth
from michi.infrastructure.sqlite_settings import (
    _AUTHORITATIVE_TABLES,
    PersistenceStartupError,
    SQLiteSettingsRepository,
    _read_authoritative_state,
)
from tests.conftest import FakeAudioPort
from tests.test_library_incremental import StatScanner
from tests.test_library_metadata import FakeExtractor

GOLDEN_SETTINGS = [
    ("schema_version", "1"),
    ("volume", "37"),
    ("theme", "dark"),
    ("muted", "false"),
    ("last_directory", "/m"),
    ("recent_files", json.dumps([])),
]
GOLDEN_PREFS = [
    ("favorites", json.dumps(["A"])),
    ("history", json.dumps(["A"])),
    ("recently_added", json.dumps(["A", "B"])),
    ("playlists", json.dumps([{"name": "Road", "track_paths": ["A", "B"]}])),
]


def _fabricate_db(db_path, settings, prefs=None, index=None):
    """Fabricate a michi.db with the given table rows (test-only raw SQL)."""
    with sqlite3.connect(str(db_path)) as conn:
        conn.execute(
            "CREATE TABLE IF NOT EXISTS settings ("
            "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.executemany("INSERT OR REPLACE INTO settings VALUES (?, ?)", settings)
        if prefs is not None:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_prefs ("
                "key TEXT PRIMARY KEY, value TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT OR REPLACE INTO library_prefs VALUES (?, ?)", prefs
            )
        if index is not None:
            conn.execute(
                "CREATE TABLE IF NOT EXISTS library_index ("
                "track_id TEXT PRIMARY KEY, file_size INTEGER NOT NULL, "
                "mtime_ns INTEGER NOT NULL, metadata TEXT NOT NULL)"
            )
            conn.executemany(
                "INSERT OR REPLACE INTO library_index VALUES (?, ?, ?, ?)", index
            )


def _read_table_rows(db_path, table):
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        try:
            return conn.execute(
                f"SELECT key, value FROM {table} ORDER BY key"
            ).fetchall()
        except sqlite3.OperationalError:
            return None  # table absent


def _read_index_count(db_path):
    """library_index has its own schema (track_id/file_size/...): count rows."""
    uri = f"{db_path.resolve().as_uri()}?mode=ro"
    with sqlite3.connect(uri, uri=True) as conn:
        try:
            return conn.execute("SELECT count(*) FROM library_index").fetchone()[0]
        except sqlite3.OperationalError:
            return None  # table absent


def _remove_primary(db_path):
    for suffix in ("", "-wal", "-shm"):
        p = Path(str(db_path) + suffix)
        if p.exists():
            p.unlink()


def _refresh_lkg(db_path):
    diag = SQLiteSettingsRepository.refresh_last_known_good(db_path)
    assert diag.health is PersistenceHealth.HEALTHY


def _index_rows_for(music_paths):
    """Real fingerprint rows for the given files (unchanged-scan compatible)."""
    rows = []
    for p in music_paths:
        st = p.stat()
        meta = TrackMetadata(title=p.stem)
        rows.append((str(p), st.st_size, st.st_mtime_ns, encode_index_metadata(meta)))
    return rows


class TestAuthoritativeState:
    def test_authoritative_state_includes_library_prefs(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS)
        state = _read_authoritative_state(db)
        assert set(state) == {"settings", "library_prefs"}
        assert state["settings"] == [
            (k, v) for k, v in sorted(GOLDEN_SETTINGS, key=lambda r: r[0])
        ]
        assert state["library_prefs"] == [
            (k, v) for k, v in sorted(GOLDEN_PREFS, key=lambda r: r[0])
        ]

    def test_authoritative_tables_are_centralized(self):
        assert _AUTHORITATIVE_TABLES == ("settings", "library_prefs")
        assert "library_index" not in _AUTHORITATIVE_TABLES  # rebuildable cache


class TestProvenance:
    def test_candidate_same_settings_different_library_prefs_rejected(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS)
        _refresh_lkg(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        # Same settings, DIFFERENT user library state.
        _fabricate_db(
            candidate,
            GOLDEN_SETTINGS,
            [
                ("favorites", json.dumps(["B"])),
                ("history", json.dumps(["B"])),
                ("recently_added", json.dumps(["B"])),
                ("playlists", json.dumps([{"name": "Road", "track_paths": ["B"]}])),
            ],
        )
        assert (
            SQLiteSettingsRepository.inspect_path(candidate).health
            is PersistenceHealth.HEALTHY
        )
        candidate_before = candidate.read_bytes()
        _remove_primary(db)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.read_bytes() == candidate_before  # untrusted, preserved
        assert not db.exists()  # never installed

    def test_candidate_same_authoritative_state_different_library_index_allowed(
        self, tmp_path
    ):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS, _index_rows_for([a, b]))
        _refresh_lkg(db)
        # A pre-existing candidate with the SAME authoritative state but a
        # DIFFERENT index cache (only A indexed) — cache divergence must not
        # invalidate provenance.
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _fabricate_db(candidate, GOLDEN_SETTINGS, GOLDEN_PREFS, _index_rows_for([a]))
        _remove_primary(db)

        SQLiteSettingsRepository.open_for_startup(db)

        # The candidate was authorized and installed (with its cache).
        assert db.exists()
        assert _read_index_count(db) == 1  # the A-only cache, not the LKG's A+B

    def test_pre_m6_missing_library_prefs_equivalent_to_empty(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS)  # pre-M6: no library_prefs table
        _refresh_lkg(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        # Candidate WITH an empty library_prefs table.
        _fabricate_db(candidate, GOLDEN_SETTINGS, prefs=[])
        _remove_primary(db)

        SQLiteSettingsRepository.open_for_startup(db)
        assert db.exists()  # absent == empty: logical equivalence holds

    def test_nonempty_library_prefs_not_equivalent_to_missing(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS)  # LKG has NO library_prefs table
        _refresh_lkg(db)
        candidate = SQLiteSettingsRepository.recovery_candidate_path(db)
        _fabricate_db(candidate, GOLDEN_SETTINGS, GOLDEN_PREFS)  # candidate HAS data
        candidate_before = candidate.read_bytes()
        _remove_primary(db)

        with pytest.raises(PersistenceStartupError):
            SQLiteSettingsRepository.open_for_startup(db)

        assert candidate.read_bytes() == candidate_before  # preserved, rejected


class TestLkgSnapshot:
    def test_lkg_snapshot_contains_library_prefs(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS)
        _refresh_lkg(db)
        lkg = SQLiteSettingsRepository.last_known_good_path(db)
        assert _read_table_rows(lkg, "library_prefs") == [
            (k, v) for k, v in sorted(GOLDEN_PREFS, key=lambda r: r[0])
        ]
        assert _read_table_rows(lkg, "settings") is not None


class TestRecoveryRestoresUserState:
    @pytest.fixture()
    def recovered(self, tmp_path):
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS)
        _refresh_lkg(db)
        _remove_primary(db)
        SQLiteSettingsRepository.open_for_startup(db)
        return db

    def test_recovery_restores_favorites(self, recovered):
        assert _read_table_rows(recovered, "library_prefs") is not None
        rows = dict(_read_table_rows(recovered, "library_prefs"))
        assert json.loads(rows["favorites"]) == ["A"]

    def test_recovery_restores_history(self, recovered):
        rows = dict(_read_table_rows(recovered, "library_prefs"))
        assert json.loads(rows["history"]) == ["A"]

    def test_recovery_restores_recently_added(self, recovered):
        rows = dict(_read_table_rows(recovered, "library_prefs"))
        assert json.loads(rows["recently_added"]) == ["A", "B"]

    def test_recovery_restores_playlists(self, recovered):
        rows = dict(_read_table_rows(recovered, "library_prefs"))
        playlists = json.loads(rows["playlists"])
        assert playlists == [{"name": "Road", "track_paths": ["A", "B"]}]

    def test_recovery_restores_settings(self, recovered):
        rows = dict(_read_table_rows(recovered, "settings"))
        assert rows["volume"] == "37"
        assert rows["theme"] == "dark"

    def test_recovered_production_graph_loads_library_prefs(self, recovered, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        graph = _production_graph(recovered, [a, b])
        # The golden user state used opaque paths ("A"/"B") — restored VERBATIM,
        # never fabricated.
        assert "A" in graph.library.state.favorite_paths
        assert "A" in graph.library.state.history_paths
        assert "A" in graph.library.state.recently_added_paths
        assert "B" in graph.library.state.recently_added_paths

    def test_recovered_production_graph_loads_playlists(self, recovered, tmp_path):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        graph = _production_graph(recovered, [a, b])
        assert [
            (r["name"], r["trackCount"]) for r in graph.playlists_bridge.playlists
        ] == [("Road", 2)]
        assert graph.playlist_service.playlists[0].track_paths == ("A", "B")
        graph.bridge.dispose()


class TestIndexRecovery:
    def test_recovery_preserves_valid_index_when_present(self, tmp_path, qapp):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS, _index_rows_for([a, b]))
        _refresh_lkg(db)
        _remove_primary(db)
        SQLiteSettingsRepository.open_for_startup(db)

        # The index survived the full-database recovery...
        assert _read_index_count(db) == 2
        # ...and an unchanged scan performs ZERO extractions.
        extractor = _CountingExtractor()
        graph = _production_graph(db, [a, b], extractor=extractor)
        graph.library.scan(str(music))
        assert extractor.calls == []
        graph.bridge.dispose()

    def test_recovery_without_index_can_rebuild_from_filesystem(self, tmp_path, qapp):
        music = tmp_path / "music"
        music.mkdir()
        a = music / "a.mp3"
        b = music / "b.mp3"
        a.write_bytes(b"x")
        b.write_bytes(b"x")
        db = tmp_path / "michi.db"
        _fabricate_db(db, GOLDEN_SETTINGS, GOLDEN_PREFS)  # no index table
        _refresh_lkg(db)
        _remove_primary(db)
        SQLiteSettingsRepository.open_for_startup(db)

        extractor = _CountingExtractor()
        graph = _production_graph(db, [a, b], extractor=extractor)
        graph.library.scan(str(music))
        assert set(extractor.calls) == {a, b}  # index rebuilt from the filesystem
        assert [t.file_path for t in graph.library.state.tracks] == [a, b]
        # No user state loss in the process (opaque golden paths restored).
        assert "A" in graph.library.state.favorite_paths
        assert [
            (r["name"], r["trackCount"]) for r in graph.playlists_bridge.playlists
        ] == [("Road", 2)]
        graph.bridge.dispose()


class TestAlbumTechnicalSummary:
    def _model(self, *specs):
        from michi.domain.library import build_music_model

        tracks = []
        for i, (codec, sample_rate, bit_depth, bitrate) in enumerate(specs):
            tracks.append(
                TrackRef(
                    file_path=Path(f"/m/t{i}.mp3"),
                    title=f"t{i}",
                    album="Album",
                    artist="Artist",
                    codec=codec,
                    sample_rate_hz=sample_rate,
                    bit_depth=bit_depth,
                    bitrate_bps=bitrate,
                )
            )
        return build_music_model(tracks).albums[0]

    def test_album_summary_uniform_known_tracks(self):
        album = self._model(("FLAC", 96000, 24, 0), ("FLAC", 96000, 24, 0))
        assert album.technical_summary == "FLAC · 24-bit · 96 kHz"

    def test_album_summary_mixed_known_tracks(self):
        album = self._model(("FLAC", 96000, 24, 0), ("FLAC", 44100, 16, 0))
        assert album.technical_summary == "Mixed formats"

    def test_album_summary_known_plus_unknown_not_definitive(self):
        album = self._model(("FLAC", 96000, 24, 0), ("", 0, 0, 0))
        assert album.technical_summary != "FLAC · 24-bit · 96 kHz"
        assert album.technical_summary == ""  # no fabricated claim

    def test_album_summary_all_unknown_empty(self):
        album = self._model(("", 0, 0, 0), ("", 0, 0, 0))
        assert album.technical_summary == ""

    def test_album_summary_uniform_lossy_tracks(self):
        album = self._model(("MP3", 0, 0, 320000), ("MP3", 0, 0, 320000))
        assert album.technical_summary == "MP3 · 320 kbps"


class TestProgressSnapshots:
    def test_progress_events_are_distinct_snapshots(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(6)])
        graph = _production_graph(tmp_path / "michi.db", paths)
        received = []
        graph.relay.progress.connect(lambda gen, snap: received.append(snap))

        graph.library.start_scan(str(music))
        _wait_terminal(graph)

        assert received
        assert all(isinstance(s, ScanProgressSnapshot) for s in received)
        processed_seq = [s.processed for s in received]
        assert processed_seq == sorted(processed_seq)  # monotonic
        assert all(received[i] is not received[i + 1] for i in range(len(received) - 1))

    def test_progress_snapshot_values_do_not_mutate_after_emit(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(6)])
        extractor = _GatedExtractor()
        graph = _production_graph(tmp_path / "michi.db", paths, extractor=extractor)
        received = []
        graph.relay.progress.connect(lambda gen, snap: received.append(snap))

        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)  # worker parked inside the gate
        extractor.gate.set()
        _spin_until(lambda: received)  # first snapshot delivered after report
        assert received
        first = received[0]
        first_processed = first.processed
        _wait_terminal(graph)

        # The emitted snapshot is immutable: later progress never mutates it.
        assert first.processed == first_processed
        assert all(s is not first for s in received[1:])

    def test_progress_still_arrives_on_owner_thread(self, tmp_path, qapp):
        gui_id = threading.get_ident()
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(6)])
        graph = _production_graph(tmp_path / "michi.db", paths)

        state_threads = []
        graph.library.subscribe_changed(
            lambda: state_threads.append(threading.get_ident())
        )
        graph.library.start_scan(str(music))
        _wait_terminal(graph)

        assert state_threads
        assert all(t == gui_id for t in state_threads)  # owner-thread delivery

    def test_cancel_pipeline_regression(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(10)])
        extractor = _GatedExtractor()
        graph = _production_graph(tmp_path / "michi.db", paths, extractor=extractor)
        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        graph.library.cancel_scan()
        extractor.gate.set()
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.CANCELLED
        graph.bridge.dispose()

    def test_new_scan_after_cancel_regression(self, tmp_path, qapp):
        music, paths = _music(tmp_path, [f"t{i:02}.mp3" for i in range(10)])
        extractor = _GatedExtractor()
        graph = _production_graph(tmp_path / "michi.db", paths, extractor=extractor)
        graph.library.start_scan(str(music))
        _wait_calls(extractor, 1)
        graph.library.cancel_scan()
        extractor.gate.set()
        _wait_terminal(graph)
        extractor.gate = threading.Event()
        extractor.gate.set()
        graph.library.start_scan(str(music))
        _wait_terminal(graph)
        assert graph.library.state.scan_status is LibraryScanStatus.COMPLETED
        assert len(graph.library.state.tracks) == 10
        graph.bridge.dispose()


# ---------------------------------------------------------------------------
# Test scaffolding
# ---------------------------------------------------------------------------


class _CountingExtractor:
    """Records every extracted path; delegates to a FakeExtractor."""

    def __init__(self, factory=None) -> None:
        self.inner = FakeExtractor(factory=factory)
        self.calls = []

    def extract(self, file_path):
        self.calls.append(file_path)
        return self.inner.extract(file_path)


class _GatedExtractor(_CountingExtractor):
    """Deterministic in-flight gate (threading.Event, never sleeps)."""

    def __init__(self, factory=None) -> None:
        super().__init__(factory)
        self.gate = threading.Event()

    def extract(self, file_path):
        self.calls.append(file_path)
        self.gate.wait(timeout=5.0)
        return self.inner.extract(file_path)


def _music(tmp_path, names):
    music = tmp_path / "music"
    music.mkdir(exist_ok=True)
    paths = []
    for name in names:
        p = music / name
        p.write_bytes(b"x")
        paths.append(p)
    return music, paths


def _production_graph(db_path, paths, extractor=None):
    """The PRODUCTION graph (bootstrap._build_services) on the given db."""
    from michi.bootstrap import _build_services

    return _build_services(
        db_path,
        backend=FakeAudioPort(),
        scanner=StatScanner(paths),
        metadata_extractor=extractor or _CountingExtractor(),
        artwork_provider=None,
        artwork_cache=None,
    )


def _spin_until(predicate, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if predicate():
            return True
        time.sleep(0.005)
    return False


def _wait_terminal(graph, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        QCoreApplication.processEvents()
        if graph.library.state.scan_status in (
            LibraryScanStatus.COMPLETED,
            LibraryScanStatus.CANCELLED,
            LibraryScanStatus.FAILED,
        ):
            return
        time.sleep(0.005)
    raise AssertionError(
        f"scan did not reach a terminal status, got "
        f"{graph.library.state.scan_status.name}"
    )


def _wait_calls(extractor, n, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if len(extractor.calls) >= n:
            return
        time.sleep(0.005)
    raise AssertionError(f"extractor made {len(extractor.calls)} calls, expected {n}")


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app
