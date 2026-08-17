"""LOCAL-06 playlists (full scope: create/delete/rename/add/remove/reorder/
play) — Phase-1 RED tests.

On the current baseline the module-level import of the new domain symbol
(Playlist) fails at collection (ImportError) — that IS the expected Phase-1
red evidence. The tests encode the target contract and must pass once the
production changes land:

- michi/domain/playlist.py: frozen ``Playlist(name, track_paths=())``
- michi/application/ports.py: ``PlaylistsPort`` (load/save; load never
  raises, save is best effort)
- michi/infrastructure/playlists.py: ``SqlitePlaylistsRepository`` — one
  JSON list of {"name", "track_paths"} rows under the ``"playlists"`` key of
  the shared ``library_prefs`` table (settings table and journal mode never
  touched)
- michi/application/playlist_service.py: ``PlaylistService`` — create
  (ValueError on empty/whitespace/duplicate name), delete (unknown no-op),
  rename (ValueError on empty/duplicate target, unknown old no-op), add
  (path dedupe, unknown playlist no-op), remove (bounds-checked), move
  (from bounds-checked, to clamped to [0, len-1]), play (fills the queue,
  plays first only when the queue was empty); best-effort persistence and
  change notifications on every mutation
- michi/presentation/library_bridge.py: playlist surface — ``playlists``
  rows [{name, trackCount}], ``selectedPlaylistName``, ``playlistTracks``
  rows [{displayName, path}] (displayName via resolve_trackref else
  Path.stem), and the create/delete/rename/add_to_playlist/
  remove_playlist_track/move_playlist_track/play_selected_playlist slots;
  empty/no-op when no playlist service is wired
- LibraryView.qml: 9th "Playlists" tab (GREEN phase — the QML smoke below
  is a forward pin and passes trivially on baseline)

Helpers reuse the existing fakes: FakeScanner/FakeExtractor from
tests.test_library_metadata and FakeAudioPort from tests.conftest.
FakePlaylistsPort is defined here (in-memory, seedable, records every
save).
"""

import os
import sqlite3
import sys
from pathlib import Path

import pytest
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.library_service import LibraryService
from michi.application.playback_service import PlaybackService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService

# NOTE: the domain import MUST stay first — it is the expected Phase-1
# collection failure (michi.domain.playlist does not exist on baseline).
from michi.domain.playlist import Playlist
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.library_bridge import LibraryBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


class FakePlaylistsPort:
    """In-memory PlaylistsPort: seedable; every save is recorded.

    load() returns the stored playlists (or () when never seeded/saved);
    save() stores the playlists and appends them to ``saved``. Never
    raises — mirrors the best-effort port contract.
    """

    def __init__(self, playlists=()) -> None:
        self._stored = list(playlists)
        self.saved: list[tuple[Playlist, ...]] = []

    def load(self) -> tuple[Playlist, ...]:
        return tuple(self._stored)

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        self._stored = list(playlists)
        self.saved.append(tuple(playlists))


def _make_queue():
    """Build QueueService over PlaybackService over the shared FakeAudioPort."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    return QueueService(playback), audio


def _make_library_and_queue(scanner, extractor=None):
    """Build LibraryService with a real queue; extractor is optional."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService(playback)
    if extractor is None:
        library = LibraryService(scanner, queue)
    else:
        library = LibraryService(scanner, queue, extractor)
    return library, queue, audio


def _write_tracks(tmp_path, names):
    """Create real (empty) track files and return their Paths."""
    paths = [tmp_path / name for name in names]
    for p in paths:
        p.write_bytes(b"x")
    return paths


