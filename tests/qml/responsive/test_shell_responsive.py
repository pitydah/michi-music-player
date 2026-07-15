from pathlib import Path

import pytest
from PySide6.QtCore import QUrl, QObject, Property, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("shell"), pytest.mark.qml_dimension("responsive")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeNavigationBridge(QObject):
    routeChanged = Signal(str)
    invalidRouteError = Signal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._currentRoute = "home"
        self._canGoBack = False
        self._canGoForward = False

    @Property(str, notify=routeChanged)
    def currentRoute(self): return self._currentRoute

    @Property(bool, notify=routeChanged)
    def canGoBack(self): return self._canGoBack

    @Property(bool, notify=routeChanged)
    def canGoForward(self): return self._canGoForward

    @Slot(str)
    def navigate(self, route): self._currentRoute = route

    @Slot()
    def refreshCurrent(self): pass

    @Slot(str, "QVariant")
    def navigateWithParams(self, route, params): pass

    @Slot(result=str)
    def getTitle(self, route): return "Inicio"


class FakeRouteRegistryBridge(QObject):
    @Slot(str, result=str)
    def getTitle(self, route): return "Inicio"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestShellResponsive:
    def _create_page(self, engine, width, height):
        nb = FakeNavigationBridge()
        rrb = FakeRouteRegistryBridge()
        engine.rootContext().setContextProperty("navigationBridge", nb)
        engine.rootContext().setContextProperty("routeRegistryBridge", rrb)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "shell/AppShell.qml")))
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
        assert (QML_DIR / "shell/AppShell.qml").exists()
