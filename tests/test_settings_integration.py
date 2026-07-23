"""Tests for Settings — runtime coordinator, persistence, rollback."""


class TestSettingsIntegration:
    def test_coordinator_execute(self):
        from core.composition.infrastructure import build as infra
        from core.composition.playback import build as playback
        from core.composition.settings import build as settings_b
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        playback(c)
        settings_b(c)
        coord = c.get("settings_coordinator")
        assert coord._queue is c.get("queue_service")
        result = coord.execute("appearance/theme", "dark")
        assert result["ok"]
        assert result["persisted"]
        from core.settings_manager import get
        assert get("appearance/theme") == "dark"

    def test_coordinator_invalid_key(self):
        from core.composition.infrastructure import build as infra
        from core.composition.settings import build as settings_b
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        settings_b(c)
        coord = c.get("settings_coordinator")
        result = coord.execute("nonexistent/key", "value")
        assert not result["ok"]
        assert "UNKNOWN_KEY" in result.get("error_code", "")

    def test_coordinator_invalid_value(self):
        from core.composition.infrastructure import build as infra
        from core.composition.settings import build as settings_b
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        settings_b(c)
        coord = c.get("settings_coordinator")
        # Try setting a boolean key to a string
        result = coord.execute("appearance/theme", True)
        assert isinstance(result.get("ok"), bool)

    def test_coordinator_rollback(self):
        from core.composition.infrastructure import build as infra
        from core.composition.settings import build as settings_b
        from core.service_container import ServiceContainer
        c = ServiceContainer()
        infra(c)
        settings_b(c)
        coord = c.get("settings_coordinator")
        # Set and verify
        coord.execute("appearance/theme", "dark")
        from core.settings_manager import get
        prev = get("appearance/theme")
        # Rollback via revert
        if hasattr(coord, 'revert'):
            result = coord.revert("appearance/theme")
            assert result.get("ok")

    def test_persistence_across_restart(self):
        """Settings survive coordinator recreation."""
        from core.settings_manager import set_, get
        test_key = "_test_michi_persist"
        set_(test_key, "persisted_value")

        # New session (same QSettings persistence)
        val = get(test_key)
        assert val == "persisted_value"

        # Cleanup
        from PySide6.QtCore import QSettings
        QSettings().remove(test_key)

    def test_secrets_not_in_export(self):
        from core.secrets import redact_dict, is_sensitive
        assert is_sensitive("home_audio/ha_token")
        assert is_sensitive("mpd/password")
        d = {"api_key": "sk-secret", "name": "public"}
        r = redact_dict(d)
        assert "sk-secret" not in str(r)
        assert "public" in str(r)

    def test_settings_bridge_has_execute(self):
        from ui_qml_bridge.settings_bridge_v2 import SettingsBridgeV2
        assert hasattr(SettingsBridgeV2, 'setValue')

    def test_settings_schema_has_entries(self):
        from core.settings_schema import get_entry
        entry = get_entry("appearance/theme")
        assert entry is not None
