"""LOCAL-05 favorites / history / recently-added (persisted) — Phase-1 RED tests.

On the current baseline the module-level import of the new domain symbol
(LibraryPrefs) fails at collection (ImportError) — that IS the expected
Phase-1 red evidence. The tests encode the target contract and must pass
once the production changes land (michi/domain/library.py LibraryPrefs +
LibraryState favorite/history/recently-added fields with HISTORY_CAP=50 and
RECENT_CAP=50, michi/application/ports.py LibraryPrefsPort, michi/
infrastructure/library_prefs.py SqliteLibraryPrefsRepository, LibraryService
prefs init + toggle_favorite/set_favorite + _on_queue_changed history
recording + scan-driven recently-added, LibraryBridge favoritePaths/
historyPaths/recentlyAddedPaths/songPaths/favoriteRows/historyRows/
recentlyAddedRows + toggle_favorite slot, and the LibraryView.qml tabs).

Helpers reuse the existing fakes: FakeScanner/FakeExtractor from
tests.test_library_metadata, FakeAudioPort from tests.conftest,
FailingScanner from tests.test_library_artwork. FakePrefsPort is defined
here (in-memory, seedable, records every save).

Coverage:
- Favorites: toggle add/remove, explicit set, deterministic sorted order,
  prefs round-trip init, best-effort persistence via the port
- History: queue commit records, consecutive dedupe, 50 cap most-recent-first,
  nothing recorded while a play request is pending, persisted via the port
- Recently added: only NEW scan paths, empty on no-change rescan, 50 cap in
  scan order (most recent first), failed scan untouched, persisted via port
- Bridge: row/toggle surface, songPaths parallel to files, missing paths
  skipped in rows
- Sqlite repository: round trip, empty fresh db, missing file never raises,
  settings table untouched (shared db)
- QML smoke: LibraryView.qml still instantiates with the real bridge
  (forward pin for the three new tabs + star toggles — passes trivially on
  baseline)
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_port import LibraryFilesystemError
from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.queue_service import QueueService
from michi.domain.library import LibraryDiagnosticCode, LibraryPrefs
from michi.infrastructure.library_prefs import SqliteLibraryPrefsRepository
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_artwork import FailingScanner
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

HISTORY_CAP = 50
RECENT_CAP = 50


class FakePrefsPort:
    """In-memory LibraryPrefsPort: seedable; every save is recorded.

    load() returns the stored prefs (or empty LibraryPrefs when never
    seeded/saved); save() stores the prefs and appends them to ``saved``.
    Never raises — mirrors the best-effort port contract.
    """

    def __init__(self, prefs=None) -> None:
        self._stored = prefs if prefs is not None else LibraryPrefs()
        self.saved: list[LibraryPrefs] = []

    def load(self) -> LibraryPrefs:
        return self._stored

    def save(self, prefs: LibraryPrefs) -> None:
        self._stored = prefs
        self.saved.append(prefs)


def _make_library_and_queue(scanner, prefs_port=None, extractor=None):
    """Build LibraryService with a real queue + the shared FakeAudioPort.

    Returns (library, queue, audio): ``audio`` is needed to trigger the
    media-acceptance path that commits pending queue plays.
    """
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    if extractor is None:
        library = LibraryService(scanner, queue, library_prefs=prefs_port)
    else:
        library = LibraryService(scanner, queue, extractor, library_prefs=prefs_port)
    return library, queue, audio


def _write_tracks(tmp_path, names):
    """Create real (empty) track files and return their Paths."""
    paths = [tmp_path / name for name in names]
    for p in paths:
        p.write_bytes(b"x")
    return paths


class TestFavoritesService:
    def test_toggle_favorite_adds_and_removes(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        library, _, _ = _make_library_and_queue(FakeScanner())
        library.toggle_favorite(p)
        assert str(p) in library.state.favorite_paths
        library.toggle_favorite(p)
        assert str(p) not in library.state.favorite_paths

    def test_set_favorite_explicit(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        library, _, _ = _make_library_and_queue(FakeScanner())
        library.set_favorite(p, True)
        assert str(p) in library.state.favorite_paths
        library.set_favorite(p, False)
        assert str(p) not in library.state.favorite_paths

    def test_favorites_sorted_deterministic(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p2 = tmp_path / "two.mp3"
        for p in (p1, p2):
            p.write_bytes(b"x")
        first, _, _ = _make_library_and_queue(FakeScanner())
        first.toggle_favorite(p2)
        first.toggle_favorite(p1)
        second, _, _ = _make_library_and_queue(FakeScanner())
        second.toggle_favorite(p1)
        second.toggle_favorite(p2)
        expected = tuple(sorted((str(p1), str(p2))))
        assert first.state.favorite_paths == expected
        assert second.state.favorite_paths == expected

    def test_favorites_persisted_round_trip(self):
        port = FakePrefsPort(
            prefs=LibraryPrefs(favorite_paths=("/music/a.mp3", "/music/b.mp3"))
        )
        library, _, _ = _make_library_and_queue(FakeScanner(), prefs_port=port)
        assert library.state.favorite_paths == ("/music/a.mp3", "/music/b.mp3")

    def test_toggle_persists_via_port(self, tmp_path):
        p = tmp_path / "one.mp3"
        p.write_bytes(b"x")
        port = FakePrefsPort()
        library, _, _ = _make_library_and_queue(FakeScanner(), prefs_port=port)
        library.toggle_favorite(p)
        assert str(p) in port.saved[-1].favorite_paths


class TestHistoryRecording:
    def test_queue_commit_records_history(self):
        library, queue, audio = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        queue.play_index(0)
        audio.trigger_media_accepted(path)
        assert library.state.history_paths[0] == str(path)

    def test_history_dedupes_consecutive(self):
        library, queue, audio = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        queue.play_index(0)
        audio.trigger_media_accepted(path)
        queue.play_current()
        audio.trigger_media_accepted(path)
        assert library.state.history_paths == (str(path),)

    def test_history_capped_at_50(self):
        library, queue, audio = _make_library_and_queue(FakeScanner())
        paths = [Path(f"/music/t{i:02d}.mp3") for i in range(55)]
        for p in paths:
            queue.add(p)
        for i, p in enumerate(paths):
            queue.play_index(i)
            audio.trigger_media_accepted(p)
        assert len(library.state.history_paths) == HISTORY_CAP
        assert library.state.history_paths[0] == str(paths[-1])
        assert library.state.history_paths[-1] == str(paths[5])

    def test_history_not_recorded_when_no_commit(self):
        library, queue, _ = _make_library_and_queue(FakeScanner())
        path = Path("/music/one.mp3")
        queue.add(path)
        queue.play_index(0)  # pending, never accepted
        assert library.state.history_paths == ()

    def test_history_persisted(self):
        port = FakePrefsPort()
        library, queue, audio = _make_library_and_queue(FakeScanner(), prefs_port=port)
        path = Path("/music/one.mp3")
        queue.add(path)
        queue.play_index(0)
        audio.trigger_media_accepted(path)
        assert str(path) in port.saved[-1].history_paths


class TestRecentlyAdded:
    def test_new_scan_paths_prepended(self, tmp_path):
        p1, p2, p3 = _write_tracks(tmp_path, ("one.mp3", "two.mp3", "three.mp3"))
        scanner = FakeScanner([p1, p2])
        library, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        scanner.paths = [p1, p2, p3]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == (str(p3),)

    def test_rescan_no_changes_no_update(self, tmp_path):
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FakeScanner([p1, p2])
        library, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        scanner.paths = [p1, p2]
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == ()

    def test_recently_added_capped(self, tmp_path):
        paths = _write_tracks(tmp_path, [f"t{i:02d}.mp3" for i in range(60)])
        library, _, _ = _make_library_and_queue(FakeScanner(paths))
        library.scan(str(tmp_path))
        assert len(library.state.recently_added_paths) == RECENT_CAP
        # Most recent scan order first: the 50 newest scan entries reversed.
        assert library.state.recently_added_paths == tuple(
            str(p) for p in reversed(paths[-RECENT_CAP:])
        )

    def test_failed_scan_preserves_recently_added(self, tmp_path):
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        scanner = FailingScanner([p1, p2])
        library, _, _ = _make_library_and_queue(scanner)
        library.scan(str(tmp_path))
        before = library.state.recently_added_paths
        scanner.scan_error = LibraryFilesystemError(
            LibraryDiagnosticCode.IO_FAILURE, tmp_path, "i/o error"
        )
        library.scan(str(tmp_path))
        assert library.state.recently_added_paths == before

    def test_recently_added_persisted(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        port = FakePrefsPort()
        library, _, _ = _make_library_and_queue(FakeScanner([p1]), prefs_port=port)
        library.scan(str(tmp_path))
        assert str(p1) in port.saved[-1].recently_added_paths


class TestBridgeFavoritesHistory:
    def test_bridge_rows_and_toggle(self, tmp_path):
        p1, p2, p3 = _write_tracks(tmp_path, ("one.mp3", "two.mp3", "three.mp3"))
        scanner = FakeScanner([p1, p2])
        library, queue, audio = _make_library_and_queue(
            scanner, extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        bridge.toggle_favorite(str(p1))
        assert str(p1) in bridge.property("favoritePaths")
        assert bridge.property("favoriteRows") == [
            {"displayName": "T one", "path": str(p1)}
        ]
        queue.add(p1)
        queue.play_index(0)
        audio.trigger_media_accepted(p1)
        assert bridge.property("historyRows") == [
            {"displayName": "T one", "path": str(p1)}
        ]
        scanner.paths = [p1, p2, p3]
        library.scan(str(tmp_path))
        assert bridge.property("recentlyAddedRows") == [
            {"displayName": "T three", "path": str(p3)}
        ]
        bridge.dispose()

    def test_song_paths_parallel_to_files(self, tmp_path):
        p1, p2 = _write_tracks(tmp_path, ("one.mp3", "two.mp3"))
        library, _, _ = _make_library_and_queue(FakeScanner([p1, p2]))
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        files = bridge.property("files")
        song_paths = bridge.property("songPaths")
        assert len(song_paths) == len(files) == 2
        assert song_paths[0] == str(p1)
        bridge.dispose()

    def test_missing_paths_skipped_in_rows(self, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, _, _ = _make_library_and_queue(FakeScanner([p1]))
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        ghost = tmp_path / "ghost.mp3"
        bridge.toggle_favorite(str(ghost))
        assert str(ghost) in bridge.property("favoritePaths")
        assert bridge.property("favoriteRows") == []
        bridge.dispose()


class TestSqliteRepository:
    def test_repo_round_trip(self, tmp_path):
        db = tmp_path / "settings.db"
        prefs = LibraryPrefs(
            favorite_paths=("/music/a.mp3", "/music/b.mp3"),
            history_paths=("/music/h.mp3",),
            recently_added_paths=("/music/r.mp3",),
        )
        SqliteLibraryPrefsRepository(db).save(prefs)
        repo2 = SqliteLibraryPrefsRepository(db)
        assert repo2.load() == prefs

    def test_repo_empty_on_fresh_db(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqliteLibraryPrefsRepository(db)
        assert repo.load() == LibraryPrefs()

    def test_repo_missing_file_returns_empty(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqliteLibraryPrefsRepository(db)
        assert repo.load() == LibraryPrefs()  # never raises

    def test_repo_does_not_touch_settings_table(self, tmp_path):
        db = tmp_path / "settings.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO settings VALUES ('volume', '80')")
        conn.commit()
        conn.close()
        repo = SqliteLibraryPrefsRepository(db)
        repo.save(LibraryPrefs(favorite_paths=("/music/a.mp3",)))
        conn = sqlite3.connect(str(db))
        try:
            settings_rows = conn.execute(
                "SELECT key, value FROM settings ORDER BY key"
            ).fetchall()
            assert settings_rows == [("volume", "80")]
            prefs_rows = conn.execute(
                "SELECT key FROM library_prefs ORDER BY key"
            ).fetchall()
            assert [k for (k,) in prefs_rows] == [
                "favorites",
                "history",
                "recently_added",
            ]
        finally:
            conn.close()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_loads_with_new_tabs(self, qapp, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, _, _ = _make_library_and_queue(
            FakeScanner([p1]), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        obj.deleteLater()
        bridge.dispose()
