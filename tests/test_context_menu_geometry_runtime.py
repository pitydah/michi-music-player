# ruff: noqa: N815
"""R10 P1 — Context menu geometry runtime gates (V4 §14).

The reported production regression: right-click could render a
horizontal LINE instead of a usable menu. These gates open the
productive menus in a real Window (software/offscreen) and assert
usable geometry: width/height minima, actionable item geometry, and
on-screen placement. A collapsed 200×1 popup must FAIL here.
"""

import os
import sys
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

from PySide6.QtCore import Property, QObject, QUrl  # noqa: E402
from PySide6.QtGui import QGuiApplication  # noqa: E402
from PySide6.QtQml import QQmlComponent, QQmlEngine  # noqa: E402
from PySide6.QtTest import QTest  # noqa: E402

QML = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"

_HARNESS_TEMPLATE = """import QtQuick
import QtQuick.Window
import "{qml}/media"

Window {
    id: harness
    visible: true
    width: 900
    height: 700
    color: "#000000"

    {component} {
        id: target
    }
}
"""


_KEPT: list = []


@pytest.fixture(scope="module")
def qapp():
    app = QGuiApplication.instance() or QGuiApplication(sys.argv)
    yield app


class _Library(QObject):
    canQueueTracks = Property(bool, lambda self: True)
    canAddTracksToPlaylists = Property(bool, lambda self: True)
    searchActive = Property(bool, lambda self: False)

    def select_album(self, key):
        del key

    def select_artist(self, key):
        del key

    def select_genre(self, key):
        del key

    def play_album(self, key):
        del key

    def queue_album(self, key):
        del key

    def queue_artist(self, key):
        del key

    def request_album_playlist_target(self, key):
        del key

    def request_new_playlist_for_album(self, key):
        del key

    def request_album_properties(self, key):
        del key

    def request_artist_playlist_target(self, key):
        del key

    def request_new_playlist_for_artist(self, key):
        del key


def _mount(qapp, component_type, props=None):
    """Harness: Window real — los menús solo abren con popup() con window."""
    template = _HARNESS_TEMPLATE.replace("{qml}", QML.as_uri())
    template = template.replace("{component}", component_type)
    library = _Library()
    engine = QQmlEngine()
    engine.addImportPath(str(QML))
    engine.rootContext().setContextProperty("library", library)
    comp = QQmlComponent(engine)
    # El base es un harness neutro del MISMO directorio: el nombre del
    # componente importado no puede coincidir con el del archivo base.
    comp.setData(
        template.encode("utf-8"),
        QUrl.fromLocalFile(str(QML / "media" / "_geometry_harness.qml")),
    )
    assert comp.status() == QQmlComponent.Ready, comp.errorString()
    window = comp.create()
    assert window is not None
    window.show()
    for _ in range(10):
        QTest.qWait(20)
    _KEPT.append((engine, comp, window))
    target = _target_menu(window)
    assert target is not None, f"instancia de {component_type} no hallada"
    if props:
        for name, value in props.items():
            target.setProperty(name, value)
    QTest.qWait(120)
    return window


def _target_menu(window):
    for child in window.findChildren(QObject):
        cls = child.metaObject().className()
        if "Menu" in cls and child.objectName() == "":
            return child
    return None


def _find_menu(window):
    for child in window.findChildren(QObject):
        cls = child.metaObject().className()
        if "Menu" in cls and child.property("visible") is True:
            return child
    return None


def _open_menu(window):
    target = _target_menu(window)
    meta = target.metaObject()
    idx = meta.indexOfMethod("popup()")
    assert idx >= 0, "popup() expuesto"
    assert meta.method(idx).invoke(target)
    QTest.qWait(200)
    return _find_menu(window)


def assert_menu_geometry(menu, *, min_width=240, min_height=40):
    assert menu.property("visible") is True
    width = float(menu.property("width") or 0)
    height = float(menu.property("height") or 0)
    assert width >= min_width, f"collapsed menu width: {width}px < {min_width}px"
    assert height >= min_height, f"collapsed menu height: {height}px < {min_height}px"


def _visible_actionable_items(menu):
    """Items habilitados con geometría real (el info header está
    disabled: no cuenta)."""
    found = []
    for child in menu.findChildren(QObject):
        try:
            if child.property("enabled") is not True:
                continue
            text = child.property("text")
            width = float(child.property("width") or 0)
            height = float(child.property("height") or 0)
            if str(text or "").strip() and width >= 220 and height >= 32:
                found.append((str(text), width, height))
        except RuntimeError:
            continue
    return found


