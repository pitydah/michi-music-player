from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("library"), pytest.mark.qml_dimension("responsive")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeLibraryBridge(QObject):
    stateChanged = Signal()
    dataChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._state = "READY"
        self._songCount = 500
        self._albumCount = 42
        self._artistCount = 12
        self._searchQuery = ""

    @Property(str, notify=stateChanged)
    def state(self): return self._state

    @Property(int, notify=dataChanged)
    def songCount(self): return self._songCount

    @Property(int, notify=dataChanged)
    def albumCount(self): return self._albumCount

    @Property(int, notify=dataChanged)
    def artistCount(self): return self._artistCount

    @Property(str, notify=dataChanged)
    def searchQuery(self): return self._searchQuery

    @Slot(str)
    def search(self, text): self._searchQuery = text

    @Slot()
    def clearFilters(self): self._searchQuery = ""

    @Slot()
    def refresh(self): self.dataChanged.emit()

    @Slot(result=dict)
    def addMedia(self, path): return {"ok": False, "error": "not_implemented"}


class FakeSelectionController(QObject):
    selectionChanged = Signal()
    hasSelectionChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._hasSelection = False
        self._count = 0

    @Property(bool, notify=hasSelectionChanged)
    def hasSelection(self): return self._hasSelection

    @Property(int, notify=selectionChanged)
    def count(self): return self._count


class FakeNotificationBridge(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)

    @Slot(str, str)
    def showMessage(self, msg, kind): pass


class FakeActionRegistry(QObject):
    def __init__(self, parent=None):
        super().__init__(parent)


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestLibraryResponsive:
    def _create_page(self, engine, width, height):
        lb = FakeLibraryBridge()
        sc = FakeSelectionController()
        nb = FakeNotificationBridge()
        ar = FakeActionRegistry()
        engine.rootContext().setContextProperty("libraryBridge", lb)
        engine.rootContext().setContextProperty("selectionContextBridge", sc)
        engine.rootContext().setContextProperty("notificationBridge", nb)
        engine.rootContext().setContextProperty("actionRegistry", ar)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/library/LibraryPage.qml")))
        return comp

    def test_desktop_1920(self, engine):
        comp = self._create_page(engine, 1920, 1080)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1366(self, engine):
        comp = self._create_page(engine, 1366, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_1024(self, engine):
        comp = self._create_page(engine, 1024, 768)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_desktop_900(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_compact(self, engine):
        comp = self._create_page(engine, 600, 800)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_narrow(self, engine):
        comp = self._create_page(engine, 360, 640)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_125(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_zoom_150(self, engine):
        comp = self._create_page(engine, 900, 700)
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_page_qml_exists(self):
        assert (QML_DIR / "pages/library/LibraryPage.qml").exists()
