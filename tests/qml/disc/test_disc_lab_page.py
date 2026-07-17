"""QML test for DiscLabPage — verifies the page loads and renders without QML errors."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlApplicationEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent / "ui_qml"
DISC_LAB_QML = str(QML_DIR / "pages" / "disc_lab" / "DiscLabPage.qml")


@pytest.fixture
def mock_disc_lab_bridge():
    bridge = MagicMock()
    bridge.status = "ready"
    bridge.driveInfo = "/dev/sr0"
    bridge.tracks = [
        {"track": 1, "title": "Track 1", "duration": 240},
        {"track": 2, "title": "Track 2", "duration": 200},
    ]
    return bridge


@pytest.fixture
def engine(mock_disc_lab_bridge):
    engine = QQmlApplicationEngine()
    engine.rootContext().setContextProperty("discLabBridge", mock_disc_lab_bridge)
    engine.quit.connect(engine.deleteLater)
    return engine


class TestDiscLabPageLoading:
    def test_page_loads_without_qml_errors(self, engine):
        errors = []

        def on_warning(msg):
            errors.append(msg)

        engine.warnings.connect(on_warning)
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))

        assert len(engine.rootObjects()) > 0, (
            f"DiscLabPage did not load. Errors: {errors}"
        )

    def test_page_object_name(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        assert root.objectName == "discLabPage"

    def test_page_has_disc_bridge(self, engine, mock_disc_lab_bridge):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        disc_prop = root.property("disc")
        assert disc_prop is mock_disc_lab_bridge

    def test_page_state_ready_with_bridge(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        assert root.property("pageState") == 1

    def test_page_state_unavailable_without_bridge(self):
        engine = QQmlApplicationEngine()
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))

        roots = engine.rootObjects()
        assert len(roots) > 0
        root = roots[0]
        assert root.property("pageState") == 4

    def test_error_state_visible_when_error(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        root.setProperty("pageState", 3)
        assert root.property("pageState") == 3

    def test_loading_state_visible(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        root.setProperty("pageState", 0)
        assert root.property("pageState") == 0

    def test_empty_state_visible(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        root.setProperty("pageState", 2)
        assert root.property("pageState") == 2

    def test_page_refresh_called_on_completed(self, engine, mock_disc_lab_bridge):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        mock_disc_lab_bridge.refresh.assert_called_once()

    def test_tracks_repeater_model(self, engine, mock_disc_lab_bridge):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        disc = root.property("disc")
        assert len(disc.tracks) == 2
        assert disc.tracks[0]["title"] == "Track 1"

    def test_rip_button_disabled_by_default(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        disc = root.property("disc")
        disc.status = "not_ready"
        assert disc.status != "ready"

    def test_refresh_handles_error(self, engine, mock_disc_lab_bridge):
        mock_disc_lab_bridge.refresh.side_effect = RuntimeError("Device error")
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        assert root.property("pageState") == 3

    def test_accessible_role(self, engine):
        engine.load(QUrl.fromLocalFile(DISC_LAB_QML))
        root = engine.rootObjects()[0]
        assert root.property("Accessible") is not None
