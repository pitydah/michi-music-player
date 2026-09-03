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
from michi.application.playback_session_service import PlaybackSessionService
from michi.application.playlist_service import PlaylistService
from michi.application.queue_service import QueueService

# NOTE: the domain import MUST stay first — it is the expected Phase-1
# collection failure (michi.domain.playlist does not exist on baseline).
from michi.domain.playlist import Playlist, PlaylistNavigationState
from michi.infrastructure.playlists import SqlitePlaylistsRepository
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.conftest import FakeAudioPort
from tests.test_library_metadata import FakeExtractor, FakeScanner

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


class FakePlaylistsPort:
    """In-memory PlaylistsPort: seedable; every save is recorded.

    load() returns the stored playlists (or () when never seeded/saved);
    save() stores the playlists and appends them to ``saved``. Never
    raises — mirrors the best-effort port contract.
    """

    def __init__(self, playlists=(), navigation=None) -> None:
        self._stored = list(playlists)
        self.saved: list[tuple[Playlist, ...]] = []
        self._nav_stored = (
            navigation if navigation is not None else PlaylistNavigationState()
        )
        self.saved_nav: list[PlaylistNavigationState] = []

    def load(self) -> tuple[Playlist, ...]:
        return tuple(self._stored)

    def save(self, playlists: tuple[Playlist, ...]) -> None:
        self._stored = list(playlists)
        self.saved.append(tuple(playlists))

    def load_navigation(self) -> PlaylistNavigationState:
        return self._nav_stored

    def save_navigation(self, state: PlaylistNavigationState) -> None:
        self._nav_stored = state
        self.saved_nav.append(state)

    def save_state(
        self,
        playlists: tuple[Playlist, ...],
        navigation: PlaylistNavigationState,
    ) -> None:
        """R3-02: atomic compound write — both snapshots published as ONE
        logical in-memory operation (no half-commit observable)."""
        self._stored = list(playlists)
        self._nav_stored = navigation
        self.saved.append(tuple(playlists))
        self.saved_nav.append(navigation)


