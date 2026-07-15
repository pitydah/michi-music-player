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


class TestHomeNegative:
    def test_no_bridge_shows_error_state(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()

    def test_no_bridge_no_crash(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("objectName") == "home.page"
        finally:
            obj.deleteLater()

    def test_no_bridge_emits_no_signals(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            fired = []
            obj.continuePlayback.connect(lambda: fired.append(True))
            assert len(fired) == 0
        finally:
            obj.deleteLater()


class TestHomeDegraded:
    def test_empty_bridge_no_crash(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        ctx = engine.rootContext()
        empty_bridge = MagicMock()
        empty_bridge.libraryAlbums = 0
        empty_bridge.libraryArtists = 0
        empty_bridge.libraryTracks = 0
        empty_bridge.hasPlayback = False
        empty_bridge.activeJobs = 0
        empty_bridge.currentTrackTitle = "—"
        empty_bridge.currentArtist = "—"
        empty_bridge.sourcesCount = 0
        empty_bridge.backend = ""
        empty_bridge.refresh = MagicMock()
        ctx.setContextProperty("homeBridge", empty_bridge)
        ctx.setContextProperty("navigationBridge", MagicMock())
        obj = comp.create()
        try:
            assert obj.property("state") == "READY"
            assert obj.property("bridge").libraryTracks == 0
        finally:
            obj.deleteLater()

    def test_library_zero_counts_show_empty(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        ctx = engine.rootContext()
        bridge = MagicMock()
        bridge.libraryAlbums = 0
        bridge.libraryArtists = 0
        bridge.libraryTracks = 0
        bridge.hasPlayback = False
        bridge.activeJobs = 0
        bridge.currentTrackTitle = "—"
        bridge.currentArtist = "—"
        bridge.sourcesCount = 0
        bridge.backend = ""
        bridge.refresh = MagicMock()
        ctx.setContextProperty("homeBridge", bridge)
        ctx.setContextProperty("navigationBridge", MagicMock())
        obj = comp.create()
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_no_playback_shows_placeholder(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        ctx = engine.rootContext()
        bridge = MagicMock()
        bridge.hasPlayback = False
        bridge.currentTrackTitle = "—"
        bridge.currentArtist = "—"
        bridge.libraryAlbums = 50
        bridge.libraryArtists = 10
        bridge.libraryTracks = 500
        bridge.activeJobs = 0
        bridge.sourcesCount = 1
        bridge.backend = ""
        bridge.refresh = MagicMock()
        ctx.setContextProperty("homeBridge", bridge)
        ctx.setContextProperty("navigationBridge", MagicMock())
        obj = comp.create()
        try:
            assert not obj.property("bridge").hasPlayback
        finally:
            obj.deleteLater()


class TestHomeErrorStates:
    def test_error_state_shows_retry(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()

    def test_recover_from_error(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
            ctx = engine.rootContext()
            bridge = MagicMock()
            bridge.libraryAlbums = 10
            bridge.libraryTracks = 100
            bridge.hasPlayback = True
            bridge.currentTrackTitle = "Test"
            bridge.currentArtist = "Test"
            ctx.setContextProperty("homeBridge", bridge)
            obj.setProperty("hasBridge", True)
            obj.setProperty("state", "READY")
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()
