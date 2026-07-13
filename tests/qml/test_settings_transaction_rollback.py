"""Tests for Settings transaction rollback — verify coordinator owns the transaction."""
from unittest.mock import MagicMock, patch

import pytest

from core.settings_runtime_coordinator import SettingsRuntimeCoordinator, SettingsApplyResult
from core.settings_service import SettingsService


@pytest.fixture
def coordinator():
    return SettingsRuntimeCoordinator(player_service=MagicMock())


@pytest.fixture
def service(coordinator):
    svc = SettingsService(coordinator=coordinator)
    return svc


class TestTransactionFlow:
    def test_set_delegates_to_coordinator(self, service, coordinator):
        with patch.object(coordinator, "execute", return_value={"ok": True, "applied": True}) as mock_exec:
            result = service.set_("appearance/theme", "dark")
            mock_exec.assert_called_once_with("appearance/theme", "dark")
            assert result["ok"] is True

    def test_reset_delegates_to_coordinator(self, service, coordinator):
        with patch.object(coordinator, "execute", return_value={"ok": True, "key": "appearance/theme"}) as mock_exec:
            from core.settings_schema import get_entry
            entry = get_entry("appearance/theme")
            result = service.reset("appearance/theme")
            mock_exec.assert_called_once_with("appearance/theme", entry.default)
            assert result["ok"] is True

    def test_reset_unknown_key(self, service):
        result = service.reset("nonexistent/key")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_KEY"

    def test_service_rejects_without_coordinator(self):
        svc = SettingsService(coordinator=None)
        result = svc.set_("appearance/theme", "dark")
        assert result["ok"] is False
        assert result["error_code"] == "NO_COORDINATOR"

    def test_coordinator_execute_validates_key(self, coordinator):
        result = coordinator.execute("nonexistent/key", "value")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_KEY"

    def test_coordinator_execute_validates_value(self, coordinator):
        result = coordinator.execute("playback/default_volume", -1)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_VALUE"

    def test_coordinator_execute_success(self, coordinator):
        result = coordinator.execute("appearance/theme", "dark")
        assert result["ok"] is True
        assert result["key"] == "appearance/theme"
        assert result["requested_value"] == "dark"

    def test_coordinator_persists_after_apply(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as mock_settings:
            mock_settings.value.return_value = "light"
            result = coordinator.execute("appearance/theme", "dark")
            assert result["ok"] is True
            mock_settings.setValue.assert_called_once_with("appearance/theme", "dark")
            mock_settings.sync.assert_called_once()

    def test_coordinator_apply_result_includes_all_fields(self, coordinator):
        result = coordinator.execute("playback/default_volume", 80)
        assert "key" in result
        assert "requested_value" in result
        assert "previous_value" in result
        assert "persisted" in result
        assert "applied" in result
        assert "requires_restart" in result
        assert "affected_service" in result
        assert "error_code" in result
        assert "message" in result

    def test_apply_result_to_dict(self):
        r = SettingsApplyResult(
            ok=True, key="test", requested_value="val", previous_value="old",
            persisted=True, applied=False, requires_restart=True,
            error_code="", message="test", affected_service="TestAdapter"
        )
        d = r.to_dict()
        assert d["ok"] is True
        assert d["key"] == "test"
        assert d["requested_value"] == "val"
        assert d["previous_value"] == "old"
        assert d["persisted"] is True
        assert d["applied"] is False
        assert d["requires_restart"] is True
        assert d["affected_service"] == "TestAdapter"


class TestCoordinatorRevert:
    def test_revert_unknown_key(self, coordinator):
        result = coordinator.revert("nonexistent/key")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_KEY"

    def test_revert_calls_execute_with_default(self, coordinator):
        from core.settings_schema import get_entry
        entry = get_entry("appearance/theme")
        with patch.object(coordinator, "execute", return_value={"ok": True}) as mock_exec:
            coordinator.revert("appearance/theme")
            mock_exec.assert_called_once_with("appearance/theme", entry.default)


class TestAdapterIntegration:
    def test_coordinator_finds_adapter(self, coordinator):
        from core.settings_adapters import ThemeSettingsAdapter
        coordinator.register_adapter(ThemeSettingsAdapter())
        result = coordinator.execute("appearance/theme", "dark")
        assert result["ok"] is True
        assert "ThemeSettingsAdapter" in result.get("affected_service", "")

    def test_adapter_apply_failure_rolls_back(self, coordinator):
        from core.settings_adapters import ThemeSettingsAdapter

        class FailingAdapter(ThemeSettingsAdapter):
            def apply(self, key, value):
                raise RuntimeError("Simulated adapter failure")

        coordinator.register_adapter(FailingAdapter())
        with patch("core.settings_runtime_coordinator.SETTINGS") as mock_settings:
            mock_settings.value.return_value = "light"
            result = coordinator.execute("appearance/theme", "dark")
            assert result["ok"] is False
            assert result["error_code"] == "APPLY_FAILED"
            mock_settings.setValue.assert_not_called()

    def test_adapters_supported_keys(self):
        from core.settings_adapters import (
            ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
            EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
            HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
            DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
            LoggingSettingsAdapter,
        )
        for cls in (ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
                    EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
                    HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
                    DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
                    LoggingSettingsAdapter):
            keys = cls.supported_keys()
            assert len(keys) > 0, f"{cls.__name__} has no supported keys"
            for k in keys:
                assert isinstance(k, str), f"{cls.__name__} key {k} not a string"


class TestResetAllWithCoordinator:
    def test_reset_all_delegates(self, service, coordinator):
        with patch.object(coordinator, "execute", return_value={"ok": True}) as mock_exec:
            result = service.reset_all()
            assert result["ok"] is True
            assert mock_exec.call_count > 1
