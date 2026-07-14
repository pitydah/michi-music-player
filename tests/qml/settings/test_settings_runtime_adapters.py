"""Tests for Settings Runtime Adapters — 13 adapters registered, adapter_for, transaction lifecycle."""
from unittest.mock import MagicMock, patch

import pytest

from core.settings_adapters import (
    ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
    EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
    HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
    DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
    LoggingSettingsAdapter, AccessibilitySettingsAdapter,
    register_all_adapters,
)
from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
from core.settings_runtime_coordinator import SettingsApplyResult as CoordinatorApplyResult


@pytest.fixture
def coordinator():
    c = SettingsRuntimeCoordinator(player_service=MagicMock())
    register_all_adapters(c)
    return c


class TestAllAdaptersRegistered:
    def test_14_adapters_registered(self):
        c = SettingsRuntimeCoordinator()
        register_all_adapters(c)
        assert len(c._adapters) == 14

    def test_14_adapter_classes(self):
        classes = [
            ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
            EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
            HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
            DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
            LoggingSettingsAdapter, AccessibilitySettingsAdapter,
        ]
        assert len(classes) == 14

    def test_each_adapter_has_supported_keys(self):
        classes = [
            ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
            EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
            HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
            DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
            LoggingSettingsAdapter, AccessibilitySettingsAdapter,
        ]
        for cls in classes:
            keys = cls.supported_keys()
            assert len(keys) > 0, f"{cls.__name__} has no supported keys"
            for k in keys:
                assert isinstance(k, str)


class TestAdapterFor:
    def test_adapter_for_theme(self, coordinator):
        adapter = coordinator.adapter_for("appearance/theme")
        assert isinstance(adapter, ThemeSettingsAdapter)

    def test_adapter_for_accent(self, coordinator):
        adapter = coordinator.adapter_for("appearance/accent_color")
        assert isinstance(adapter, ThemeSettingsAdapter)

    def test_adapter_for_accessibility(self, coordinator):
        adapter = coordinator.adapter_for("accessibility/font_size")
        assert isinstance(adapter, AccessibilitySettingsAdapter)

    def test_adapter_for_playback(self, coordinator):
        adapter = coordinator.adapter_for("playback/default_volume")
        assert isinstance(adapter, PlaybackSettingsAdapter)

    def test_adapter_for_audio(self, coordinator):
        adapter = coordinator.adapter_for("audio/device")
        assert isinstance(adapter, AudioSettingsAdapter)

    def test_adapter_for_eq(self, coordinator):
        adapter = coordinator.adapter_for("eq/enabled")
        assert isinstance(adapter, EqSettingsAdapter)

    def test_adapter_for_library(self, coordinator):
        adapter = coordinator.adapter_for("library/auto_scan")
        assert isinstance(adapter, LibrarySettingsAdapter)

    def test_adapter_for_cache(self, coordinator):
        adapter = coordinator.adapter_for("cache/covers_size")
        assert isinstance(adapter, CacheSettingsAdapter)

    def test_adapter_for_history(self, coordinator):
        adapter = coordinator.adapter_for("privacy/history_enabled")
        assert isinstance(adapter, HistorySettingsAdapter)

    def test_adapter_for_radio(self, coordinator):
        adapter = coordinator.adapter_for("radio/default_codec")
        assert isinstance(adapter, RadioSettingsAdapter)

    def test_adapter_for_lyrics(self, coordinator):
        adapter = coordinator.adapter_for("lyrics/provider")
        assert isinstance(adapter, LyricsSettingsAdapter)

    def test_adapter_for_devices(self, coordinator):
        adapter = coordinator.adapter_for("devices/sync_enabled")
        assert isinstance(adapter, DeviceSettingsAdapter)

    def test_adapter_for_connections(self, coordinator):
        adapter = coordinator.adapter_for("connections/server_port")
        assert isinstance(adapter, ConnectionSettingsAdapter)

    def test_adapter_for_home_audio(self, coordinator):
        adapter = coordinator.adapter_for("home_audio/ha_host")
        assert isinstance(adapter, HomeAudioSettingsAdapter)

    def test_adapter_for_logging(self, coordinator):
        adapter = coordinator.adapter_for("advanced/log_level")
        assert isinstance(adapter, LoggingSettingsAdapter)


