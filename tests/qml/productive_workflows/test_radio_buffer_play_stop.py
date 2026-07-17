"""Workflow: Radio → Buffer → Play → Stop."""
from __future__ import annotations
import pytest

pytestmark = [
    pytest.mark.qml_module("radio"),
    pytest.mark.qml_dimension("vertical_workflow"),
]


class TestRadio:
    def test_radio_play_action(self, bootstrap, bridges):
        ar = bridges.get("action_registry")
        for aid in ("radio.play", "radio.stop"):
            a = ar.get(aid)
            assert a is not None, f"{aid} action exists"

    def test_radio_service_methods(self, bootstrap):
        svc = bootstrap.container.get("radio_service")
        assert svc is not None
        assert hasattr(svc, 'play_station')
        assert hasattr(svc, 'stop')
        assert hasattr(svc, 'get_buffer_ms') or hasattr(svc, 'set_buffer_ms')
        assert hasattr(svc, 'set_reconnect_policy')

    def test_radio_bridge_exists(self, bootstrap, bridges):
        rb = bridges.get("radio")
        assert rb is not None

    def test_qtest_click_station(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item, wait_for_condition
        nav.navigate("radio")
        assert nav.currentRoute == "radio", (
            f"Expected 'radio', got '{nav.currentRoute}'"
        )
        radio_page = find_qml_item(root_window, "radioPage")
        assert radio_page is not None, "radioPage not found"
        stations = [c for c in radio_page.childItems() if c.objectName() == "radioStationDetail"]
        if len(stations) == 0:
            pytest.skip("No radio stations available to click")
        radio_bridge = all_bridges.get("radio")
        assert radio_bridge is not None, "RadioBridge should exist"
        state_before = getattr(radio_bridge, '_state', '') or getattr(radio_bridge, 'state', '')
        qtest_click_item(stations[0], root_window)
        wait_for_condition(
            lambda: (getattr(radio_bridge, '_state', '') or getattr(radio_bridge, 'state', '')) != state_before,
            timeout_ms=500
        )
        QTest.qWait(100)
        assert nav.currentRoute == "radio"
        state_after = getattr(radio_bridge, '_state', '') or getattr(radio_bridge, 'state', '')
        assert state_after != state_before, f"Radio state should change: '{state_before}' -> '{state_after}'"
