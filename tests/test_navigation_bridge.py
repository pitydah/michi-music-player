"""Tests for NavigationBridge."""

from michi.application.navigation_service import NavigationService
from michi.domain.navigation import AppRoute
from michi.presentation.navigation_bridge import NavigationBridge


class TestNavigationBridge:
    def test_current_route_reflects_service(self):
        svc = NavigationService()
        bridge = NavigationBridge(svc)
        assert bridge.property("currentRoute") == "library"

    def test_navigate_changes_route(self):
        svc = NavigationService()
        bridge = NavigationBridge(svc)
        bridge.navigate("queue")
        assert svc.state.current_route == AppRoute.QUEUE
        assert bridge.property("currentRoute") == "queue"

    def test_invalid_route_no_crash(self):
        svc = NavigationService()
        bridge = NavigationBridge(svc)
        bridge.navigate("banana")
        assert svc.state.current_route == AppRoute.LIBRARY

    def test_dispose_unsubscribes(self):
        svc = NavigationService()
        bridge = NavigationBridge(svc)
        assert len(svc._subscribers) == 1
        bridge.dispose()
        assert len(svc._subscribers) == 0
