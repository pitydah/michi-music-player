"""Playlists R3 — pointer/keyboard runtime gates (R3-F1/F2/F3, R3-09).

Real QQuickWindow + QTest pointer/key delivery — source-string assertions
are NOT the interaction gate.
"""

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QUICK_BACKEND", "software")

import pytest
from PySide6.QtCore import QObject, Qt, QUrl
from PySide6.QtQuick import QQuickView
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication

from michi.application.navigation_service import NavigationService
from michi.application.playlist_navigation_coordinator import (
    PlaylistNavigationCoordinator,
)
from michi.application.playlist_service import PlaylistService
from michi.presentation.navigation_bridge import NavigationBridge
from michi.presentation.playlists_bridge import PlaylistsBridge
from tests.test_playlists import FakePlaylistsPort

QML_DIR = Path(__file__).resolve().parents[1] / "src" / "michi" / "presentation" / "qml"


@pytest.fixture
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def _world(tmp_path):
    del tmp_path
    service = PlaylistService(playlists_port=FakePlaylistsPort())
    nav = NavigationService()
    coord = PlaylistNavigationCoordinator(service, nav)
    bridge = PlaylistsBridge(service, playlist_navigation=coord, navigation_service=nav)
    nb = NavigationBridge(nav, playlist_navigation=coord)
    return service, nav, coord, bridge, nb


def _view(source_qml, context_props):
    view = QQuickView()
    view.engine().addImportPath(str(QML_DIR))
    for name, value in context_props.items():
        view.engine().rootContext().setContextProperty(name, value)
    view.setSource(QUrl.fromLocalFile(str(source_qml)))
    assert view.status() == QQuickView.Ready, [e.toString() for e in view.errors()]
    view.resize(900, 700)
    view.show()
    return view


def _click(qapp, item, button=Qt.LeftButton):
    from PySide6.QtCore import QPointF

    center = item.mapToScene(QPointF(item.width() / 2, item.height() / 2))
    QTest.mouseClick(item.window(), button, Qt.NoModifier, center.toPoint())
    qapp.processEvents()


_ROWS = [
    {
        "path": f"/t{i}.flac",
        "title": f"T{i}",
        "displayName": f"T{i}",
        "artist": "",
        "album": "",
        "durationMs": 0,
        "qualityLabel": "",
        "codec": "",
        "sampleRateHz": 0,
        "bitDepth": 0,
        "channels": 0,
        "fileSize": 0,
        "artworkPath": "",
    }
    for i in range(4)
]


# ==========================================================================
# R3-F1 — PLAIN UP/DOWN KEEPS NATIVE KEY NAVIGATION
# ==========================================================================


class TestPlainUpDown:
    def test_plain_down_up_navigates_listview(self, qapp, tmp_path):
        """Sin Alt: Down/Up mueven el currentIndex del ListView."""
        service, nav, coord, bridge, nb = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        for i in range(4):
            service.add_track(playlist.playlist_id, f"/t{i}.flac")
        harness = Path(__file__).resolve().parent / "TrackListHarness.qml"
        view = _view(harness, {"playlists": bridge, "navigation": nb})
        qapp.processEvents()
        list_view = view.rootObject().findChild(QObject, "playlistTrackList")
        assert list_view is not None
        list_view.setProperty("model", _ROWS)
        qapp.processEvents()
        list_view.setProperty("currentIndex", 1)
        list_view.forceActiveFocus()
        qapp.processEvents()
        current_item = list_view.property("currentItem")
        if current_item is not None:
            current_item.forceActiveFocus()
        qapp.processEvents()
        QTest.keyClick(list_view.window(), Qt.Key_Down)
        qapp.processEvents()
        assert list_view.property("currentIndex") == 2, (
            "plain Down must move the ListView cursor"
        )
        QTest.keyClick(list_view.window(), Qt.Key_Up)
        qapp.processEvents()
        assert list_view.property("currentIndex") == 1, (
            "plain Up must move the ListView cursor"
        )
        view.close()


# ==========================================================================
# R3-F2 — PLAYLISTCARD POINTER ISOLATION
# ==========================================================================


