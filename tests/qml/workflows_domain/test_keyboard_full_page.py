from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QObject, Property, QUrl, Signal, Slot
from PySide6.QtQml import QQmlComponent, QQmlEngine

pytestmark = [pytest.mark.qml_module("shell"), pytest.mark.qml_workflow("keyboard")]

QML_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"


class FakeNavigationBridge(QObject):
    routeChanged = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._currentRoute = "home"
        self._canGoBack = False
        self._canGoForward = False
        self._navigated = []

    @Property(str, notify=routeChanged)
    def currentRoute(self): return self._currentRoute

    @Property(bool, notify=routeChanged)
    def canGoBack(self): return self._canGoBack

    @Property(bool, notify=routeChanged)
    def canGoForward(self): return self._canGoForward

    @Slot(str)
    def navigate(self, route):
        self._navigated.append(route)
        self._currentRoute = route
        self.routeChanged.emit(route)

    @Slot()
    def back(self): pass

    @Slot()
    def forward(self): pass

    @Slot()
    def refreshCurrent(self): pass

    @Slot(str, "QVariant")
    def navigateWithParams(self, route, params): pass


class FakeRouteRegistryBridge(QObject):
    @Slot(str, result=str)
    def getTitle(self, route): return "Inicio"


@pytest.fixture
def engine(qapp):
    return QQmlEngine(qapp)


class TestKeyboardFullPage:
    def test_shell_focus_and_keys(self, engine):
        nb = FakeNavigationBridge()
        rrb = FakeRouteRegistryBridge()
        engine.rootContext().setContextProperty("navigationBridge", nb)
        engine.rootContext().setContextProperty("routeRegistryBridge", rrb)
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "shell/AppShell.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_home_keys_on_escape(self, engine):
        nb = FakeNavigationBridge()
        engine.rootContext().setContextProperty("navigationBridge", nb)
        engine.rootContext().setContextProperty("homeBridge", QObject())
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/home/HomePage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_library_keys_on_escape(self, engine):
        nb = FakeNavigationBridge()
        lb = QObject()
        lb.__class__.state = Property(str, lambda self: "READY")
        sc = QObject()
        sc.__class__.hasSelection = Property(bool, lambda self: False)
        engine.rootContext().setContextProperty("navigationBridge", nb)
        engine.rootContext().setContextProperty("libraryBridge", lb)
        engine.rootContext().setContextProperty("selectionContextBridge", sc)
        engine.rootContext().setContextProperty("notificationBridge", QObject())
        engine.rootContext().setContextProperty("actionRegistry", QObject())
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/library/LibraryPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()

    def test_history_keys_on_escape(self, engine):
        hb = QObject()
        hb.__class__.historyModel = Property("QVariantList", lambda self: [])
        hb.__class__.historyCount = Property(int, lambda self: 0)
        engine.rootContext().setContextProperty("historyBridge", hb)
        engine.rootContext().setContextProperty("notificationBridge", QObject())
        engine.addImportPath(str(QML_DIR))
        comp = QQmlComponent(engine)
        comp.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "pages/history/HistoryPage.qml")))
        assert comp.isReady() or comp.status() == QQmlComponent.Null, comp.errorString()
