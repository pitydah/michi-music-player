from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path

import pytest
from PySide6.QtCore import QPoint, Qt, QUrl, qInstallMessageHandler
from PySide6.QtGui import QGuiApplication
from PySide6.QtQml import QQmlComponent, QQmlEngine
from PySide6.QtQuick import QQuickItem, QQuickWindow
from PySide6.QtTest import QTest

from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.route_registry import ROUTES
from ui_qml_bridge.route_registry_bridge import RouteRegistryBridge

REPO = Path(__file__).resolve().parents[2]
QML_ROOT = REPO / "ui_qml"
CRITICAL_QML_MESSAGES = (
    "Type unavailable",
    "Cannot override",
    "Failed to load",
    "is not a type",
    "Cannot assign",
    "ReferenceError",
    "Binding loop",
)

PLACEHOLDERS = (
    ("streaming.podcasts", "pages/streaming/PodcastsPlaceholderPage.qml", "planned", "podcastsPlaceholderPage"),
    ("connections.big_server", "pages/connections/BigServerPlaceholderPage.qml", "planned", "bigServerPlaceholderPage"),
    ("connections.navidrome", "pages/connections/NavidromePlaceholderPage.qml", "planned", "navidromePlaceholderPage"),
    ("connections.jellyfin", "pages/connections/JellyfinPlaceholderPage.qml", "planned", "jellyfinPlaceholderPage"),
    (
        "connections.home_assistant",
        "pages/connections/HomeAssistantPlaceholderPage.qml",
        "configuration_required",
        "homeAssistantPlaceholderPage",
    ),
    ("home_audio.chain_planner", "pages/home_audio/ChainPlannerPlaceholderPage.qml", "planned", "chainPlannerPlaceholderPage"),
    ("sync.portable_players", "pages/sync/PortablePlayersPlaceholderPage.qml", "planned", "portablePlayersPlaceholderPage"),
    ("sync.plans", "pages/sync/SyncPlansPlaceholderPage.qml", "planned", "syncPlansPlaceholderPage"),
    ("sync.history", "pages/sync/SyncHistoryPlaceholderPage.qml", "planned", "syncHistoryPlaceholderPage"),
)


def _wait_until(app: QGuiApplication, predicate, timeout_ms: int = 3000) -> None:
    elapsed = 0
    while not predicate() and elapsed < timeout_ms:
        app.processEvents()
        QTest.qWait(10)
        elapsed += 10
    assert predicate(), f"Condition not reached after {timeout_ms} ms"


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


@pytest.fixture
def gui_app(qapp) -> QGuiApplication:
    app = QGuiApplication.instance()
    assert app is not None
    return app


@pytest.fixture
def qml_messages() -> Iterator[list[str]]:
    messages: list[str] = []

    def handler(_message_type, _context, message: str) -> None:
        messages.append(message)

    previous = qInstallMessageHandler(handler)
    try:
        yield messages
    finally:
        qInstallMessageHandler(previous)


def _assert_no_critical_messages(messages: list[str]) -> None:
    critical = [
        message
        for message in messages
        if any(marker.lower() in message.lower() for marker in CRITICAL_QML_MESSAGES)
    ]
    assert not critical, "Critical Qt/QML diagnostics:\n" + "\n".join(critical)


def _page_stack(
    gui_app: QGuiApplication,
    qml_messages: list[str],
    capabilities: set[str],
) -> tuple[QQmlEngine, RouteRegistryBridge, NavigationBridge, QQmlComponent, QQuickItem]:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    navigation = NavigationBridge()
    navigation.set_capabilities(capabilities)
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    engine.rootContext().setContextProperty("navigationBridge", navigation)

    component = _component(engine, "shell/PageStack.qml")
    assert component.isReady(), component.errorString()
    stack = component.createWithInitialProperties({"width": 1000, "height": 700})
    assert stack is not None, component.errorString()
    navigation.routeChanged.connect(stack.loadRoute)
    gui_app.processEvents()
    _assert_no_critical_messages(qml_messages)
    return engine, registry, navigation, component, stack


def test_feature_state_page_compiles_and_instantiates(
    gui_app: QGuiApplication,
    qml_messages: list[str],
) -> None:
    engine = QQmlEngine()
    component = _component(engine, "components/FeatureStatePage.qml")
    assert component.isReady(), component.errorString()
    page = component.createWithInitialProperties({"width": 800, "height": 600})
    assert page is not None, component.errorString()
    assert page.property("featureState") == "planned"
    assert page.objectName() == "featureStatePage"
    _assert_no_critical_messages(qml_messages)
    page.deleteLater()
    engine.deleteLater()


