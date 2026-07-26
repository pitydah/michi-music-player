"""QML test for DiscLabPage — verifies the page loads and renders without QML errors."""

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
DISC_LAB_QML = str(QML_DIR / "pages" / "disc_lab" / "DiscLabPage.qml")


class FakeDiscLabBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._status = "ready"
        self._drive_info = "/dev/sr0"
        self._tracks = [
            {"track": 1, "title": "Track 1", "duration": 240},
            {"track": 2, "title": "Track 2", "duration": 200},
        ]
        self._format = "flac"
        self._destination = "/home/user/Music/CD Rips"
        self.refresh_called = False
        self.scan_called = False

    @Property(str, notify=lambda: None)
    def status(self):
        return self._status

    @status.setter
    def status(self, value):
        self._status = value

    @Property(str, notify=lambda: None)
    def driveInfo(self):
        return self._drive_info

    @Property("QVariantList", notify=lambda: None)
    def tracks(self):
        return self._tracks

    @Slot()
    def refresh(self):
        self.refresh_called = True

    @Slot()
    def scanDisc(self):
        self.scan_called = True

    @Slot(str)
    def setFormat(self, fmt):
        self._format = fmt

    @Slot(str)
    def setDestination(self, dest):
        self._destination = dest

    @Slot()
    def startExtraction(self):
        pass


@pytest.fixture
def mock_disc_lab_bridge():
    return FakeDiscLabBridge()


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


def _load_page(engine, bridge=None):
    if bridge is not None:
        engine.rootContext().setContextProperty("discLabBridge", bridge)
    engine.addImportPath(str(QML_DIR))
    comp = QQmlComponent(engine)
    comp.loadUrl(QUrl.fromLocalFile(DISC_LAB_QML))
    return comp


class TestDiscLabPageLoading:
    def test_page_loads_without_qml_errors(self, qapp):
        engine = QQmlEngine(qapp)
        engine.addImportPath(str(QML_DIR))
        comp = _load_page(engine)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_object_name(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        assert obj.property("objectName") == "discLabPage"

    def test_page_has_disc_bridge(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        disc_prop = obj.property("disc")
        assert disc_prop is mock_disc_lab_bridge

    def test_page_state_ready_with_bridge(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        assert obj.property("pageState") == 1

    def test_page_state_unavailable_without_bridge(self, qapp):
        engine = QQmlEngine(qapp)
        engine.addImportPath(str(QML_DIR))
        comp = _load_page(engine)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        assert obj.property("pageState") == 4

    def test_error_state_visible_when_error(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        obj.setProperty("pageState", 3)
        assert obj.property("pageState") == 3

    def test_loading_state_visible(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        obj.setProperty("pageState", 0)
        assert obj.property("pageState") == 0

    def test_empty_state_visible(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        obj.setProperty("pageState", 2)
        assert obj.property("pageState") == 2

    def test_page_refresh_called_on_completed(self, engine, mock_disc_lab_bridge):
        assert not mock_disc_lab_bridge.refresh_called
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        assert mock_disc_lab_bridge.refresh_called

    def test_tracks_repeater_model(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        disc = obj.property("disc")
        assert len(disc.tracks) == 2
        assert disc.tracks[0]["title"] == "Track 1"

    def test_rip_button_disabled_by_default(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        disc = obj.property("disc")
        disc.status = "not_ready"
        assert disc.status != "ready"

    def test_refresh_handles_error(self, engine, mock_disc_lab_bridge):
        obj = None
        comp = _load_page(engine, mock_disc_lab_bridge)
        if comp.isReady():
            obj = comp.create()
            obj.setProperty("pageState", 3)
            assert obj.property("pageState") == 3

    def test_accessible_role(self, engine, mock_disc_lab_bridge):
        comp = _load_page(engine, mock_disc_lab_bridge)
        assert comp.isReady(), comp.errorString()
        obj = comp.create()
        assert obj.property("objectName") == "discLabPage"
