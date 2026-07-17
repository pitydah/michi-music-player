"""E2E productive workflows harness — real QGuiApplication + QQmlApplicationEngine + Main.qml.

Loads Main.qml with all productive bridges registered as context properties.
Provides helpers for QML item lookup and QTest interaction.
Safe to run in QT_QPA_PLATFORM=offscreen.
"""
from __future__ import annotations

import os
import time as _time
from pathlib import Path
from typing import Any, Callable

import pytest
from PySide6.QtCore import QUrl, Qt
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow

from core.application_bootstrap import ApplicationBootstrap


def find_qml_item(root: QQuickItem, object_name: str) -> QQuickItem | None:
    if root.objectName() == object_name:
        return root
    for child in root.childItems():
        result = find_qml_item(child, object_name)
        if result is not None:
            return result
    return None


def find_qml_items(root: QQuickItem, object_name: str) -> list[QQuickItem]:
    results: list[QQuickItem] = []
    if root.objectName() == object_name:
        results.append(root)
    for child in root.childItems():
        results.extend(find_qml_items(child, object_name))
    return results


def wait_for_condition(condition_fn: Callable[[], bool], timeout_ms: int = 1000) -> bool:
    from PySide6.QtTest import QTest
    deadline = _time.monotonic() + timeout_ms / 1000.0
    while _time.monotonic() < deadline:
        if condition_fn():
            return True
        QTest.qWait(10)
    return False


def wait_for_property(item: QQuickItem, property_name: str, expected_value: Any, timeout_ms: int = 1000) -> bool:
    return wait_for_condition(lambda: item.property(property_name) == expected_value, timeout_ms)


def qml_item_type_names(item: QQuickItem, depth: int = 0) -> list[str]:
    lines: list[str] = []
    indent = "  " * depth
    lines.append(f"{indent}{item.objectName()} ({type(item).__name__})")
    for child in item.childItems():
        lines.extend(qml_item_type_names(child, depth + 1))
    return lines


def qtest_click_item(item: QQuickItem, window: QQuickWindow | None = None,
                     button: Qt.MouseButton = Qt.LeftButton) -> None:
    from PySide6.QtCore import QPoint, QPointF
    from PySide6.QtTest import QTest
    center = item.mapToScene(QPointF(item.width() / 2.0, item.height() / 2.0))
    target = QPoint(round(center.x()), round(center.y()))
    QTest.mouseClick(window or item, button, Qt.NoModifier, target)
    QTest.qWait(50)


def qtest_key_click(item: QQuickItem, key: Qt.Key) -> None:
    from PySide6.QtTest import QTest
    item.forceActiveFocus()
    QTest.keyClick(item, key)
    QTest.qWait(50)


def qtest_type_text(item: QQuickItem, text: str) -> None:
    from PySide6.QtTest import QTest
    item.forceActiveFocus()
    QTest.keyClicks(item, text)
    QTest.qWait(50)


_QT_QPA_ORIGINAL = os.environ.get("QT_QPA_PLATFORM", "")


def ensure_engine_platform() -> None:
    if "offscreen" in _QT_QPA_ORIGINAL:
        os.environ["QT_QPA_PLATFORM"] = "offscreen"


ensure_engine_platform()

_QML_APP: QGuiApplication | None = None


def ensure_qapp() -> QGuiApplication:
    global _QML_APP
    if _QML_APP is None:
        _QML_APP = QGuiApplication.instance() or QGuiApplication([])
    return _QML_APP


@pytest.fixture(scope="session")
def qml_app():
    yield ensure_qapp()


@pytest.fixture(scope="session")
def bootstrap():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()
    from ui_qml_bridge.bridge_factory import BridgeFactory
    factory = BridgeFactory(bs.container)
    bs._bridges = factory.create_all()
    nav = bs._bridges.get("navigation")
    if nav is not None:
        from ui_qml_bridge.route_registry import CAPABILITY_MAP
        nav.set_capabilities(set(CAPABILITY_MAP.values()))
    return bs


@pytest.fixture(scope="module")
def engine(bootstrap):
    engine = QQmlApplicationEngine()
    from ui_qml_bridge.context_registrar import ContextRegistrar
    from ui_qml_bridge.context_bindings import QML_CONTEXT_BINDINGS
    registrar = ContextRegistrar(engine)
    for qml_name, bridge_key in QML_CONTEXT_BINDINGS.items():
        bridge = bootstrap._bridges.get(bridge_key)
        if bridge is not None:
            registrar.register(qml_name, bridge)
    engine.addImportPath("ui_qml")
    main_qml = str(Path("ui_qml/Main.qml").resolve())
    engine.load(QUrl.fromLocalFile(main_qml))
    if not engine.rootObjects():
        raise RuntimeError("Failed to load Main.qml — no root objects")
    yield engine
    engine.deleteLater()


@pytest.fixture(scope="module")
def root_window(engine) -> QQuickWindow:
    roots = engine.rootObjects()
    assert roots, "Main.qml did not load — no root objects"
    root = roots[0]
    assert isinstance(root, QQuickWindow), f"Root object is {type(root)}, expected QQuickWindow"
    assert isinstance(root, QQuickWindow)
    return root


@pytest.fixture(scope="session")
def nav(bootstrap):
    return bootstrap._bridges.get("navigation")


@pytest.fixture(scope="session")
def library_bridge(bootstrap):
    return bootstrap._bridges.get("library")


@pytest.fixture(scope="session")
def playback_bridge(bootstrap):
    return bootstrap._bridges.get("playback")


@pytest.fixture(scope="session")
def global_search_bridge(bootstrap):
    return bootstrap._bridges.get("global_search")


@pytest.fixture(scope="session")
def queue_bridge(bootstrap):
    return bootstrap._bridges.get("queue")


@pytest.fixture(scope="session")
def action_registry(bootstrap):
    return bootstrap.container.get("action_registry")


@pytest.fixture(scope="session")
def all_bridges(bootstrap) -> dict[str, Any]:
    return dict(bootstrap._bridges)


@pytest.fixture(scope="session")
def bridges(bootstrap) -> dict[str, Any]:
    return bootstrap._bridges
