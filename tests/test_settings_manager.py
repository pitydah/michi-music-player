from core.settings_manager import SETTINGS, DEFAULTS


class TestSettingsManager:
    def test_defaults_exist(self):
        assert len(DEFAULTS) > 10

    def test_settings_object(self):
        assert SETTINGS.organizationName() == "Michi"
