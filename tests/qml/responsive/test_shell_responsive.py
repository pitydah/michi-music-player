from __future__ import annotations

from pathlib import Path

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem
from PySide6.QtTest import QTest

from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge


pytestmark = [pytest.mark.qml_module("shell"), pytest.mark.qml_dimension("responsive")]
QML_DIR = Path(__file__).resolve().parents[3] / "ui_qml"


def _item(root: QQuickItem, name: str) -> QQuickItem:
    item = root.findChild(QQuickItem, name)
    assert item is not None, f"Missing QML item: {name}"
    return item


@pytest.mark.parametrize(
    ("width", "height"),
    (
        (800, 640),
        (1024, 768),
        (1366, 768),
        (1600, 900),
        (1920, 1080),
        (2560, 1440),
        (3840, 2160),
    ),
)
def test_shell_runtime_geometry(qapp, width: int, height: int) -> None:
    engine = QQmlEngine()
    navigation = NavigationBridge(parent=engine)
    registry = RouteRegistryBridge(parent=engine)
    engine.rootContext().setContextProperty("navigationBridge", navigation)
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "shell/AppShell.qml")))
    assert component.isReady(), component.errorString()
    shell = component.createWithInitialProperties({"width": width, "height": height})
    assert shell is not None, component.errorString()
    QTest.qWait(80)
    qapp.processEvents()

    sidebar = _item(shell, "sidebar")
    header = _item(shell, "headerBar")
    stack = _item(shell, "pageStack")
    surface = _item(shell, "pageSurface")
    now_playing = _item(shell, "nowPlayingBar")

    expected_sidebar = 70 if width < 1024 else 244
    assert round(sidebar.width()) == expected_sidebar
    assert round(sidebar.width() + header.width()) == width
    assert round(header.height()) == 56
    expected_now_playing = 132 if width >= 1200 else 122 if width >= 800 else 108
    assert round(now_playing.height()) == expected_now_playing
    assert round(header.height() + stack.height() + now_playing.height()) == height
    assert surface.width() <= stack.width()
    assert surface.height() <= stack.height()
    assert header.y() == 0
    assert stack.y() >= header.height()
    assert now_playing.y() >= stack.y() + stack.height()

    shell.deleteLater()
    engine.deleteLater()


def test_page_qml_exists() -> None:
    assert (QML_DIR / "shell/AppShell.qml").exists()


def test_header_search_navigates_once_and_updates_route_params(qapp) -> None:
    engine = QQmlEngine()
    navigation = NavigationBridge(parent=engine)
    registry = RouteRegistryBridge(parent=engine)
    engine.rootContext().setContextProperty("navigationBridge", navigation)
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_DIR / "shell/AppShell.qml")))
    assert component.isReady(), component.errorString()
    shell = component.createWithInitialProperties({"width": 1200, "height": 760})
    assert shell is not None, component.errorString()

    header = _item(shell, "headerBar")
    header.searchRequested.emit("michi", True)
    qapp.processEvents()
    history_size = len(navigation._back_stack)

    assert navigation.currentRoute == "search"
    assert navigation.currentParams == {"query": "michi", "submitted": True}

    header.searchRequested.emit("music", False)
    qapp.processEvents()
    assert navigation.currentParams == {"query": "music", "submitted": False}
    assert len(navigation._back_stack) == history_size

    shell.deleteLater()
    engine.deleteLater()
