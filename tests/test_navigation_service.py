"""Tests for NavigationService."""

from michi.application.navigation_service import NavigationService
from michi.domain.navigation import AppRoute


class TestNavigationService:
    def test_default_route_is_library(self):
        svc = NavigationService()
        assert svc.state.current_route == AppRoute.LIBRARY

    def test_navigate_changes_route(self):
        svc = NavigationService()
        svc.navigate("now_playing")
        assert svc.state.current_route == AppRoute.NOW_PLAYING

    def test_navigate_to_queue(self):
        svc = NavigationService()
        svc.navigate("queue")
        assert svc.state.current_route == AppRoute.QUEUE

    def test_same_route_no_duplicate_notification(self):
        svc = NavigationService()
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.navigate("library")  # already default
        assert len(calls) == 0

    def test_same_route_after_change(self):
        svc = NavigationService()
        svc.navigate("queue")
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.navigate("queue")  # already queue
        assert len(calls) == 0

    def test_invalid_route_no_change(self):
        svc = NavigationService()
        svc.navigate("now_playing")
        svc.navigate("banana")
        assert svc.state.current_route == AppRoute.NOW_PLAYING

    def test_invalid_route_no_notification(self):
        svc = NavigationService()
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.navigate("grapefruit")
        assert len(calls) == 0

    def test_notification_on_change(self):
        svc = NavigationService()
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.navigate("queue")
        assert len(calls) == 1

    def test_unsubscribe(self):
        svc = NavigationService()
        calls = []

        def cb():
            calls.append(1)

        svc.subscribe_changed(cb)
        svc.unsubscribe_changed(cb)
        svc.navigate("now_playing")
        assert len(calls) == 0
