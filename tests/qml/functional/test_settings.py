"""Test: settings manager read/write and bridge integration."""


class TestSettingsManager:
    def test_settings_get_set(self):
        from core.settings_manager import get, set_
        test_key = "_test_michi_key"
        set_(test_key, "test_value")
        val = get(test_key)
        assert val is not None
        from PySide6.QtCore import QSettings
        s = QSettings()
        s.remove(test_key)

    def test_settings_defaults(self):
        from core.settings_manager import DEFAULTS
        assert len(DEFAULTS) > 0


class TestSettingsCategories:
    def test_settings_have_categories(self):
        from core.settings_manager import DEFAULTS
        categories = set()
        for key in DEFAULTS:
            cat = key.split("/")[0] if "/" in key else "general"
            categories.add(cat)
        assert len(categories) >= 3, f"Expected 3+ categories, got {categories}"
