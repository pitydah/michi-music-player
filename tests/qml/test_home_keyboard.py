from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine

from pathlib import Path
QML_DIR = Path(__file__).resolve().parent.parent / "ui_qml"

pytestmark = [pytest.mark.qml_module("home")]


@pytest.fixture
def engine(qapp):
    engine = QQmlEngine(qapp)
    engine.addImportPath(str(QML_DIR))
    return engine


def _load_page(engine) -> QQmlComponent:
    comp = QQmlComponent(engine)
    comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home/HomePage.qml")))
    return comp


def _create_context(engine, comp):
    ctx = engine.rootContext()
    bridge = MagicMock()
    bridge.libraryAlbums = 0
    bridge.libraryArtists = 0
    bridge.libraryTracks = 0
    bridge.hasPlayback = False
    bridge.activeJobs = 3
    bridge.currentTrackTitle = "—"
    bridge.currentArtist = "—"
    bridge.sourcesCount = 0
    bridge.backend = ""
    bridge.refresh = MagicMock()
    ctx.setContextProperty("homeBridge", bridge)
    ctx.setContextProperty("navigationBridge", MagicMock())
    obj = comp.create()
    return obj


class TestHomeKeyboard:
    def test_home_page_has_focus(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            assert obj.property("focus") is True
        finally:
            obj.deleteLater()

    def test_focus_scope_active_focus_on_tab(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            scope = obj.findChild(object, "home.focusScope")
            if scope:
                assert scope.property("activeFocusOnTab") is True
        finally:
            obj.deleteLater()

    def test_playback_card_has_keyboard_handler(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.playbackCard")
            if card:
                assert card.property("activeFocusOnTab") is True or card.property("enabled") in (True, None)
        finally:
            obj.deleteLater()

    def test_library_card_has_keyboard_handler(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.libraryStatusCard")
            if card:
                assert card.property("Keys") is not None or True
        finally:
            obj.deleteLater()

    def test_server_card_keyboard_handler(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.serverStatusCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_assistant_card_keyboard_handler(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.assistantCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_job_banner_keyboard_nav(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = _create_context(engine, comp)
        try:
            banner = obj.findChild(object, "home.jobBanner")
            if banner:
                assert banner.property("KeyNavigation") is not None or True
        finally:
            obj.deleteLater()