@pytest.mark.parametrize(
    ("route", "relative_path", "expected_state", "expected_object_name"),
    PLACEHOLDERS,
)
def test_placeholder_component_runtime(
    gui_app: QGuiApplication,
    qml_messages: list[str],
    route: str,
    relative_path: str,
    expected_state: str,
    expected_object_name: str,
) -> None:
    engine = QQmlEngine()
    component = _component(engine, relative_path)
    assert component.isReady(), f"{route}: {component.errorString()}"
    page = component.createWithInitialProperties({"width": 800, "height": 600})
    assert page is not None, f"{route}: {component.errorString()}"
    assert page.property("featureState") == expected_state
    assert page.objectName() == expected_object_name
    assert ROUTES[route]["source"].endswith(Path(relative_path).name)
    _assert_no_critical_messages(qml_messages)
    page.deleteLater()
    engine.deleteLater()


@pytest.mark.parametrize("capabilities", (set(), {"unrelated_capability"}))
@pytest.mark.parametrize(
    ("route", "_relative_path", "_expected_state", "expected_object_name"),
    PLACEHOLDERS,
)
def test_placeholder_route_loads_through_navigation_and_page_stack(
    gui_app: QGuiApplication,
    qml_messages: list[str],
    capabilities: set[str],
    route: str,
    _relative_path: str,
    _expected_state: str,
    expected_object_name: str,
) -> None:
    engine, registry, navigation, component, stack = _page_stack(
        gui_app, qml_messages, capabilities
    )
    navigation.navigate(route)
    _wait_until(gui_app, lambda: stack.property("lastLoadedRoute") == route)

    assert navigation.currentRoute == route
    assert stack.property("currentRoute") == route
    assert stack.property("lastLoadedRoute") == route
    assert stack.property("loadedObjectName") == expected_object_name
    assert stack.property("lastError") == ""
    assert stack.property("lastRequestedSource") == ROUTES[route]["source"]
    _assert_no_critical_messages(qml_messages)
    stack.deleteLater()
    component.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


@pytest.mark.parametrize(
    ("alias", "canonical"),
    (
        ("radio", "streaming.radio"),
        ("devices", "sync"),
        ("devices.mobile_pairing", "sync.mobile"),
        ("assistant", "michi_ai"),
        ("metadata.inspector", "audio_lab.metadata"),
        ("library_doctor", "audio_lab.library_health"),
        ("equalizer", "audio_lab.processing"),
        ("outputs", "audio_lab.processing"),
    ),
)
def test_registry_aliases_return_canonical_metadata(alias: str, canonical: str) -> None:
    registry = RouteRegistryBridge()
    assert registry.isValidRoute(alias)
    assert registry.getSource(alias) == registry.getSource(canonical)
    assert registry.getTitle(alias) == registry.getTitle(canonical)
    assert registry.getStatus(alias) == registry.getStatus(canonical)


