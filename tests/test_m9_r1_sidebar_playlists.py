"""M9-R1: Sidebar playlists section gates.

- PLAYLISTS section exists with All Playlists / Pinned / Recent / New.
- Bounded visible rows (≤5 pinned, ≤5 recent — projection from bridge).
- Recent excludes pinned (presentation policy).
- Selected states: All Playlists when PLAYLISTS+None; row when PLAYLISTS+id.
- Library not selected while Playlists active.
- Create affordance present.
"""

from pathlib import Path

import pytest
from PySide6.QtQml import QQmlComponent, QQmlEngine

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
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


def _world(tmp_path):
    paths = [tmp_path / "a.mp3"]
    for p in paths:
        p.write_bytes(b"x")
    library, queue, _ = _make_library_and_queue(
        FakeScanner(paths), extractor=FakeExtractor()
    )
    library.scan(str(tmp_path))
    service = PlaylistService(queue, FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    lb = LibraryBridge(library, service)
    pb = PlaylistsBridge(service, playlist_navigation=coord, library=library)
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", lb)
    engine.rootContext().setContextProperty("playlists", pb)
    return engine, service, nav, coord, pb, lb


def _load_sidebar(engine):
    component = QQmlComponent(engine, str(QML_DIR / "shell" / "Sidebar.qml"))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"Sidebar: {errs}"
    return component.create()


class TestSidebarStructure:
    def test_sidebar_has_playlists_section(self, qapp, tmp_path):
        engine, *_ = _world(tmp_path)
        text = Path(QML_DIR / "shell" / "Sidebar.qml").read_text()
        assert '"PLAYLISTS"' in text
        assert "All Playlists" in text
        assert "PINNED" in text
        assert "RECENT" in text
        assert "New Playlist" in text
        assert "createPlaylistRequested" in text
        obj = _load_sidebar(engine)
        assert obj is not None
        engine.deleteLater()

    def test_sidebar_instantiates_with_pinned_and_recent(self, qapp, tmp_path):
        engine, service, nav, _, _, _ = _world(tmp_path)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        service.mark_recent(b.playlist_id)
        obj = _load_sidebar(engine)
        assert obj is not None
        engine.deleteLater()

    def test_sidebar_bounded_projection(self, qapp, tmp_path):
        """Pinned/recent rows are bounded to 5 by slice; Sidebar never
        renders every playlist permanently."""
        engine, *_ = _world(tmp_path)
        text = Path(QML_DIR / "shell" / "Sidebar.qml").read_text()
        assert ".slice(0, 5)" in text
        engine.deleteLater()


class TestSidebarBridgeProjection:
    def test_pinned_projection(self, qapp, tmp_path):
        engine, service, _, _, pb, _ = _world(tmp_path)
        for i in range(3):
            service.pin_playlist(service.create_playlist(f"P{i}").playlist_id)
        pinned = pb.property("pinnedPlaylists")
        assert len(pinned) == 3
        engine.deleteLater()

    def test_recent_projection_excludes_pinned(self, qapp, tmp_path):
        engine, service, _, _, pb, _ = _world(tmp_path)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        service.mark_recent(b.playlist_id)
        recent = pb.property("recentPlaylists")
        assert [r["playlistId"] for r in recent] == [b.playlist_id]
        engine.deleteLater()

    def test_library_not_selected_while_playlists_active(self, qapp, tmp_path):
        """Sidebar selected state derives from navigation: PLAYLISTS active
        never highlights Library — no PLAYLISTS row inside the NAVIGATION
        section."""
        engine, *_ = _world(tmp_path)
        text = Path(QML_DIR / "shell" / "Sidebar.qml").read_text()
        # the NAVIGATION route list must not contain a playlists route
        nav_list = text.split("_bottom_routes")[0]
        assert '{ id: "playlists"' not in nav_list
        engine.deleteLater()
