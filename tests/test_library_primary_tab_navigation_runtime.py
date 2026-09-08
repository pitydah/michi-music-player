"""POST-R4 P2 — Library primary-tab ↔ entity-detail navigation runtime.

LibraryView productivo montado sobre un bridge con catálogo REAL:

- Album Detail → Songs: currentTab == songs y selectedAlbumKey == "";
- Album Detail → Albums: vuelve al BROWSE raíz (selectedAlbumKey == "");
- Artist Detail → Favorites / Artists: idem;
- los library_changed POSTERIORES a la transición nunca revierten el tab
  (el bounce-back de syncEntitySelection queda prohibido).
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import QCoreApplication, QObject, QUrl  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402

from tests.test_search_overlay_canonical_projection_runtime import (  # noqa: E402
    _five_category_world,
)

QML_DIR = (
    Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"
)


@pytest.fixture(scope="module")
def qapp():
    from PySide6.QtGui import QGuiApplication

    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


def _pump(ms=30):
    from PySide6.QtTest import QTest

    QTest.qWait(ms)


def _mount_library_view(tmp_path):
    """LibraryView PRODUCTIVO (componente real) con el bridge de catálogo
    real en contexto — el mismo harness que el smoke LIB-A."""
    world = _five_category_world(tmp_path)
    engine = QQmlEngine()
    engine.addImportPath(str(QML_DIR))
    engine.rootContext().setContextProperty("library", world["lb"])
    component = QQmlComponent(engine, str(QML_DIR / "views" / "LibraryView.qml"))
    errs = "; ".join(e.toString() for e in component.errors())
    assert component.status() == QQmlComponent.Ready, f"LibraryView: {errs}"
    obj = component.create()
    assert obj is not None, "LibraryView: null object"
    if not hasattr(engine, "_held"):
        engine._held = []
    engine._held.append(component)
    _pump()
    world["engine"] = engine
    world["view"] = obj
    return world


class TestPrimaryTabNavigation:
    def _album(self, world):
        return world["library"].state.albums[0]

    def _artist(self, world):
        return world["library"].state.artists[0]

    def test_album_detail_to_songs_clears_album_selection(self, tmp_path, qapp):
        world = _mount_library_view(tmp_path)
        lb = world["lb"]
        view = world["view"]
        key = self._album(world).key
        lb.select_album(key)
        _pump()
        assert view.property("currentTab") == "albums", "el detail vive en Albums"
        assert lb.property("selectedAlbumKey") == key
        # click productivo del primary tab Songs.
        view.requestTab("songs")
        _pump()
        assert view.property("currentTab") == "songs"
        assert lb.property("selectedAlbumKey") == "", "selección de detalle retirada"
        assert lb.property("selectedArtistKey") == ""
        # library_changed posteriores NO pueden revertir a Albums.
        lb.library_changed.emit()
        _pump()
        lb.library_changed.emit()
        _pump()
        assert view.property("currentTab") == "songs", "bounce-back prohibido"

    def test_album_detail_to_albums_returns_to_browse(self, tmp_path, qapp):
        world = _mount_library_view(tmp_path)
        lb = world["lb"]
        view = world["view"]
        key = self._album(world).key
        lb.select_album(key)
        _pump()
        # click explícito sobre el primary tab Albums → browse raíz.
        view.requestTab("albums")
        _pump()
        assert view.property("currentTab") == "albums"
        assert lb.property("selectedAlbumKey") == "", "browse raíz (sin detalle)"
        lb.library_changed.emit()
        _pump()
        assert view.property("currentTab") == "albums"

    def test_artist_detail_to_favorites_clears_artist_selection(
        self, tmp_path, qapp
    ):
        world = _mount_library_view(tmp_path)
        lb = world["lb"]
        view = world["view"]
        key = self._artist(world).key
        lb.select_artist(key)
        _pump()
        assert view.property("currentTab") == "artists"
        view.requestTab("favorites")
        _pump()
        assert view.property("currentTab") == "favorites"
        assert lb.property("selectedArtistKey") == ""
        lb.library_changed.emit()
        _pump()
        assert view.property("currentTab") == "favorites", "sin bounce-back"

    def test_artist_detail_to_artists_returns_to_browse(self, tmp_path, qapp):
        world = _mount_library_view(tmp_path)
        lb = world["lb"]
        view = world["view"]
        key = self._artist(world).key
        lb.select_artist(key)
        _pump()
        view.requestTab("artists")
        _pump()
        assert view.property("currentTab") == "artists"
        assert lb.property("selectedArtistKey") == "", "browse raíz de Artists"
        lb.library_changed.emit()
        _pump()
        assert view.property("currentTab") == "artists"

    def test_toolbar_routes_through_requestTab(self, tmp_path, qapp):
        """El toolbar consume requestTab — nunca vuelve a escribir
        root.currentTab directamente."""
        src = (QML_DIR / "views" / "LibraryView.qml").read_text(
            encoding="utf-8", errors="ignore"
        )
        toolbar_seg = src[src.index("LibraryToolbar {") :]
        toolbar_seg = toolbar_seg[: toolbar_seg.index("LibraryContentHost")]
        assert "root.requestTab(tab)" in toolbar_seg
        assert "root.currentTab = tab" not in toolbar_seg
