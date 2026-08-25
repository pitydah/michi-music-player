"""M9-R1: playlist detail + search-navigation convergence gates.

- Detail resolves from PLAYLISTS + playlist_id; rename keeps id; delete
  converges to All Playlists.
- Search result activates the first-class route via open_playlist (validated,
  Recent updated, Library never activated).
- QML smoke for the new playlists components (no ReferenceError/import
  failures with realistic bridge fakes).
"""

from pathlib import Path

import pytest
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.domain.navigation import AppRoute
from michi.presentation.library_bridge import LibraryBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_library_metadata import FakeExtractor, FakeScanner
from tests.test_playlists import FakePlaylistsPort, _make_library_and_queue

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication([])
    yield app


def _world(tmp_path, with_engine=False):
    paths = [tmp_path / "a.mp3", tmp_path / "b.mp3"]
    for p in paths:
        p.write_bytes(b"x")
    library, queue, _ = _make_library_and_queue(
        FakeScanner(paths), extractor=FakeExtractor()
    )
    library.scan(str(tmp_path))
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    service.set_on_playlist_deleted(nav.forget_playlist)
    coord = PlaylistNavigationCoordinator(service, nav)
    lb = LibraryBridge(library)
    pb = PlaylistsBridge(service, playlist_navigation=coord, library=library)
    engine = None
    if with_engine:
        from michi.presentation.navigation_bridge import NavigationBridge

        nb = NavigationBridge(nav, playlist_navigation=coord)
        engine = QQmlEngine()
        engine.addImportPath(str(QML_DIR))
        engine.rootContext().setContextProperty("library", lb)
        engine.rootContext().setContextProperty("playlists", pb)
        engine.rootContext().setContextProperty("navigation", nb)
    return engine, service, nav, coord, pb


class TestDetailSemantics:
    def test_rename_keeps_target(self):
        engine, service, nav, coord, pb = _world(Path("/tmp"))
        a = service.create_playlist("A")
        nav.navigate_to_playlist(a.playlist_id)
        service.rename_playlist(a.playlist_id, "A Long Name")
        assert nav.state.playlist_id == a.playlist_id
        assert nav.state.current_route == AppRoute.PLAYLISTS

    def test_delete_converges_to_all(self):
        engine, service, nav, coord, pb = _world(Path("/tmp"))
        a = service.create_playlist("A")
        coord.open_playlist(a.playlist_id)
        assert nav.state.playlist_id == a.playlist_id
        service.delete_playlist(a.playlist_id)
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id is None

    def test_invalid_id_falls_back(self):
        engine, service, nav, coord, pb = _world(Path("/tmp"))
        coord.open_playlist("ghost-id")
        assert nav.state.playlist_id is None
        assert nav.state.current_route == AppRoute.PLAYLISTS


class TestSearchNavigation:
    def test_search_result_opens_first_class_route(self):
        engine, service, nav, coord, pb = _world(Path("/tmp"))
        a = service.create_playlist("Road Trip")
        pb._library.search("Road")
        rows = pb.property("searchPlaylists")
        assert rows and rows[0]["playlistId"] == a.playlist_id
        coord.open_playlist(rows[0]["playlistId"])
        assert nav.state.current_route == AppRoute.PLAYLISTS
        assert nav.state.playlist_id == a.playlist_id
        assert service.navigation.recent_ids == (a.playlist_id,)
        assert nav.state.current_route is not AppRoute.LIBRARY


