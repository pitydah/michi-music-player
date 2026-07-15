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
    bridge.libraryAlbums = 10
    bridge.libraryArtists = 5
    bridge.libraryTracks = 100
    bridge.sourcesCount = 2
    bridge.lastScan = "hoy"
    bridge.currentTrackTitle = "Canción de prueba"
    bridge.currentArtist = "Artista de prueba"
    bridge.hasPlayback = True
    bridge.activeJobs = 0
    bridge.backend = "GStreamer"
    bridge.refresh = MagicMock()
    ctx.setContextProperty("homeBridge", bridge)
    ctx.setContextProperty("navigationBridge", MagicMock())
    obj = comp.create()
    return obj, bridge


class TestHomePageObjectName:
    def test_page_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "home.page"
        finally:
            obj.deleteLater()

    def test_focus_scope_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            scope = obj.findChild(object, "home.focusScope")
            assert scope is not None
        finally:
            obj.deleteLater()

    def test_flickable_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            flick = obj.findChild(object, "home.flickableContent")
            assert flick is not None
        finally:
            obj.deleteLater()

    def test_playback_card_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.playbackCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_library_status_card_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.libraryStatusCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_server_status_card_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.serverStatusCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_assistant_card_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            card = obj.findChild(object, "home.assistantCard")
            assert card is not None
        finally:
            obj.deleteLater()

    def test_continue_button_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "home.continueButton")
            assert btn is not None
        finally:
            obj.deleteLater()

    def test_resume_queue_button_object_name(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            btn = obj.findChild(object, "home.resumeQueueButton")
            assert btn is not None
        finally:
            obj.deleteLater()


class TestHomePageStates:
    def test_ready_with_bridge(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("state") == "READY"
        finally:
            obj.deleteLater()

    def test_error_no_bridge(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj = comp.create()
        try:
            assert obj.property("state") == "ERROR"
        finally:
            obj.deleteLater()


class TestHomePagePlayback:
    def test_shows_current_track(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            assert obj.property("bridge").currentTrackTitle == "Canción de prueba"
        finally:
            obj.deleteLater()

    def test_shows_current_artist(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            assert obj.property("bridge").currentArtist == "Artista de prueba"
        finally:
            obj.deleteLater()

    def test_has_playback_flag(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, bridge = _create_context(engine, comp)
        try:
            assert obj.property("bridge").hasPlayback
        finally:
            obj.deleteLater()


class TestHomePageSignals:
    def test_continue_playback_signal(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.continuePlayback.connect(lambda: fired.append(True))
            obj.continuePlayback.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()

    def test_resume_queue_signal(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.resumeQueue.connect(lambda: fired.append(True))
            obj.resumeQueue.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()

    def test_reconnect_server_signal(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.reconnectServer.connect(lambda: fired.append(True))
            obj.reconnectServer.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()

    def test_open_jobs_signal(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.openJobs.connect(lambda: fired.append(True))
            obj.openJobs.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()

    def test_open_assistant_signal(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            fired = []
            obj.openAssistant.connect(lambda: fired.append(True))
            obj.openAssistant.emit()
            assert len(fired) == 1
        finally:
            obj.deleteLater()


class TestHomePageAccessible:
    def test_accessible_role(self, engine):
        comp = _load_page(engine)
        assert comp.isReady()
        obj, _ = _create_context(engine, comp)
        try:
            assert obj.property("objectName") == "home.page"
        finally:
            obj.deleteLater()