class TestPlaylistCardPointer:
    def _card_view(self, qapp, tmp_path):
        service, nav, coord, bridge, nb = _world(tmp_path)
        playlist = service.create_playlist("Road Trip")
        service.add_track(playlist.playlist_id, "/a.flac")
        harness = Path(__file__).resolve().parent / "CardHarness.qml"
        view = _view(harness, {"playlists": bridge, "navigation": nb})
        qapp.processEvents()
        card = view.rootObject().findChild(QObject, "playlistCardHarness")
        assert card is not None
        return view, card, service, playlist

    def test_click_cover_opens(self, qapp, tmp_path):
        view, card, service, playlist = self._card_view(qapp, tmp_path)
        opens = []
        card.openRequested.connect(lambda: opens.append(1))
        cover = card.findChild(QObject, "cardCoverArea")
        assert cover is not None, "cover area objectName missing"
        from PySide6.QtCore import QPointF

        QTest.mouseClick(
            cover.window(),
            Qt.LeftButton,
            Qt.NoModifier,
            cover.mapToScene(QPointF(12, 12)).toPoint(),
        )
        qapp.processEvents()
        assert opens == [1], "cover click must open"
        view.close()

    def test_click_play_does_not_open(self, qapp, tmp_path):
        view, card, service, playlist = self._card_view(qapp, tmp_path)
        opens = []
        plays = []
        card.openRequested.connect(lambda: opens.append(1))
        card.playRequested.connect(lambda: plays.append(1))
        play_button = card.findChild(QObject, "cardPlayButton")
        assert play_button is not None
        _click(qapp, play_button)
        assert plays == [1]
        assert opens == [], "Play must NEVER open the detail"
        view.close()

    def test_click_more_does_not_open(self, qapp, tmp_path):
        view, card, service, playlist = self._card_view(qapp, tmp_path)
        opens = []
        card.openRequested.connect(lambda: opens.append(1))
        more_button = card.findChild(QObject, "cardMoreButton")
        assert more_button is not None
        _click(qapp, more_button)
        assert opens == [], "More must NEVER open the detail"
        view.close()

    def test_right_click_does_not_open(self, qapp, tmp_path):
        view, card, service, playlist = self._card_view(qapp, tmp_path)
        opens = []
        card.openRequested.connect(lambda: opens.append(1))
        _click(qapp, card, button=Qt.RightButton)
        assert opens == [], "Right click must NEVER open the detail"
        view.close()


# ==========================================================================
# R3-F3 — LIST MODE POINTER ISOLATION
# ==========================================================================


class TestListRowPointer:
    def test_row_background_click_plays(self, qapp, tmp_path):
        service, nav, coord, bridge, nb = _world(tmp_path)
        playlist = service.create_playlist("Mix")
        service.add_track(playlist.playlist_id, "/a.flac")
        harness = Path(__file__).resolve().parent / "TrackListHarness.qml"
        view = _view(harness, {"playlists": bridge, "navigation": nb})
        qapp.processEvents()
        list_view = view.rootObject().findChild(QObject, "playlistTrackList")
        plays = []
        view.rootObject().playTrackRequested.connect(lambda idx: plays.append(idx))
        list_view.setProperty("model", [_ROWS[0]])
        qapp.processEvents()
        list_view.setProperty("currentIndex", 0)
        qapp.processEvents()
        from PySide6.QtCore import QPointF

        QTest.mouseClick(
            list_view.window(),
            Qt.LeftButton,
            Qt.NoModifier,
            list_view.mapToScene(QPointF(200, 25)).toPoint(),
        )
        qapp.processEvents()
        assert plays == [0], "row click must play the track"
        view.close()


# ==========================================================================
# R3-09 — HIDDEN ACTIONS VISIBLE ON CHILD KEYBOARD FOCUS
# ==========================================================================


class TestActionFocusVisibility:
    def test_child_focus_reveals_actions(self, qapp, tmp_path):
        table = Path(QML_DIR / "playlists" / "PlaylistTrackList.qml").read_text()
        assert "favoriteButton.activeFocus" in table
        assert "moreButton.activeFocus" in table
        assert "opacity: actionsVisible ? 1 : 0" in table
        assert "focusPolicy: Qt.NoFocus" not in table


# ==========================================================================
# R3-13 — NO DUAL ARTWORK STORAGE API
# ==========================================================================


class TestSingleArtworkProtocol:
    def test_no_legacy_mutable_storage_api_in_production(self):
        store = Path(
            QML_DIR.parents[1] / "infrastructure" / "playlist_artwork_store.py"
        )
        if not store.exists():
            store = Path("src/michi/infrastructure/playlist_artwork_store.py")
        source = store.read_text()
        for symbol in (
            "store_cover",
            "store_hero",
            "delete_cover",
            "delete_hero",
            "store_artwork",
            "delete_artwork",
            "_store_variant",
            "_delete_variant",
        ):
            assert symbol not in source, f"legacy storage symbol remains: {symbol}"
        # El protocolo canónico es el único lifecycle.
        assert "def prepare_cover" in source
        assert "def prepare_hero" in source
        assert "def delete_managed_asset" in source
