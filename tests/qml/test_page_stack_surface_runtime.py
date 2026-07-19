from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge


QML_ROOT = Path(__file__).resolve().parents[2] / "ui_qml"


def test_page_stack_loads_route_inside_canonical_surface(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "shell/PageStack.qml")))
    assert component.isReady(), component.errorString()
    stack = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert stack is not None, component.errorString()

    stack.loadRoute("home")
    for _ in range(100):
        qapp.processEvents()
        if stack.property("lastLoadedRoute") == "home":
            break
        QTest.qWait(10)

    container = stack.findChild(QObject, "pageStackContainer")
    surface = stack.findChild(QObject, "pageSurface")
    content = stack.findChild(QObject, "pageContentViewport")
    assert stack.property("lastLoadedRoute") == "home"
    assert stack.property("loadedObjectName") == "homePage"
    assert container is not None
    assert surface is not None
    assert content is not None
    assert surface.width() < stack.width()
    assert surface.height() < stack.height()

    stack.deleteLater()
    registry.deleteLater()
    engine.deleteLater()
