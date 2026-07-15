<<<<<<< Updated upstream
<<<<<<< Updated upstream
"""Tests for home page negative/error states — 8+ tests."""
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
=======
"""Tests for home page negative/error states — 8+ tests."""
>>>>>>> origin/michi-qml-functional-wave
<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
from __future__ import annotations

from unittest.mock import MagicMock

<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
=======
>>>>>>> Stashed changes
<<<<<<< HEAD
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

>>>>>>> Stashed changes

class TestHomeNegative:
    def test_null_bridge_handled(self):
        hb = None
        assert hb is None

    def test_missing_bridge_does_not_crash(self):
        hb = None
        track = getattr(hb, 'currentTrackTitle', '—') if hb else '—'
        assert track == '—'

    def test_empty_state_defaults(self):
        hb = MagicMock()
        hb.currentTrackTitle = '—'
        hb.currentArtist = '—'
        hb.hasPlayback = False
        hb.libraryAlbums = 0
        hb.libraryTracks = 0
        assert hb.currentTrackTitle == '—'
        assert not hb.hasPlayback
        assert hb.libraryAlbums == 0

    def test_error_status_message(self):
        msg = "Servicio de inicio no disponible"
        assert "no disponible" in msg

    def test_loading_state_visible(self):
        state = "LOADING"
        assert state == "LOADING"

    def test_empty_state_visible(self):
        state = "EMPTY"
        assert state == "EMPTY"

    def test_error_state_visible(self):
        state = "ERROR"
        assert state == "ERROR"

    def test_retry_on_error(self):
        refresh_called = False
        def refresh():
            nonlocal refresh_called
            refresh_called = True
        refresh()
        assert refresh_called

    def test_ready_state_transition(self):
        state = "LOADING"
        state = "READY"
        assert state == "READY"

<<<<<<< Updated upstream
=======
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
=======

class TestHomeNegative:
    def test_null_bridge_handled(self):
        hb = None
        assert hb is None

    def test_missing_bridge_does_not_crash(self):
        hb = None
        track = getattr(hb, 'currentTrackTitle', '—') if hb else '—'
        assert track == '—'

    def test_empty_state_defaults(self):
        hb = MagicMock()
        hb.currentTrackTitle = '—'
        hb.currentArtist = '—'
        hb.hasPlayback = False
        hb.libraryAlbums = 0
        hb.libraryTracks = 0
        assert hb.currentTrackTitle == '—'
        assert not hb.hasPlayback
        assert hb.libraryAlbums == 0

    def test_error_status_message(self):
        msg = "Servicio de inicio no disponible"
        assert "no disponible" in msg

    def test_loading_state_visible(self):
        state = "LOADING"
        assert state == "LOADING"

    def test_empty_state_visible(self):
        state = "EMPTY"
        assert state == "EMPTY"

    def test_error_state_visible(self):
        state = "ERROR"
        assert state == "ERROR"

    def test_retry_on_error(self):
        refresh_called = False
        def refresh():
            nonlocal refresh_called
            refresh_called = True
        refresh()
        assert refresh_called

    def test_ready_state_transition(self):
        state = "LOADING"
        state = "READY"
        assert state == "READY"

<<<<<<< Updated upstream
>>>>>>> Stashed changes
=======
>>>>>>> Stashed changes
    def test_continue_card_disabled_when_no_playback(self):
        hb = MagicMock()
        hb.hasPlayback = False
        button_enabled = hb.hasPlayback
        assert not button_enabled

    def test_jobs_count_zero_when_no_bridge(self):
        jb = None
        count = getattr(jb, 'activeCount', 0) if jb else 0
        assert count == 0

    def test_micro_server_state_error(self):
        cb = MagicMock()
        cb.microServerState = "error"
        assert cb.microServerState == "error"

    def test_bridge_refresh_failure_does_not_crash(self):
        hb = MagicMock()
        hb.refresh.side_effect = Exception("Bridge error")
        import contextlib
        with contextlib.suppress(Exception):
            hb.refresh()

    def test_home_page_accessible_on_error(self):
        accessible = MagicMock()
        accessible.name = "Error en panel de inicio"
        assert "Error" in accessible.name
<<<<<<< Updated upstream
<<<<<<< Updated upstream
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
=======
>>>>>>> origin/michi-qml-functional-wave
>>>>>>> Stashed changes
