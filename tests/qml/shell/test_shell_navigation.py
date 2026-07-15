from __future__ import annotations
"""Tests for shell navigation — NavigationBridge back/forward, route resolution, errors, state."""

import pytest

from ui_qml_bridge.navigation_bridge import NavigationBridge
from ui_qml_bridge.route_registry import ROUTES

pytestmark = [pytest.mark.qml_module("shell")]


@pytest.fixture
def nav():
    return NavigationBridge()


class TestNavigationBasics:
    def test_initial_route(self, nav):
        assert nav.currentRoute == "home"
        assert nav.currentTitle == "Inicio"

    def test_navigate(self, nav):
        nav.navigate("library")
        assert nav.currentRoute == "library"
        assert nav.canGoBack is True
        assert nav.canGoForward is False

    def test_navigate_same_route_refreshes(self, nav):
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.navigate("home")
        assert signals == ["home"]

    def test_back(self, nav):
        nav.navigate("library")
        nav.navigate("radio")
        assert nav.currentRoute == "radio"
        nav.back()
        assert nav.currentRoute == "library"
        assert nav.canGoForward is True

    def test_forward(self, nav):
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "radio"

    def test_back_empty_stack(self, nav):
        nav.back()
        assert nav.currentRoute == "home"

    def test_forward_empty_stack(self, nav):
        nav.forward()
        assert nav.currentRoute == "home"

    def test_replace(self, nav):
        nav.replace("radio")
        assert nav.currentRoute == "radio"
        assert nav.canGoBack is False

    def test_clear_history(self, nav):
        nav.navigate("library")
        nav.clearHistory()
        assert nav.canGoBack is False
        assert nav.canGoForward is False

    def test_invalid_route_becomes_placeholder(self, nav):
        errors = []
        nav.invalidRouteError.connect(lambda r, m: errors.append((r, m)))
        nav.navigate("non_existent_route")
        assert nav.currentRoute == "placeholder"
        assert len(errors) > 0

    def test_refresh_current(self, nav):
        signals = []
        nav.routeRefreshRequested.connect(lambda r: signals.append(r))
        nav.refreshCurrent()
        assert signals == ["home"]


class TestNavigationState:
    def test_save_restore_state(self, nav):
        nav.navigate("library")
        nav.navigateWithParams("library.album_detail", {"album_key": "abc123"})
        state = nav.saveState()
        assert state["ok"] is True

        nav2 = NavigationBridge()
        result = nav2.restoreState(state["state"])
        assert result["ok"] is True
        assert nav2.currentRoute == "library.album_detail"
        assert nav2.currentParams.get("album_key") == "abc123"

    def test_restore_invalid_state(self, nav):
        result = nav.restoreState("{}")
        assert result["ok"] is False

    def test_deep_link(self, nav):
        result = nav.deepLink("/library")
        assert result["ok"] is True
        assert result["route"] == "library"

    def test_deep_link_with_params(self, nav):
        result = nav.deepLink("/library.album_detail?album_key=xyz")
        assert result["ok"] is True
        assert result["route"] == "library.album_detail"
        assert result["params"]["album_key"] == "xyz"

    def test_history_limit(self, nav):
        for _ in range(60):
            nav.navigate("library")
        assert len(nav._back_stack) <= 50

    def test_navigate_with_params(self, nav):
        nav.navigateWithParams("library.album_detail", {"album_key": "test123"})
        assert nav.currentRoute == "library.album_detail"
        assert nav.currentParams == {"album_key": "test123"}

    def test_navigate_without_required_params_errors(self, nav):
        errors = []
        nav.invalidRouteError.connect(lambda r, m: errors.append(m))
        nav.navigateWithParams("library.album_detail", {})
        assert len(errors) > 0
        assert any("Missing required" in e for e in errors)

    def test_current_title_unknown_route(self, nav):
        nav._current_route = "unknown_route"
        assert nav.currentTitle == "Sección en migración"

    def test_current_title_known_route(self, nav):
        nav._current_route = "library.albums"
        assert nav.currentTitle == "Álbumes"


class TestNavigationCapabilities:
    def test_capability_gate(self, nav):
        nav.set_capabilities(set())
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "home"

    def test_capability_allows(self, nav):
        nav.set_capabilities({"audio_lab"})
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "audio_lab.overview"

    def test_no_capabilities_required(self, nav):
        nav.navigate("library")
        assert nav.currentRoute == "library"


class TestRouteRegistry:
    def test_all_routes_have_title(self):
        for route, info in ROUTES.items():
            assert "title" in info, f"Route {route} missing title"

    def test_all_routes_have_category(self):
        for route, info in ROUTES.items():
            assert "category" in info, f"Route {route} missing category"

    def test_all_routes_have_status(self):
        for route, info in ROUTES.items():
            assert "status" in info, f"Route {route} missing status"

    def test_detail_routes_have_params(self):
        detail_no_params = {"group_editor", "mix_generator"}
        for route, info in ROUTES.items():
            if info.get("category") == "detail" and route not in detail_no_params:
                assert "params" in info, f"Detail route {route} missing params"

    def test_no_duplicate_routes(self):
        assert len(ROUTES) == len(set(ROUTES.keys()))


class TestNavigationSignals:
    def test_route_changed_emitted(self, nav):
        signals = []
        nav.routeChanged.connect(lambda r: signals.append(r))
        nav.navigate("library")
        assert "library" in signals

    def test_back_stack_changed_on_navigate(self, nav):
        signals = []
        nav.backStackChanged.connect(lambda: signals.append(True))
        nav.navigate("library")
        assert len(signals) >= 1

    def test_forward_stack_cleared_on_navigate(self, nav):
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.canGoForward is True
        nav.navigate("mix")
        assert nav.canGoForward is False