class TestSettingsApplyResult:
    def test_constructor_defaults(self):
        r = CoordinatorApplyResult()
        assert r.ok is True
        assert r.key == ""
        assert r.requested_value is None
        assert r.previous_value is None
        assert r.persisted is False
        assert r.applied is False
        assert r.requires_restart is False
        assert r.error_code == ""
        assert r.message == ""
        assert r.affected_service == ""

    def test_constructor_all_fields(self):
        r = CoordinatorApplyResult(
            ok=True, key="test/key", requested_value="v", previous_value="old",
            persisted=True, applied=True, requires_restart=False,
            error_code="", message="ok", affected_service="TestAdapter"
        )
        assert r.ok is True
        assert r.key == "test/key"
        assert r.requested_value == "v"
        assert r.previous_value == "old"

    def test_to_dict(self):
        r = CoordinatorApplyResult(ok=True, key="k", requested_value="v", applied=True)
        d = r.to_dict()
        assert d["ok"] is True
        assert d["key"] == "k"
        assert d["applied"] is True


class TestTransactionLifecycle:
    def test_execute_unknown_key(self, coordinator):
        result = coordinator.execute("nonexistent/key", "val")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_KEY"

    def test_execute_invalid_value(self, coordinator):
        result = coordinator.execute("playback/default_volume", -5)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_VALUE"

    def test_execute_success_with_adapter(self, coordinator):
        result = coordinator.execute("appearance/theme", "dark")
        assert result["ok"] is True
        assert result["key"] == "appearance/theme"
        assert result["requested_value"] == "dark"

    def test_execute_success_no_adapter(self, coordinator):
        result = coordinator.execute("general/start_minimized", True)
        assert result["ok"] is True
        assert result["message"] == "Sin adapter — sólo persistido"

    def test_execute_persists(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            result = coordinator.execute("appearance/theme", "dark")
            assert result["ok"] is True
            ms.setValue.assert_called_once_with("appearance/theme", "dark")
            ms.sync.assert_called_once()

    def test_execute_restart_required(self, coordinator):
        result = coordinator.execute("mpd/host", "192.168.1.1")
        assert result["requires_restart"] is True
        assert result["applied"] is False

    def test_execute_no_applied_without_adapter(self, coordinator):
        result = coordinator.execute("general/start_minimized", True)
        assert result["applied"] is False

    def test_execute_affected_service(self, coordinator):
        result = coordinator.execute("appearance/theme", "dark")
        assert "ThemeSettingsAdapter" in result["affected_service"]

    def test_adapter_apply_failure(self):
        coord = SettingsRuntimeCoordinator(player_service=MagicMock())
        class FailingThemeAdapter(ThemeSettingsAdapter):
            def apply(self, key, value):
                raise RuntimeError("fail")
        coord.register_adapter(FailingThemeAdapter())
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            result = coord.execute("appearance/theme", "dark")
            assert result["ok"] is False
            assert result["error_code"] == "APPLY_FAILED"
            ms.setValue.assert_not_called()

    def test_revert_unknown_key(self, coordinator):
        result = coordinator.revert("nonexistent")
        assert result["ok"] is False

    def test_revert_calls_execute(self, coordinator):
        with patch.object(coordinator, "execute", return_value={"ok": True}) as me:
            coordinator.revert("appearance/theme")
            me.assert_called_once()

    def test_legacy_apply(self, coordinator):
        result = coordinator.apply("appearance/theme", "dark")
        assert isinstance(result, CoordinatorApplyResult)
        assert result.ok is True