def _make_queue():
    """Build QueueService + PlaybackSessionService over FakeAudioPort."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    session = PlaybackSessionService(playback, queue)
    return queue, session, audio


def _make_library_and_queue(scanner, extractor=None):
    """Build LibraryService with a real queue; extractor is optional."""
    audio = FakeAudioPort()
    playback = PlaybackService(audio)
    queue = QueueService()
    PlaybackSessionService(playback, queue)
    if extractor is None:
        library = LibraryService(scanner)
    else:
        library = LibraryService(scanner, metadata_extractor=extractor)
    return library, queue, audio


def _write_tracks(tmp_path, names):
    """Create real (empty) track files and return their Paths."""
    paths = [tmp_path / name for name in names]
    for p in paths:
        p.write_bytes(b"x")
    return paths


class TestPlaylistService:
    """LOCAL-06 historical behavior preserved, migrated to the M8-R1
    identity-based API: mutations take playlist_id; create returns the
    created Playlist."""

    def test_create_playlist_appends(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        created = service.create_playlist("Road Trip")
        assert created.playlist_id != ""
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("Road Trip", ())
        ]

    def test_create_empty_name_raises(self):
        queue, _, _ = _make_queue()
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        with pytest.raises(ValueError):
            service.create_playlist("")
        with pytest.raises(ValueError):
            service.create_playlist("   ")
        assert service.playlists == ()
        assert port.saved == []  # validation fails before any persist

    def test_create_duplicate_name_raises(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        service.create_playlist("A")
        with pytest.raises(ValueError):
            service.create_playlist("A")
        assert [(x.name, x.track_paths) for x in service.playlists] == [("A", ())]

    def test_delete_playlist(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        service.create_playlist("B")
        service.delete_playlist(a.playlist_id)
        assert [(x.name, x.track_paths) for x in service.playlists] == [("B", ())]
        service.delete_playlist("ghost-id")  # unknown → no-op
        assert [(x.name, x.track_paths) for x in service.playlists] == [("B", ())]

    def test_rename_playlist(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        a = service.create_playlist("A")
        service.create_playlist("C")
        service.rename_playlist(a.playlist_id, "B")
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("B", ()),
            ("C", ()),
        ]
        with pytest.raises(ValueError):
            service.rename_playlist(a.playlist_id, "")
        with pytest.raises(ValueError):
            service.rename_playlist(a.playlist_id, "   ")
        with pytest.raises(ValueError):
            service.rename_playlist(a.playlist_id, "C")  # duplicate target ≠ old
        service.rename_playlist("ghost-id", "D")  # unknown → no-op
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("B", ()),
            ("C", ()),
        ]

    def test_add_track_appends_and_dedupes(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        p = service.create_playlist("P")
        p1 = Path("/m/p1.mp3")
        service.add_track(p.playlist_id, p1)
        service.add_track(p.playlist_id, p1)  # same path → deduped
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("P", ("/m/p1.mp3",))
        ]
        service.add_track(p.playlist_id, Path("/m/p2.mp3"))
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("P", ("/m/p1.mp3", "/m/p2.mp3"))
        ]

    def test_add_track_unknown_playlist_noop(self):
        queue, _, _ = _make_queue()
        port = FakePlaylistsPort()
        service = PlaylistService(playlists_port=port)
        service.add_track("ghost-id", Path("/m/a.mp3"))
        assert service.playlists == ()
        assert port.saved == []  # no mutation → no persist

    def test_remove_track_bounds(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        p = service.create_playlist("P")
        service.add_track(p.playlist_id, Path("/m/a.mp3"))
        service.add_track(p.playlist_id, Path("/m/b.mp3"))
        service.remove_track(p.playlist_id, 0)
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("P", ("/m/b.mp3",))
        ]
        service.remove_track(p.playlist_id, 5)  # out of range → no-op
        service.remove_track(p.playlist_id, -1)  # out of range → no-op
        assert [(x.name, x.track_paths) for x in service.playlists] == [
            ("P", ("/m/b.mp3",))
        ]

    def test_move_track_reorders(self):
        queue, _, _ = _make_queue()

        def seeded(*paths):
            service = PlaylistService(playlists_port=FakePlaylistsPort())
            p = service.create_playlist("P")
            for path in paths:
                service.add_track(p.playlist_id, Path(path))
            return service, p

        # pop + insert-at-clamped-position: from=0 → to=2: [a,b,c] → [b,c,a]
        s, p = seeded("a", "b", "c")
        s.move_track(p.playlist_id, 0, 2)
        assert [(x.name, x.track_paths) for x in s.playlists] == [
            ("P", ("b", "c", "a"))
        ]

        # from=2 → to=0: [a,b,c] → [c,a,b]
        s, p = seeded("a", "b", "c")
        s.move_track(p.playlist_id, 2, 0)
        assert [(x.name, x.track_paths) for x in s.playlists] == [
            ("P", ("c", "a", "b"))
        ]

        # out-of-range from → no-op
        s, p = seeded("a", "b", "c")
        s.move_track(p.playlist_id, 5, 1)
        s.move_track(p.playlist_id, -1, 0)
        assert [(x.name, x.track_paths) for x in s.playlists] == [
            ("P", ("a", "b", "c"))
        ]

        # to clamped to [0, len-1]
        s, p = seeded("a", "b", "c")
        s.move_track(p.playlist_id, 0, 99)  # clamped to 2 → same as move(0, 2)
        assert [(x.name, x.track_paths) for x in s.playlists] == [
            ("P", ("b", "c", "a"))
        ]
        s, p = seeded("a", "b", "c")
        s.move_track(p.playlist_id, 2, -5)  # clamped to 0 → [c,a,b]
        assert [(x.name, x.track_paths) for x in s.playlists] == [
            ("P", ("c", "a", "b"))
        ]

    def test_play_playlist_sets_playlist_context(self):
        """M4-R1: Play Playlist → PLAYLIST session context; Queue NEVER
        receives the playlist tracks."""
        from michi.application.playlist_playback_coordinator import (
            PlaylistPlaybackCoordinator,
        )

        queue, session, audio = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        coordinator = PlaylistPlaybackCoordinator(service, session, queue)
        p = service.create_playlist("P")
        for path in ("/m/a.mp3", "/m/b.mp3", "/m/c.mp3"):
            service.add_track(p.playlist_id, Path(path))
        coordinator.play_playlist(p.playlist_id)
        assert queue.state.count == 0  # Queue untouched
        # context commits ONLY after backend acceptance
        assert session.state.context_type.name == "NONE"
        audio.trigger_media_accepted(Path("/m/a.mp3"))
        assert session.state.context_type.name == "PLAYLIST"
        assert session.state.count == 3
        assert session.state.current_index == 0

    def test_play_playlist_unknown_noop(self):
        from michi.application.playlist_playback_coordinator import (
            PlaylistPlaybackCoordinator,
        )

        queue, session, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        coordinator = PlaylistPlaybackCoordinator(service, session, queue)
        coordinator.play_playlist("ghost-id")
        assert queue.state.count == 0

    def test_loads_at_construction(self):
        port = FakePlaylistsPort(
            playlists=(Playlist("seeded-id", "Seeded", ("/m/a.mp3",)),)
        )
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=port)
        assert [(x.playlist_id, x.name, x.track_paths) for x in service.playlists] == [
            ("seeded-id", "Seeded", ("/m/a.mp3",))
        ]

    def test_mutations_persist(self):
        port = FakePlaylistsPort()
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=port)
        created = service.create_playlist("A")
        service.add_track(created.playlist_id, Path("/m/a.mp3"))
        saved = port.saved[-1]
        assert [(x.name, x.track_paths) for x in saved] == [("A", ("/m/a.mp3",))]

    def test_notify_on_mutations(self):
        queue, _, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        created = service.create_playlist("A")
        assert len(calls) == 1
        service.add_track(created.playlist_id, Path("/m/a.mp3"))
        assert len(calls) == 2

    def test_no_notify_for_noop_unknown(self):
        queue, session, _ = _make_queue()
        service = PlaylistService(playlists_port=FakePlaylistsPort())
        from michi.application.playlist_playback_coordinator import (
            PlaylistPlaybackCoordinator,
        )

        coordinator = PlaylistPlaybackCoordinator(service, session, queue)
        calls = []
        service.subscribe_changed(lambda: calls.append(1))
        service.delete_playlist("ghost-id")
        service.add_track("ghost-id", Path("/m/a.mp3"))
        service.remove_track("ghost-id", 0)
        coordinator.play_playlist("ghost-id")
        assert len(calls) == 0


class TestSqlitePlaylistsRepository:
    def test_repo_round_trip(self, tmp_path):
        db = tmp_path / "settings.db"
        playlists = (
            Playlist("id-a", "A", ("/music/a.mp3", "/music/b.mp3")),
            Playlist("id-b", "B"),
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
        repo.save((Playlist("id-a", "A", ("/music/a.mp3",)),))
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
    """M9-R1: canonical playlist presentation lives in PlaylistsBridge —
    LibraryBridge no longer owns playlist projection (hierarchy gate).
    M9-R1I: selection IS navigation; the bridge needs the coordinator and
    the navigation service to project the current detail."""

    def _bridge(self, tmp_path, names=("one.mp3", "two.mp3", "three.mp3")):
        paths = _write_tracks(tmp_path, names)
        library, queue, audio = _make_library_and_queue(
            FakeScanner(paths), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        return library, queue, audio, paths

    def _plb(self, queue, library, service=None):
        from michi.application.navigation_service import NavigationService
        from michi.application.playlist_navigation_coordinator import (
            PlaylistNavigationCoordinator,
        )

        service = (
            service
            if service is not None
            else PlaylistService(playlists_port=FakePlaylistsPort())
        )
        nav = NavigationService()
        service.set_on_playlist_deleted(nav.forget_playlist)
        coord = PlaylistNavigationCoordinator(service, nav)
        from michi.application.playback_session_service import (
            PlaybackSessionService,
        )
        from michi.application.playlist_playback_coordinator import (
            PlaylistPlaybackCoordinator,
        )

        _session = PlaybackSessionService(
            PlaybackService(FakeAudioPort()), QueueService()
        )
        pcoord = PlaylistPlaybackCoordinator(service, _session, QueueService())
        bridge = PlaylistsBridge(
            service,
            playlist_navigation=coord,
            navigation_service=nav,
            library=library,
            playback_coordinator=pcoord,
        )
        return bridge, coord

    def test_bridge_rows_and_selection(self, tmp_path):
        library, queue, _, (p1, p2) = self._bridge(
            tmp_path, names=("one.mp3", "two.mp3")
        )
        playlist_service = PlaylistService(playlists_port=FakePlaylistsPort())
        trip = playlist_service.create_playlist("Road Trip")
        playlist_service.add_track(trip.playlist_id, p1)
        playlist_service.add_track(trip.playlist_id, p2)
        bridge, _ = self._plb(queue, library, playlist_service)
        assert [
            (
                r["name"],
                r["trackCount"],
                "playlistId" in r,
                "pinned" in r,
                "recentRank" in r,
            )
            for r in bridge.property("playlists")
        ] == [("Road Trip", 2, True, True, True)]
        bridge.open_playlist(trip.playlist_id)
        assert bridge.property("selectedPlaylistName") == "Road Trip"
        # Identity recovery: las filas del detalle ahora transportan
        # trackId (vacío para tracks legacy/harness sin catálogo).
        assert bridge.property("playlistTracks") == [
            {"displayName": "T one", "path": str(p1), "trackId": ""},
            {"displayName": "T two", "path": str(p2), "trackId": ""},
        ]
        bridge.open_all_playlists()
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_bridge_no_playlist_service_compat(self, tmp_path):
        library, _, _, _ = self._bridge(tmp_path)
        bridge = PlaylistsBridge()
        assert bridge.property("playlists") == []
        bridge.open_playlist("Ghost")  # no-op, no crash
        assert bridge.property("selectedPlaylistName") == ""
        assert bridge.property("playlistTracks") == []
        bridge.dispose()

    def test_bridge_slots(self, tmp_path):
        library, queue, audio, (p1, p2, p3) = self._bridge(tmp_path)
        playlist_service = PlaylistService(playlists_port=FakePlaylistsPort())
        bridge, _ = self._plb(queue, library, playlist_service)

        bridge.create_and_open_playlist("Mix")
        assert [(r["name"], r["trackCount"]) for r in bridge.property("playlists")] == [
            ("Mix", 0)
        ]
        created = playlist_service.playlists[0]
        bridge.open_playlist(created.playlist_id)
        bridge.add_track_to_playlist(created.playlist_id, str(p1))
        bridge.add_track_to_playlist(created.playlist_id, str(p2))
        bridge.add_track_to_playlist(created.playlist_id, str(p3))
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p1),
            str(p2),
            str(p3),
        ]

        bridge.remove_track(0)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p2),
            str(p3),
        ]

        bridge.move_track(0, 1)
        assert [r["path"] for r in bridge.property("playlistTracks")] == [
            str(p3),
            str(p2),
        ]

        bridge.play_selected_playlist()
        # M4-R1: Play → PLAYLIST session context; Queue NEVER receives the
        # playlist tracks.
        assert queue.state.count == 0
        bridge.dispose()

    def test_bridge_rename_slot(self, tmp_path):
        library, queue, _, _ = self._bridge(tmp_path)
        playlist_service = PlaylistService(playlists_port=FakePlaylistsPort())
        bridge, _ = self._plb(queue, library, playlist_service)
        bridge.create_and_open_playlist("A")
        created = playlist_service.playlists[0]
        assert bridge.rename_playlist(created.playlist_id, "B") == "renamed"
        assert [(r["name"], r["trackCount"]) for r in bridge.property("playlists")] == [
            ("B", 0)
        ]
        bridge.dispose()


@pytest.fixture(scope="module")
def qapp():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    app = QGuiApplication.instance()
    if app is None:
        app = QGuiApplication(sys.argv)
    yield app


class TestQmlSmoke:
    def test_library_view_loads_without_playlists(self, qapp, tmp_path):
        """M9-R1 hierarchy: LibraryView no longer hosts a Playlists tab —
        Playlists is a first-class Shell feature (PLAYLIST-HIERARCHY-01/02)."""
        p1 = tmp_path / "one.mp3"
        p1.write_bytes(b"x")
        library, queue, _ = _make_library_and_queue(
            FakeScanner([p1]), extractor=FakeExtractor()
        )
        library.scan(str(tmp_path))
        playlist_service = PlaylistService(playlists_port=FakePlaylistsPort())
        playlist_service.create_playlist("Road Trip")
        bridge = LibraryBridge(library)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", bridge)
        component = QQmlComponent(engine, str(QML_DIR / "views/LibraryView.qml"))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
        obj = component.create()
        assert obj is not None, "LibraryView: null object"
        # hierarchy proof: no playlist tab in the Library rail
        tabs = (
            Path(__file__).parent.parent
            / "src"
            / "michi"
            / "presentation"
            / "qml"
            / "views"
            / "LibraryTabs.qml"
        ).read_text()
        assert 'value: "playlists"' not in tabs
        obj.deleteLater()
        bridge.dispose()
