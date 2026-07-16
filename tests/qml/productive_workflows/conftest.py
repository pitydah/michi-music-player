"""E2E productive workflows harness — real QGuiApplication + QQmlApplicationEngine + Main.qml.

Loads Main.qml with all productive bridges registered as context properties.
Provides helpers for QML item lookup and interaction.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow

from core.application_bootstrap import ApplicationBootstrap


def find_qml_item(root: QQuickItem, object_name: str) -> QQuickItem | None:
    """Recursively find a QQuickItem by objectName."""
    if root.objectName() == object_name:
        return root
    for child in root.childItems():
        result = find_qml_item(child, object_name)
        if result is not None:
            return result
    return None


def find_qml_items(root: QQuickItem, object_name: str) -> list[QQuickItem]:
    """Recursively find all QQuickItems matching objectName."""
    results: list[QQuickItem] = []
    if root.objectName() == object_name:
        results.append(root)
    for child in root.childItems():
        results.extend(find_qml_items(child, object_name))
    return results


def qml_item_type_names(item: QQuickItem, depth: int = 0) -> list[str]:
    """Debug helper: list all child types recursively."""
    lines: list[str] = []
    indent = "  " * depth
    lines.append(f"{indent}{item.objectName()} ({type(item).__name__})")
    for child in item.childItems():
        lines.extend(qml_item_type_names(child, depth + 1))
    return lines


_QML_APP: QGuiApplication | None = None


def ensure_qapp() -> QGuiApplication:
    global _QML_APP
    if _QML_APP is None:
        _QML_APP = QGuiApplication.instance() or QGuiApplication([])
    return _QML_APP


@pytest.fixture(scope="session")
def qml_app():
    app = ensure_qapp()
    yield app


@pytest.fixture(scope="session")
def bootstrap():
    bs = ApplicationBootstrap()
    bs.build()
    bs.start()
    from ui_qml_bridge.bridge_factory import BridgeFactory
    factory = BridgeFactory(bs.container)
    bs._bridges = factory.create_all()
    return bs


@pytest.fixture(scope="session")
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
    main_qml = str(Path(__file__).resolve().parent.parent.parent.parent / "ui_qml" / "Main.qml")
    engine.load(QUrl.fromLocalFile(main_qml))
    if not engine.rootObjects():
        raise RuntimeError("Failed to load Main.qml — no root objects")
    yield engine
    engine.deleteLater()


@pytest.fixture(scope="session")
def root_window(engine) -> QQuickWindow:
    root = engine.rootObjects()[0]
    assert isinstance(root, QQuickWindow), f"Root object is {type(root)}, expected QQuickWindow"
    root.show()
    from PySide6.QtTest import QTest
    QTest.qWaitForWindowExposed(root)
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
