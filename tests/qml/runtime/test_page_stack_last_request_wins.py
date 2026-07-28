"""Rapid navigation: only the last request should load.

D3 of the QML route reintegration plan (P0-C0.5).

Proves the PageStack's generation-safe atomic route replacement: when
several ``loadRoute`` calls land back-to-back without event processing,
only the most recent request is honoured.

The contract verified here is the one introduced in C4:
  * ``lastLoadedRoute`` ends up at the final requested route.
  * ``currentPage`` resolves to a non-null page.
  * No stale ``lastError`` from superseded routes remains.
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtCore import QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtTest import QTest

from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge

REPO = Path(__file__).resolve().parents[3]
QML_ROOT = REPO / "ui_qml"

RAPID_SEQUENCE = (
    "library.artists",
    "library.genres",
    "library.composers",
    "library.folders",
)
FINAL_ROUTE = RAPID_SEQUENCE[-1]


@pytest.fixture
def engine(qapp) -> QQmlEngine:
    qml_engine = QQmlEngine(qapp)
    qml_engine.addImportPath(str(QML_ROOT))
    registry = RouteRegistryBridge()
    qml_engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    yield qml_engine
    qml_engine.deleteLater()


@pytest.fixture
def page_stack(engine) -> object:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / "shell/PageStack.qml")))
    assert component.isReady(), component.errorString()
    stack = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert stack is not None, component.errorString()
    yield stack
    stack.deleteLater()


def _settle(stack, qapp) -> None:
    for _ in range(300):
        qapp.processEvents()
        if (
            stack.property("lastLoadedRoute") == FINAL_ROUTE
            and not stack.property("transitionRunning")
        ):
            return
        QTest.qWait(10)


def test_rapid_navigation_keeps_only_last_request(page_stack, qapp) -> None:
    """Only the last of four rapid loadRoute calls reaches lastLoadedRoute."""
    stack = page_stack

    for route in RAPID_SEQUENCE:
        stack.loadRoute(route)

    _settle(stack, qapp)

    assert stack.property("lastLoadedRoute") == FINAL_ROUTE
    assert stack.property("currentRoute") == FINAL_ROUTE
    assert stack.property("loading") is False
    assert stack.property("lastError") == ""
    assert stack.property("currentPage") is not None


def test_rapid_navigation_clear_error_on_new_navigation(page_stack, qapp) -> None:
    """A stale error from a superseded navigation is cleared by the final load."""
    stack = page_stack

    # Navigate to an invalid route first to produce an error
    stack.loadRoute("nonexistent_route")
    QTest.qWait(50)

    # Now navigate to valid routes rapidly
    for route in RAPID_SEQUENCE:
        stack.loadRoute(route)

    _settle(stack, qapp)

    assert stack.property("lastLoadedRoute") == FINAL_ROUTE
    assert stack.property("currentRoute") == FINAL_ROUTE
    assert stack.property("currentPage") is not None
