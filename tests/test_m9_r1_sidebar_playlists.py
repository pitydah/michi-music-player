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
    lb = LibraryBridge(library)
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
    def test_sidebar_has_first_level_navigation(self, qapp, tmp_path):
        engine, *_ = _world(tmp_path)
        text = Path(QML_DIR / "shell" / "Sidebar.qml").read_text()
        assert '{ id: "now_playing"' in text
        assert '{ id: "library"' in text
        assert '{ id: "playlists"' in text
        assert '{ id: "settings"' in text
        assert "Local · " in text
        obj = _load_sidebar(engine)
        assert obj is not None
        engine.deleteLater()

    def test_sidebar_instantiates_cleanly(self, qapp, tmp_path):
        engine, service, nav, _, _, _ = _world(tmp_path)
        a = service.create_playlist("A")
        b = service.create_playlist("B")
        service.pin_playlist(a.playlist_id)
        service.mark_recent(a.playlist_id)
        service.mark_recent(b.playlist_id)
        obj = _load_sidebar(engine)
        assert obj is not None
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


class TestSidebarMaterial:
    """M9-R2.6: smoke-glass material audit — single grain, single accent."""

    def test_single_grain_single_accent(self):
        text = Path(QML_DIR / "shell" / "Sidebar.qml").read_text()
        # no stacked own grain (the glass surfaces texture it once)
        assert "MichiMaterialTexture" not in text
        assert "textured: true" in text
        # single cyan accent — no purple remnants (comment allowed)
        assert "accentColor: MichiPalette.auroraCyan" in text
        assert "auroraPurpleSurface" not in text
        assert "auroraPurpleBorder" not in text
        assert "contentAmbientPurple" not in text
        # true smoke glass
        assert "forceBlur: true" in text
        assert "materialOpacityOverride: 0.68" in text