class TestTrackMenuGeometry:
    def test_track_menu_never_collapses(self, qapp):
        window = _mount(
            qapp,
            "TrackContextMenu",
            props={
                "titleText": "So What",
                "artistText": "Miles",
                "albumText": "Kind of Blue",
                "formatKey": "flac",
                "formatLabel": "FLAC",
                "canPlayNow": True,
                "canQueue": True,
                "canAddToPlaylist": True,
                "canAddToNewPlaylist": True,
                "canFavorite": True,
                "canGoToAlbum": True,
                "canGoToArtist": True,
                "canShowProperties": True,
            },
        )
        menu = _open_menu(window)
        assert menu is not None, "menú de track abierto"
        assert_menu_geometry(menu, min_width=260, min_height=160)
        # Posición dentro de la ventana (nunca desplazado a 0/offscreen).
        x = float(menu.property("x") or 0)
        y = float(menu.property("y") or 0)
        w = float(menu.property("width") or 0)
        h = float(menu.property("height") or 0)
        assert x + w > 0 and y + h > 0
        assert x < 900 and y < 700
        items = _visible_actionable_items(menu)
        assert len(items) >= 3, f"items accionables: {items}"
        window.close()


class TestHeaderMenuNestedSubmenu:
    def test_nested_columns_submenu_has_geometry(self, qapp):
        """R10.2 (§14.3): el submenú Columns del menú del header es un
        submenú NATIVO real con geometría usable — nunca un popup
        colapsado ni un item muerto."""
        window = _mount(qapp, "TrackTableHeaderContextMenu")
        menu = _open_menu(window)
        assert menu is not None, "menú del header abierto"
        assert_menu_geometry(menu, min_width=260, min_height=120)

        # El submenú Columns: instancia nativa MichiMenu dentro del root.
        submenu = None
        for child in window.findChildren(QObject):
            if child.property("title") == "Columns":
                submenu = child
                break
        assert submenu is not None, "submenú Columns no hallado"
        meta = submenu.metaObject()
        idx = meta.indexOfMethod("popup()")
        assert idx >= 0
        assert meta.method(idx).invoke(submenu)
        QTest.qWait(180)
        assert submenu.property("visible") is True
        w = float(submenu.property("width") or 0)
        h = float(submenu.property("height") or 0)
        assert w >= 260, f"submenú colapsado: {w}px"
        assert h > 60, f"submenú sin contenido: {h}px"
        # Items accionables dentro del submenú (Artwork/Artist checks).
        items = _visible_actionable_items(submenu)
        assert len(items) >= 3, f"items del submenú: {items}"
        # Dentro de la ventana.
        x = float(submenu.property("x") or 0)
        y = float(submenu.property("y") or 0)
        assert x + w > 0 and y + h > 0
        assert x < 900 and y < 700
        window.close()

    def test_nested_preset_submenu_lists_all_presets(self, qapp):
        window = _mount(qapp, "TrackTableHeaderContextMenu")
        menu = _open_menu(window)
        assert menu is not None
        submenu = None
        for child in window.findChildren(QObject):
            if child.property("title") == "Preset":
                submenu = child
                break
        assert submenu is not None, "submenú Preset no hallado"
        meta = submenu.metaObject()
        assert meta.method(meta.indexOfMethod("popup()")).invoke(submenu)
        QTest.qWait(180)
        labels = {
            str(c.property("text"))
            for c in submenu.findChildren(QObject)
            if isinstance(c.property("text"), str) and c.property("text")
        }
        for preset in ("Essential", "Audiophile", "Metadata", "Minimal"):
            assert preset in labels, f"preset {preset} ausente del submenú"
        window.close()


class TestAlbumArtistGenreGeometry:
    def test_album_menu_geometry(self, qapp):
        window = _mount(
            qapp,
            "AlbumContextMenu",
            props={
                "album": {
                    "key": "a1",
                    "title": "Album",
                    "artist": "Artist",
                    "year": 2020,
                    "hasArtwork": False,
                    "artistKey": "ar1",
                },
                "canAddToPlaylist": True,
                "canCreatePlaylist": True,
                "canShowProperties": True,
            },
        )
        menu = _open_menu(window)
        assert menu is not None, "menú de álbum abierto"
        assert_menu_geometry(menu, min_width=260, min_height=140)
        window.close()

    def test_artist_menu_geometry(self, qapp):
        window = _mount(
            qapp,
            "ArtistContextMenu",
            props={
                "artist": {
                    "key": "ar1",
                    "name": "Artist",
                    "albumCount": 1,
                    "trackCount": 10,
                    "artworkPath": "",
                },
                "canAddToPlaylist": True,
                "canCreatePlaylist": True,
            },
        )
        menu = _open_menu(window)
        assert menu is not None, "menú de artista abierto"
        assert_menu_geometry(menu, min_width=260, min_height=100)
        window.close()

    def test_genre_menu_geometry(self, qapp):
        window = _mount(
            qapp,
            "GenreContextMenu",
            props={"genre": {"key": "rock", "name": "Rock"}},
        )
        menu = _open_menu(window)
        assert menu is not None, "menú de género abierto"
        assert_menu_geometry(menu, min_width=260, min_height=36)
        window.close()
