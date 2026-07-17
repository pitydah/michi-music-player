"""Workflow: Home — bridge existence and navigation."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("home"),
    pytest.mark.qml_dimension("vertical_workflow"),
    pytest.mark.qml_route("home"),
]


class TestHomeWorkflow:
    def test_home_bridge_exists(self, bootstrap):
        home_bridge = bootstrap._bridges.get("home")
        assert home_bridge is not None, "HomeBridge should be registered"

    def test_capability_bridge_exists(self, bootstrap):
        cap = bootstrap._bridges.get("capability")
        assert cap is not None, "CapabilityBridge should be registered"

    def test_navigate_to_home(self, nav):
        nav.navigate("home")
        assert nav.currentRoute == "home", (
            f"Expected 'home', got '{nav.currentRoute}'"
        )

    def test_qtest_click_continue_card(self, nav, playback_bridge, root_window):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        nav.navigate("home")
        assert nav.currentRoute == "home"
        continue_card = find_qml_item(root_window, "continueCard")
        assert continue_card is not None, "continueCard not found"
        route_before = nav.currentRoute
        qtest_click_item(continue_card, root_window)
        QTest.qWait(100)
        route_after = nav.currentRoute
        assert route_after in ("home", "playback"), (
            f"Route after continue card click: '{route_after}'"
        )
        has_playback = getattr(continue_card, '_hasPlayback', None) or continue_card.property("hasPlayback")
        if has_playback:
            QTest.qWait(50)