class TestPlaylistService:
    def test_create_playlist_appends(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("Road Trip")
        assert service.playlists == (Playlist("Road Trip"),)

    def test_create_empty_name_raises(self):
        queue, _ = _make_queue()
        port = FakePlaylistsPort()
        service = PlaylistService(queue, playlists_port=port)
        with pytest.raises(ValueError):
            service.create_playlist("")
        with pytest.raises(ValueError):
            service.create_playlist("   ")
        assert service.playlists == ()
        assert port.saved == []  # validation fails before any persist

    def test_create_duplicate_name_raises(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("A")
        with pytest.raises(ValueError):
            service.create_playlist("A")
        assert service.playlists == (Playlist("A"),)

    def test_delete_playlist(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("A")
        service.create_playlist("B")
        service.delete_playlist("A")
        assert service.playlists == (Playlist("B"),)
        service.delete_playlist("ghost")  # unknown → no-op
        assert service.playlists == (Playlist("B"),)

    def test_rename_playlist(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("A")
        service.create_playlist("C")
        service.rename_playlist("A", "B")
        assert service.playlists == (Playlist("B"), Playlist("C"))
        with pytest.raises(ValueError):
            service.rename_playlist("B", "")
        with pytest.raises(ValueError):
            service.rename_playlist("B", "   ")
        with pytest.raises(ValueError):
            service.rename_playlist("B", "C")  # duplicate target ≠ old
        service.rename_playlist("ghost", "D")  # unknown old → no-op
        assert service.playlists == (Playlist("B"), Playlist("C"))

    def test_add_track_appends_and_dedupes(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("P")
        p1 = Path("/m/p1.mp3")
        service.add_track("P", p1)
        service.add_track("P", p1)  # same path → deduped
        assert service.playlists == (Playlist("P", ("/m/p1.mp3",)),)
        service.add_track("P", Path("/m/p2.mp3"))
        assert service.playlists == (Playlist("P", ("/m/p1.mp3", "/m/p2.mp3")),)

    def test_add_track_unknown_playlist_noop(self):
        queue, _ = _make_queue()
        port = FakePlaylistsPort()
        service = PlaylistService(queue, playlists_port=port)
        service.add_track("ghost", Path("/m/a.mp3"))
        assert service.playlists == ()
        assert port.saved == []  # no mutation → no persist

    def test_remove_track_bounds(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("P")
        service.add_track("P", Path("/m/a.mp3"))
        service.add_track("P", Path("/m/b.mp3"))
        service.remove_track("P", 0)
        assert service.playlists == (Playlist("P", ("/m/b.mp3",)),)
        service.remove_track("P", 5)  # out of range → no-op
        service.remove_track("P", -1)  # out of range → no-op
        assert service.playlists == (Playlist("P", ("/m/b.mp3",)),)

    def test_move_track_reorders(self):
        queue, _ = _make_queue()

        def seeded(*paths):
            service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
            service.create_playlist("P")
            for p in paths:
                service.add_track("P", Path(p))
            return service

        # pop + insert-at-clamped-position: from=0 → to=2: [a,b,c] → [b,c,a]
        s = seeded("a", "b", "c")
        s.move_track("P", 0, 2)
        assert s.playlists == (Playlist("P", ("b", "c", "a")),)

        # from=2 → to=0: [a,b,c] → [c,a,b]
        s = seeded("a", "b", "c")
        s.move_track("P", 2, 0)
        assert s.playlists == (Playlist("P", ("c", "a", "b")),)

        # out-of-range from → no-op
        s = seeded("a", "b", "c")
        s.move_track("P", 5, 1)
        s.move_track("P", -1, 0)
        assert s.playlists == (Playlist("P", ("a", "b", "c")),)

        # to clamped to [0, len-1]
        s = seeded("a", "b", "c")
        s.move_track("P", 0, 99)  # clamped to 2 → same as move(0, 2)
        assert s.playlists == (Playlist("P", ("b", "c", "a")),)
        s = seeded("a", "b", "c")
        s.move_track("P", 2, -5)  # clamped to 0 → [c,a,b]
        assert s.playlists == (Playlist("P", ("c", "a", "b")),)

    def test_play_playlist_fills_queue(self):
        queue, audio = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.create_playlist("P")
        for p in ("/m/a.mp3", "/m/b.mp3", "/m/c.mp3"):
            service.add_track("P", Path(p))
        service.play_playlist("P")
        assert queue.state.count == 3
        # play_index(0) requested: current_index commits only on acceptance.
        assert queue.state.current_index == -1
        audio.trigger_media_accepted(Path("/m/a.mp3"))
        assert queue.state.current_index == 0

    def test_play_playlist_unknown_noop(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        service.play_playlist("ghost")
        assert queue.state.count == 0

    def test_loads_at_construction(self):
        port = FakePlaylistsPort(playlists=(Playlist("Seeded", ("/m/a.mp3",)),))
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=port)
        assert service.playlists == (Playlist("Seeded", ("/m/a.mp3",)),)

    def test_mutations_persist(self):
        port = FakePlaylistsPort()
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=port)
        service.create_playlist("A")
        service.add_track("A", Path("/m/a.mp3"))
        assert port.saved[-1] == (Playlist("A", ("/m/a.mp3",)),)

    def test_notify_on_mutations(self):
        queue, _ = _make_queue()
        service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.create_playlist("A")
        assert len(calls) == 1
        service.add_track("A", Path("/m/a.mp3"))
        assert len(calls) == 2


class TestSqlitePlaylistsRepository:
    def test_repo_round_trip(self, tmp_path):
        db = tmp_path / "settings.db"
        playlists = (
            Playlist("A", ("/music/a.mp3", "/music/b.mp3")),
            Playlist("B"),
        )
        SqlitePlaylistsRepository(db).save(playlists)
        repo2 = SqlitePlaylistsRepository(db)
        assert repo2.load() == playlists

    def test_repo_empty_on_fresh(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqlitePlaylistsRepository(db)
        assert repo.load() == ()

    def test_repo_missing_file_empty(self, tmp_path):
        db = tmp_path / "settings.db"
        repo = SqlitePlaylistsRepository(db)
        assert repo.load() == ()  # never raises

    def test_repo_keeps_settings_table_untouched(self, tmp_path):
        db = tmp_path / "settings.db"
        conn = sqlite3.connect(str(db))
        conn.execute(
            "CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL)"
        )
        conn.execute("INSERT INTO settings VALUES ('volume', '80')")
        conn.commit()
        conn.close()
        repo = SqlitePlaylistsRepository(db)
        repo.save((Playlist("A", ("/music/a.mp3",)),))
        conn = sqlite3.connect(str(db))
        try:
            settings_rows = conn.execute(
                "SELECT key, value FROM settings ORDER BY key"
            ).fetchall()
            assert settings_rows == [("volume", "80")]
            prefs_rows = conn.execute(
                "SELECT key FROM library_prefs ORDER BY key"
            ).fetchall()
            assert [k for (k,) in prefs_rows] == ["playlists"]
        finally:
            conn.close()


class TestPlaylistBridge:
    def _bridge(self, tmp_path, names=("one.mp3", "two.mp3", "three.mp3")):
        paths = _write_tracks(tmp_path, names)
        library, queue, audio = _make_library_and_queue(
            FakeScanner(paths), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        return library, queue, audio, paths

    def test_bridge_rows_and_selection(self, tmp_path):
        library, queue, _, (p1, p2) = self._bridge(
            tmp_path, names=("one.mp3", "two.mp3")
        )
        playlist_service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        playlist_service.create_playlist("Road Trip")
        playlist_service.add_track("Road Trip", p1)
        playlist_service.add_track("Road Trip", p2)
        bridge = LibraryBridge(library, playlist_service)
        assert bridge.property("playlists") == [{"name": "Road Trip", "trackCount": 2}]
        bridge.select_playlist("Road Trip")
        assert bridge.property("selectedPlaylistName") == "Road Trip"
        assert bridge.property("playlistTracks") == [
            {"displayName": "T one", "path": str(p1)},
            {"displayName": "T two", "path": str(p2)},
        ]
        bridge.clear_playlist_selection()
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_bridge_no_playlist_service_compat(self, tmp_path):
        library, _, _, _ = self._bridge(tmp_path)
        bridge = LibraryBridge(library)
        assert bridge.property("playlists") == []
        bridge.select_playlist("Ghost")  # no-op, no crash
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_bridge_slots(self, tmp_path):
        library, queue, audio, (p1, p2, p3) = self._bridge(tmp_path)
        playlist_service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        bridge = LibraryBridge(library, playlist_service)

        bridge.create_playlist("Mix")
        assert bridge.property("playlists") == [{"name": "Mix", "trackCount": 0}]
        bridge.select_playlist("Mix")
        bridge.add_to_playlist("Mix", str(p1))
        bridge.add_to_playlist("Mix", str(p2))
        bridge.add_to_playlist("Mix", str(p3))
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p1),
            str(p2),
            str(p3),
        ]

        bridge.remove_playlist_track(0)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p2),
            str(p3),
        ]

        bridge.move_playlist_track(0, 1)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p3),
            str(p2),
        ]

        bridge.play_selected_playlist()
        assert queue.state.count == 2
        audio.trigger_media_accepted(p3)
        assert queue.state.current_index == 0

        # Unscanned path falls back to Path(path).stem for displayName.
        ghost = tmp_path / "ghost.mp3"
        bridge.add_to_playlist("Mix", str(ghost))
        rows = bridge.property("playlistTracks")
        assert rows[-1] == {"displayName": "ghost", "path": str(ghost)}

        bridge.delete_playlist("Mix")
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlists") == []
        bridge.dispose()

    def test_bridge_rename_slot(self, tmp_path):
        library, queue, _, _ = self._bridge(tmp_path)
        playlist_service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        bridge = LibraryBridge(library, playlist_service)
        bridge.create_playlist("A")
        bridge.rename_playlist("A", "B")
        assert bridge.property("playlists") == [{"name": "B", "trackCount": 0}]
        bridge.dispose()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_loads_with_playlists(self, qapp, tmp_path):
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, queue, _ = _make_library_and_queue(
            FakeScanner([p1]), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        playlist_service = PlaylistService(queue, playlists_port=FakePlaylistsPort())
        playlist_service.create_playlist("Road Trip")
        bridge = LibraryBridge(library, playlist_service)
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