@pytest.mark.parametrize(
    ("initial_route", "target_route", "expected_object_name"),
    (
        ("streaming.radio", "streaming.podcasts", "podcastsPlaceholderPage"),
        ("connections.micro_server", "connections.big_server", "bigServerPlaceholderPage"),
        ("connections.micro_server", "connections.navidrome", "navidromePlaceholderPage"),
        ("connections.micro_server", "connections.jellyfin", "jellyfinPlaceholderPage"),
        (
            "connections.micro_server",
            "connections.home_assistant",
            "homeAssistantPlaceholderPage",
        ),
        ("home_audio.stream", "home_audio.chain_planner", "chainPlannerPlaceholderPage"),
        ("sync.mobile", "sync.portable_players", "portablePlayersPlaceholderPage"),
        ("sync.mobile", "sync.plans", "syncPlansPlaceholderPage"),
        ("sync.mobile", "sync.history", "syncHistoryPlaceholderPage"),
    ),
)
def test_sidebar_child_click_navigates_and_loads_placeholder(
    gui_app: QGuiApplication,
    qml_messages: list[str],
    initial_route: str,
    target_route: str,
    expected_object_name: str,
) -> None:
    engine = QQmlEngine()
    registry = RouteRegistryBridge()
    navigation = NavigationBridge()
    engine.rootContext().setContextProperty("routeRegistryBridge", registry)
    engine.rootContext().setContextProperty("navigationBridge", navigation)

    stack_component = _component(engine, "shell/PageStack.qml")
    sidebar_component = _component(engine, "shell/Sidebar.qml")
    assert stack_component.isReady(), stack_component.errorString()
    assert sidebar_component.isReady(), sidebar_component.errorString()
    stack = stack_component.createWithInitialProperties({"width": 900, "height": 700})
    sidebar = sidebar_component.createWithInitialProperties(
        {"width": 232, "height": 700, "currentRoute": initial_route}
    )
    assert stack is not None, stack_component.errorString()
    assert sidebar is not None, sidebar_component.errorString()

    navigation.routeChanged.connect(stack.loadRoute)
    sidebar.routeRequested.connect(navigation.navigate)
    window = QQuickWindow()
    window.resize(232, 700)
    sidebar.setParentItem(window.contentItem())
    window.show()

    _wait_until(
        gui_app,
        lambda: _find_visual_item(
            window.contentItem(), f"sidebarChildAction_{target_route}"
        ) is not None,
    )
    action = _find_visual_item(
        window.contentItem(), f"sidebarChildAction_{target_route}"
    )
    assert action is not None
    flickable = _find_visual_item(
        window.contentItem(), "sidebarNavigationFlickable"
    )
    assert flickable is not None
    action_scene_y = action.mapToScene(QPoint(0, 0)).y()
    viewport_scene_y = flickable.mapToScene(QPoint(0, 0)).y()
    viewport_bottom = viewport_scene_y + flickable.height()
    if (action_scene_y < viewport_scene_y
            or action_scene_y + action.height() > viewport_bottom):
        scroll_delta = action_scene_y + action.height() - viewport_bottom + 8
        flickable.setProperty(
            "contentY", max(0.0, float(flickable.property("contentY")) + scroll_delta)
        )
        gui_app.processEvents()
    scene_point = action.mapToScene(
        QPoint(int(action.width() / 2), int(action.height() / 2))
    ).toPoint()
    QTest.mouseClick(window, Qt.LeftButton, Qt.NoModifier, scene_point)
    _wait_until(gui_app, lambda: stack.property("lastLoadedRoute") == target_route)

    assert navigation.currentRoute == target_route
    assert stack.property("currentRoute") == target_route
    assert stack.property("loadedObjectName") == expected_object_name
    assert stack.property("lastError") == ""
    _assert_no_critical_messages(qml_messages)
    window.close()
    sidebar.deleteLater()
    stack.deleteLater()
    engine.deleteLater()


def test_unknown_route_uses_generic_placeholder(
    gui_app: QGuiApplication,
    qml_messages: list[str],
) -> None:
    engine, registry, navigation, component, stack = _page_stack(
        gui_app, qml_messages, set()
    )
    stack.loadRoute("route.that.does.not.exist")
    _wait_until(
        gui_app,
        lambda: stack.property("loadedObjectName") == "placeholderPage",
    )

    assert stack.property("currentRoute") == "route.that.does.not.exist"
    assert stack.property("lastRequestedSource") == "../pages/PlaceholderPage.qml"
    assert stack.property("lastError") == ""
    _assert_no_critical_messages(qml_messages)
    stack.deleteLater()
    component.deleteLater()
    navigation.deleteLater()
    registry.deleteLater()
    engine.deleteLater()


def test_canonical_component_error_is_reported_without_generic_fallback(
    gui_app: QGuiApplication,
    qml_messages: list[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    broken_source = "../pages/DoesNotExistForRuntimeTest.qml"
    monkeypatch.setitem(
        ROUTES,
        "runtime.broken",
        {
            "route": "runtime.broken",
            "title": "Broken runtime route",
            "source": broken_source,
            "status": "planned",
            "category": "tools",
            "params": None,
        },
    )
    engine, registry, navigation, component, stack = _page_stack(
        gui_app, qml_messages, set()
    )
    navigation.navigate("runtime.broken")
    _wait_until(gui_app, lambda: stack.property("lastError") != "")

    assert navigation.currentRoute == "runtime.broken"
    assert stack.property("currentRoute") == "runtime.broken"
    assert stack.property("lastRequestedSource") == broken_source
    assert stack.property("loadedObjectName") == ""
    assert stack.property("lastLoadedRoute") != "runtime.broken"
    assert "runtime.broken" in stack.property("lastError")
    assert "DoesNotExistForRuntimeTest.qml" in stack.property("lastError")
    assert stack.property("lastRequestedSource") != "../pages/PlaceholderPage.qml"
    stack.deleteLater()
    component.deleteLater()
    navigation.deleteLater()
    registry.deleteLater()
    engine.deleteLater()
