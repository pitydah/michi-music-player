from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QObject, QUrl
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem

from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge

from .qml_component_helper import QML_ROOT

REPO = Path(__file__).resolve().parents[3]


def _component(engine: QQmlEngine, relative_path: str) -> QQmlComponent:
    component = QQmlComponent(engine)
    component.loadUrl(QUrl.fromLocalFile(str(QML_ROOT / relative_path)))
    return component


def _find_visual_item(root: QQuickItem, object_name: str) -> QQuickItem | None:
    if root.objectName() == object_name:
        return root
    for child in root.childItems():
        found = _find_visual_item(child, object_name)
        if found is not None:
            return found
    return None


def _find_children_by_property(
    root: QQuickItem, prop_name: str, prop_value
) -> list[QQuickItem]:
    results = []
    if root.property(prop_name) == prop_value:
        results.append(root)
    for child in root.childItems():
        results.extend(_find_children_by_property(child, prop_name, prop_value))
    return results


def _find_buttons_with_text(root: QQuickItem, text: str) -> list[QQuickItem]:
    buttons = _find_children_by_property(root, "text", text)
    if not buttons:
        for child in root.childItems():
            txt = child.property("text")
            if isinstance(txt, str) and text in txt:
                buttons.append(child)
            buttons.extend(_find_buttons_with_text(child, text))
    return buttons


def test_page_stack_has_error_overlay(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)

    component = _component(engine, "shell/PageStack.qml")
    assert component.isReady(), component.errorString()

    stack = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert stack is not None, component.errorString()

    assert stack.property("lastError") == ""
    assert stack.property("lastLoadedRoute") == ""
    assert hasattr(stack, "property"), "stack is not a QObject"

    qapp.processEvents()

    stack.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


def test_app_shell_error_overlay_retry_button_found(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)

    component = _component(engine, "shell/AppShell.qml")
    assert component.isReady(), component.errorString()

    shell = component.createWithInitialProperties({"width": 1200, "height": 800})
    assert shell is not None, component.errorString()

    qapp.processEvents()

    retry_buttons = _find_buttons_with_text(shell, "Reintentar")
    assert len(retry_buttons) >= 1, (
        "AppShell.qml errorOverlay must have a 'Reintentar' (Retry) button"
    )

    shell.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


def test_app_shell_error_overlay_go_home_found(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)

    component = _component(engine, "shell/AppShell.qml")
    assert component.isReady(), component.errorString()

    shell = component.createWithInitialProperties({"width": 1200, "height": 800})
    assert shell is not None, component.errorString()

    qapp.processEvents()

    home_buttons = _find_buttons_with_text(shell, "Ir a Inicio")
    assert len(home_buttons) >= 1, (
        "AppShell.qml errorOverlay must have a 'Ir a Inicio' (Go Home) button"
    )

    shell.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


def test_app_shell_has_error_state_overlay(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)

    component = _component(engine, "shell/AppShell.qml")
    assert component.isReady(), component.errorString()

    shell = component.createWithInitialProperties({"width": 1200, "height": 800})
    assert shell is not None, component.errorString()

    qapp.processEvents()

    error_overlay = shell.findChild(QObject, "fatalOverlay")
    assert error_overlay is not None, (
        "AppShell.qml must have a 'fatalOverlay' ErrorState (line 287-296)"
    )

    shell.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


def test_app_shell_fatal_overlay_has_show_retry(qapp) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)

    component = _component(engine, "shell/AppShell.qml")
    assert component.isReady(), component.errorString()

    shell = component.createWithInitialProperties({"width": 1200, "height": 800})
    assert shell is not None, component.errorString()

    qapp.processEvents()

    fatal_overlay = shell.findChild(QObject, "fatalOverlay")
    assert fatal_overlay is not None, "fatalOverlay not found"

    assert fatal_overlay.property("showRetry"), (
        "fatalOverlay must have showRetry=True (line 283)"
    )

    shell.deleteLater()
    registry.deleteLater()
    engine.deleteLater()
