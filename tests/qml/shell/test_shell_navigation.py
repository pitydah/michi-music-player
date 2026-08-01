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
        assert nav.currentRoute == "streaming.radio"
        nav.back()
        assert nav.currentRoute == "library"
        assert nav.canGoForward is True

    def test_forward(self, nav):
        nav.navigate("library")
        nav.navigate("radio")
        nav.back()
        assert nav.currentRoute == "library"
        nav.forward()
        assert nav.currentRoute == "streaming.radio"

    def test_back_empty_stack(self, nav):
        nav.back()
        assert nav.currentRoute == "home"

    def test_forward_empty_stack(self, nav):
        nav.forward()
        assert nav.currentRoute == "home"

    def test_replace(self, nav):
        nav.replace("radio")
        assert nav.currentRoute == "streaming.radio"
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

    def test_same_route_params_replace_without_history_entry(self, nav):
        routes = []
        params_changed = []
        nav.routeChanged.connect(routes.append)
        nav.routeParamsChanged.connect(lambda: params_changed.append(True))

        nav.navigateWithParams("search", {"query": "michi", "submitted": True})
        history_size = len(nav._back_stack)
        nav.navigateWithParams("search", {"query": "music", "submitted": True})

        assert nav.currentParams == {"query": "music", "submitted": True}
        assert len(nav._back_stack) == history_size
        assert routes == ["search"]
        assert len(params_changed) == 2

    def test_lightweight_params_do_not_navigate_or_change_history(self, nav):
        nav.navigateWithParams("search", {"query": "first"})
        nav.back()
        assert nav.canGoForward is True
        routes = []
        nav.routeChanged.connect(routes.append)
        history_size = len(nav._back_stack)

        params = {"query": "preview"}
        nav.updateCurrentParams(params)
        params["query"] = "mutated"

        assert nav.currentRoute == "home"
        assert nav.currentParams == {"query": "preview"}
        assert len(nav._back_stack) == history_size
        assert nav.canGoForward is True
        assert routes == []

    def test_identical_lightweight_params_are_noop(self, nav):
        signals = []
        nav.routeParamsChanged.connect(lambda: signals.append(True))
        nav.updateCurrentParams({})
        assert signals == []

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
    def test_missing_capability_keeps_informational_route_navigable(self, nav):
        nav.set_capabilities(set())
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "audio_lab"

    def test_capability_metadata_does_not_change_canonical_route(self, nav):
        nav.set_capabilities({"audio_lab"})
        nav.navigate("audio_lab.overview")
        assert nav.currentRoute == "audio_lab"

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
        detail_no_params = {"group_editor", "mix.generator", "mix.result", "mix.rules"}
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


class TestTerminalResults:
    """Patch 6 — every navigate() call ends in a terminal result."""

    def test_no_poll_timer(self, nav):
        # Polling was replaced by push-based subscription.
        assert getattr(nav, "_poll_timer", None) is None

    def test_route_loaded_on_success(self, nav):
        loaded = []
        nav.routeLoaded.connect(lambda r: loaded.append(r))
        nav.navigate("library")
        assert loaded == ["library"]

    def test_route_loaded_on_same_route_refresh(self, nav):
        loaded = []
        nav.routeLoaded.connect(lambda r: loaded.append(r))
        nav.navigate("home")
        assert loaded == ["home"]

    def test_route_unavailable_rendered_on_invalid_route(self, nav):
        unavailable = []
        nav.routeUnavailableRendered.connect(lambda r, m: unavailable.append((r, m)))
        nav.navigate("non_existent_route")
        assert len(unavailable) == 1
        assert unavailable[0][0] == "non_existent_route"

    def test_route_error_rendered_on_missing_required_param(self, nav):
        errors = []
        nav.routeErrorRendered.connect(lambda r, m: errors.append((r, m)))
        nav.navigateWithParams("library.album_detail", {})
        assert len(errors) == 1
        assert "Missing required" in errors[0][1]

    def test_back_emits_route_loaded(self, nav):
        loaded = []
        nav.routeLoaded.connect(lambda r: loaded.append(r))
        nav.navigate("library")
        nav.navigate("radio")
        loaded.clear()
        nav.back()
        assert loaded == ["library"]


class TestNavigationServicePush:
    """Patch 6 — NavigationService pushes requests; the bridge no longer polls."""

    def test_service_request_navigates_bridge_without_polling(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        assert getattr(nav, "_poll_timer", None) is None
        svc.navigate("library")
        assert nav.currentRoute == "library"

    def test_subscribe_dedupes_listener(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        # Re-subscribing the same callable must not duplicate it.
        svc.subscribe(nav._on_navigation_request)
        assert len(svc._listeners) == 1

    def test_go_back_pushes_request_to_bridge(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        svc.navigate("library")
        assert nav.currentRoute == "library"
        # go_back must push a "back" action the bridge dispatches to its own
        # history stack (previously it returned a dict without notifying).
        svc.go_back()
        assert nav.currentRoute == "home"

    def test_go_forward_pushes_request_to_bridge(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        svc.navigate("library")
        svc.go_back()
        assert nav.currentRoute == "home"
        svc.go_forward()
        assert nav.currentRoute == "library"

    def test_unsubscribe_detaches_listener(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        assert len(svc._listeners) == 1
        svc.unsubscribe(nav._on_navigation_request)
        assert svc._listeners == []
        # After unsubscribe, a navigate must NOT move the bridge.
        svc.navigate("library")
        assert nav.currentRoute == "home"

    def test_unsubscribe_unknown_listener_is_noop(self):
        from core.navigation_service import NavigationService
        svc = NavigationService()
        nav = NavigationBridge(navigation_service=svc)
        # Removing a never-subscribed callable must not raise.
        svc.unsubscribe(lambda r: None)
        assert len(svc._listeners) == 1
