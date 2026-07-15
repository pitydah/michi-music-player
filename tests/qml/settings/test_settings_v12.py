"""Tests for Settings v12 — SettingsBridgeV2, Outputs, Theme, Accessibility."""
from unittest.mock import MagicMock

import pytest


class TestSettingsBridgeV2:
    def test_requires_service(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        with pytest.raises(Exception):
            SettingsBridgeV2()

    def test_creation_with_service(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        sb = SettingsBridgeV2(service=MagicMock())
        assert sb is not None

    def test_get_value(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        svc = MagicMock()
        svc.get.return_value = "dark"
        sb = SettingsBridgeV2(service=svc)
        val = sb.getValue("appearance/theme")
        assert val == "dark"

    def test_set_value(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        svc = MagicMock()
        svc.set_.return_value = {"ok": True}
        sb = SettingsBridgeV2(service=svc)
        result = sb.setValue("appearance/theme", "light")
        assert result.get("ok")

    def test_reset_value(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        svc = MagicMock()
        svc.reset.return_value = {"ok": True}
        sb = SettingsBridgeV2(service=svc)
        result = sb.resetValue("appearance/theme")
        assert result.get("ok")

    def test_reset_all(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        svc = MagicMock()
        svc.reset_all.return_value = {"ok": True}
        sb = SettingsBridgeV2(service=svc)
        result = sb.resetAll()
        assert result.get("ok")

    def test_refresh(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        sb = SettingsBridgeV2(service=MagicMock())
        sb.refresh()
        assert True

    def test_categories(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        svc = MagicMock()
        svc.categories.return_value = [{"id": "general", "title": "General"}]
        sb = SettingsBridgeV2(service=svc)
        cats = sb.categories
        assert len(cats) > 0


class TestThemeBridge:
    def test_theme_bridge_exists(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge(coordinator=MagicMock())
        assert tb is not None

    def test_theme_has_colors(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        tb = ThemeBridge(coordinator=MagicMock())
        assert hasattr(tb, 'theme') or hasattr(tb, 'accentColor') or hasattr(tb, 'themeName')


class TestOutputProfilesBridge:
    def test_requires_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        with pytest.raises(Exception):
            OutputProfilesBridge()

    def test_creation_with_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        opb = OutputProfilesBridge(player_service=MagicMock())
        assert opb is not None

    def test_refresh(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        opb = OutputProfilesBridge(player_service=MagicMock())
        result = opb.refresh()
        assert isinstance(result, dict)