class TestQmlSmoke:
    def _load(self, engine, rel):
        component = QQmlComponent(engine, str(QML_DIR / rel))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
        return component.create()

    def test_playlists_view_smoke(self, qapp, tmp_path):
        engine, service, _, _, _ = _world(tmp_path, with_engine=True)
        a = service.create_playlist("Jazz")
        service.pin_playlist(a.playlist_id)
        obj = self._load(engine, "playlists/PlaylistsView.qml")
        assert obj is not None
        engine.deleteLater()

    def test_playlist_detail_smoke(self, qapp, tmp_path):
        engine, service, nav, coord, pb = _world(tmp_path, with_engine=True)
        # the _world bridge lacks navigation_service, so open_playlist would
        # never project into the QML surface — rebuild it wired to the nav
        pb = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav, library=None
        )
        engine.rootContext().setContextProperty("playlists", pb)
        a = service.create_playlist("Jazz")
        service.add_track(a.playlist_id, str(tmp_path / "a.mp3"))
        coord.open_playlist(a.playlist_id)
        obj = self._load(engine, "playlists/PlaylistDetailView.qml")
        assert obj is not None
        engine.deleteLater()

    def test_playlist_create_dialog_smoke(self, qapp, tmp_path):
        engine, *_ = _world(tmp_path, with_engine=True)
        obj = self._load(engine, "playlists/PlaylistCreateDialog.qml")
        assert obj is not None
        engine.deleteLater()

    def test_playlist_card_smoke(self, qapp, tmp_path):
        engine, *_ = _world(tmp_path, with_engine=True)
        obj = self._load(engine, "playlists/PlaylistCard.qml")
        assert obj is not None
        engine.deleteLater()

    def test_playlist_track_list_smoke(self, qapp, tmp_path):
        engine, service, _, coord, pb = _world(tmp_path, with_engine=True)
        a = service.create_playlist("Jazz")
        service.add_track(a.playlist_id, str(tmp_path / "a.mp3"))
        coord.open_playlist(a.playlist_id)
        obj = self._load(engine, "playlists/PlaylistTrackList.qml")
        assert obj is not None
        engine.deleteLater()

    def test_content_host_smoke(self, qapp, tmp_path):
        engine, service, _, _, _ = _world(tmp_path, with_engine=True)
        service.create_playlist("Jazz")
        obj = self._load(engine, "shell/ContentHost.qml")
        assert obj is not None
        engine.deleteLater()


class TestEditorialHeroRuntime:
    """M9-R2.5 regression: the editorial hero header must ACTUALLY appear in
    a real window. ListView.header assigns to an internal QQmlComponent
    slot — passing a pre-instantiated Item fails the conversion and the
    header silently never shows; the hero must also complete its fade-in.
    """

    def _load(self, engine, rel):
        component = QQmlComponent(engine, str(QML_DIR / rel))
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"{rel}: {errs}"
        return component.create()

    def test_hero_header_visible_with_height_and_fade(self, qapp, tmp_path):
        from PySide6.QtCore import QEventLoop, QTimer
        from PySide6.QtQuick import QQuickWindow

        engine, service, nav, coord, pb = _world(tmp_path, with_engine=True)
        # the _world bridge lacks navigation_service, so open_playlist would
        # never project into the QML surface — rebuild it wired to the nav
        pb = PlaylistsBridge(
            service, playlist_navigation=coord, navigation_service=nav, library=None
        )
        engine.rootContext().setContextProperty("playlists", pb)
        a = service.create_playlist("Jazz")
        service.add_track(a.playlist_id, str(tmp_path / "a.mp3"))
        coord.open_playlist(a.playlist_id)

        # keep the QQmlComponent alive in this scope: the created page has
        # no parent yet, and losing the component lets the engine GC
        # destroy the page before it is attached to the window
        component = QQmlComponent(
            engine, str(QML_DIR / "playlists" / "PlaylistDetailView.qml")
        )
        errs = "; ".join(e.toString() for e in component.errors())
        assert component.status() == QQmlComponent.Ready, f"detail: {errs}"
        page = component.create()
        win = QQuickWindow()
        win.resize(1200, 800)
        page.setParentItem(win.contentItem())
        win.show()

        # let the scene graph run real frames (offscreen still animates)
        loop = QEventLoop()
        for _ in range(12):
            QTimer.singleShot(30, loop.quit)
            loop.exec()

        # keep the window referenced so Python GC does not destroy the
        # scene (and with it every item) mid-test — reference it BEFORE
        # any findChild/property access
        assert win.isVisible()
        assert pb.property("selectedPlaylistName") == "Jazz", (
            "bridge did not select the playlist"
        )

        track_list = page.findChild(type(page), "playlistTrackList")
        assert track_list is not None, "track list not found"
        header = track_list.property("headerItem")
        assert header is not None, "hero header was never instantiated"
        assert header.property("height") > 0, "hero collapsed to zero height"
        hero = page.findChild(type(page), "playlistHero")
        assert hero is not None, "playlist hero missing inside the header"
        # live data via the null-safe Component bindings
        assert hero.property("playlistName") == "Jazz"
        # fade-in (MichiMotion.panel = 220ms) must have completed
        assert hero.property("opacity") > 0.9, (
            f"hero fade-in did not complete: opacity={hero.property('opacity')}"
        )
        engine.deleteLater()
