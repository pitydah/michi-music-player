"""E2E workflow: Mix + Michi AI + Settings — bridge interactions + QTest."""
from __future__ import annotations

import pytest

pytestmark = [
    pytest.mark.qml_module("mix"),
    pytest.mark.qml_dimension("end_to_end"),
    pytest.mark.qml_route("mix"),
]


def _ok(result: dict) -> bool:
    return result.get("ok") is True


class TestMixAiSettingsE2E:
    def test_mix_bridge_exists(self, all_bridges):
        mx = all_bridges.get("mix")
        assert mx is not None, "MixBridge should exist"

    def test_mix_get_mixes(self, all_bridges):
        mx = all_bridges.get("mix")
        assert mx is not None
        result = mx.getMixes()
        assert isinstance(result, (list, tuple))

    def test_mix_get_detail(self, all_bridges):
        mx = all_bridges.get("mix")
        assert mx is not None
        result = mx.getMixDetail("daily")
        assert isinstance(result, dict)

    def test_mix_navigation(self, nav):
        nav.navigate("mix")
        assert nav.currentRoute == "mix", (
            f"Expected 'mix', got '{nav.currentRoute}'"
        )

    def test_ai_bridge_exists(self, all_bridges):
        ai = all_bridges.get("michi_ai")
        assert ai is not None, "MichiAIBridge should exist"

    def test_ai_get_suggestions(self, all_bridges):
        ai = all_bridges.get("michi_ai")
        assert ai is not None
        result = ai.getSuggestions()
        assert isinstance(result, (list, tuple))

    def test_ai_navigation(self, nav):
        nav.navigate("ai")
        assert nav.currentRoute == "ai", (
            f"Expected 'ai', got '{nav.currentRoute}'"
        )

    def test_settings_bridge_exists(self, all_bridges):
        ss = all_bridges.get("settings")
        assert ss is not None, "SettingsBridge should exist"

    def test_settings_get(self, all_bridges):
        ss = all_bridges.get("settings_v2")
        assert ss is not None
        result = ss.getValue("audio/volume")
        assert result is None or isinstance(result, (str, dict))

    def test_settings_validate_key(self, all_bridges):
        ss = all_bridges.get("settings_v2")
        assert ss is not None
        result = ss.validate("audio/volume")
        assert isinstance(result, dict)

    def test_settings_apply(self, all_bridges):
        ss = all_bridges.get("settings_v2")
        assert ss is not None
        result = ss.apply("audio/volume", 50)
        assert isinstance(result, dict)

    def test_settings_navigation(self, nav):
        nav.navigate("settings")
        assert nav.currentRoute == "settings", (
            f"Expected 'settings', got '{nav.currentRoute}'"
        )

    def test_qtest_navigate_settings(self, nav, root_window):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item
        nav.navigate("settings")
        assert nav.currentRoute == "settings"
        header = find_qml_item(root_window, "settingsGeneralPage")
        assert header is not None, "settingsGeneralPage not found"
        header.forceActiveFocus()
        QTest.keyClick(header, Qt.Key_Down)
        QTest.qWait(50)
        assert nav.currentRoute == "settings"

    def test_qtest_click_eq_bypass(self, nav, root_window, all_bridges):
        from PySide6.QtTest import QTest
        from .conftest import find_qml_item, qtest_click_item
        eq_bridge = all_bridges.get("eq")
        assert eq_bridge is not None, "EqBridge should exist"
        nav.navigate("equalizer")
        assert nav.currentRoute == "equalizer", (
            f"Expected 'equalizer', got '{nav.currentRoute}'"
        )
        eq_page = find_qml_item(root_window, "equalizerPage")
        assert eq_page is not None, "equalizerPage not found"
        bypass_btn = None
        for child in eq_page.childItems():
            text = child.property("text") if hasattr(child, 'property') else ""
            if "Bypass" in str(text) or "Activar" in str(text):
                bypass_btn = child
                break
        if bypass_btn is None:
            for child in eq_page.childItems():
                if hasattr(child, 'clicked'):
                    bypass_btn = child
                    break
        assert bypass_btn is not None, "EQ bypass button not found"
        bypass_before = getattr(eq_bridge, 'bypass', None)
        qtest_click_item(bypass_btn, root_window)
        QTest.qWait(100)
        bypass_after = getattr(eq_bridge, 'bypass', None)
        if bypass_before is not None and bypass_after is not None:
            assert bypass_before != bypass_after, (
                f"EQ bypass should toggle: {bypass_before} -> {bypass_after}"
            )
