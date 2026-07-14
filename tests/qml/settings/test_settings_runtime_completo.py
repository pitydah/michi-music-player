"""EE — Settings runtime completo: schema, control, validation, adapter, backend, result,
persistence, consumer update, rollback, restart policy, layouts, no adapter without applied."""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from core.settings_adapters import (
    AccessibilitySettingsAdapter, AudioSettingsAdapter, CacheSettingsAdapter,
    ConnectionSettingsAdapter, DeviceSettingsAdapter, EqSettingsAdapter,
    HistorySettingsAdapter, HomeAudioSettingsAdapter, LibrarySettingsAdapter,
    LoggingSettingsAdapter, LyricsSettingsAdapter, PlaybackSettingsAdapter,
    RadioSettingsAdapter, ThemeSettingsAdapter, register_all_adapters,
)
from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
from core.settings_runtime_coordinator import SettingsApplyResult as CoordinatorApplyResult


@pytest.fixture
def coordinator():
    c = SettingsRuntimeCoordinator(player_service=MagicMock())
    register_all_adapters(c)
    return c


class TestSchema:
    def test_get_entry_exists(self):
        from core.settings_schema import get_entry
        entry = get_entry("playback/default_volume")
        assert entry is not None
        assert entry.key == "playback/default_volume"

    def test_get_entry_unknown_returns_none(self):
        from core.settings_schema import get_entry
        assert get_entry("nonexistent/key") is None

    def test_validate_int_pass(self):
        from core.settings_schema import validate
        ok, _ = validate("playback/default_volume", 70)
        assert ok

    def test_validate_int_fail(self):
        from core.settings_schema import validate
        ok, _ = validate("playback/default_volume", -5)
        assert ok is False


class TestControl:
    def test_14_adapters_registered(self):
        c = SettingsRuntimeCoordinator()
        register_all_adapters(c)
        assert len(c._adapters) == 14

    def test_14_adapter_classes_have_keys(self):
        classes = [
            ThemeSettingsAdapter, PlaybackSettingsAdapter, AudioSettingsAdapter,
            EqSettingsAdapter, LibrarySettingsAdapter, CacheSettingsAdapter,
            HistorySettingsAdapter, RadioSettingsAdapter, LyricsSettingsAdapter,
            DeviceSettingsAdapter, ConnectionSettingsAdapter, HomeAudioSettingsAdapter,
            LoggingSettingsAdapter, AccessibilitySettingsAdapter,
        ]
        for cls in classes:
            keys = cls.supported_keys()
            assert len(keys) > 0

    def test_adapter_for_theme(self, coordinator):
        assert isinstance(coordinator.adapter_for("appearance/theme"), ThemeSettingsAdapter)

    def test_adapter_for_unknown_returns_none(self, coordinator):
        assert coordinator.adapter_for("nonexistent/key") is None


class TestValidation:
    def test_invalid_value_returns_error_code(self, coordinator):
        result = coordinator.execute("playback/default_volume", -5)
        assert result["ok"] is False
        assert result["error_code"] == "INVALID_VALUE"

    def test_unknown_key_returns_error_code(self, coordinator):
        result = coordinator.execute("nonexistent/key", "val")
        assert result["ok"] is False
        assert result["error_code"] == "UNKNOWN_KEY"

    def test_valid_value_passes(self, coordinator):
        result = coordinator.execute("accessibility/font_size", "large")
        assert result["ok"] is True


class TestAdapter:
    def test_adapter_apply_called(self, coordinator):
        with patch.object(coordinator.adapter_for("appearance/theme"), "apply") as mock_apply:
            coordinator.execute("appearance/theme", "dark")
            mock_apply.assert_called_once_with("appearance/theme", "dark")

    def test_adapter_apply_failure_reverts(self, coordinator):
        coord = SettingsRuntimeCoordinator(player_service=MagicMock())

        class FailingThemeAdapter(ThemeSettingsAdapter):
            def apply(self, key, value):
                raise RuntimeError("apply failed")

        coord.register_adapter(FailingThemeAdapter())
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            result = coord.execute("appearance/theme", "dark")
            assert result["ok"] is False
            assert result["error_code"] == "APPLY_FAILED"
            ms.setValue.assert_not_called()

    def test_adapter_verify_after_apply(self, coordinator):
        with patch.object(coordinator.adapter_for("appearance/theme"), "verify") as mock_verify:
            mock_verify.return_value = True
            coordinator.execute("appearance/theme", "dark")
            mock_verify.assert_called_once()

    def test_no_adapter_no_applied(self, coordinator):
        result = coordinator.execute("general/start_minimized", True)
        assert result["applied"] is False
        assert "Sin adapter" in result["message"]


class TestPersistence:
    def test_persists_to_settings(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            result = coordinator.execute("appearance/theme", "dark")
            assert result["persisted"] is True
            ms.setValue.assert_called_once_with("appearance/theme", "dark")
            ms.sync.assert_called_once()

    def test_persisted_flag_false_on_adapter_failure(self, coordinator):
        coord = SettingsRuntimeCoordinator(player_service=MagicMock())

        class FailAdapter(ThemeSettingsAdapter):
            def apply(self, key, value):
                raise RuntimeError("fail")

        coord.register_adapter(FailAdapter())
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            result = coord.execute("appearance/theme", "dark")
            assert result["persisted"] is False


class TestConsumerUpdate:
    def test_playback_volume_emits_to_player(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = 70
            coordinator.execute("playback/default_volume", 50)
            coordinator._player.set_volume.assert_called_once_with(50)

    def test_repeat_mode_emits(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "none"
            coordinator.execute("playback/repeat_mode", "all")
            coordinator._player.set_repeat_mode.assert_called_once_with("all")

    def test_log_level_emits(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "warning"
            result = coordinator.execute("advanced/log_level", "debug")
            assert result["ok"] is True


class TestRollback:
    def test_revert_calls_execute(self, coordinator):
        with patch.object(coordinator, "execute", return_value={"ok": True}) as mock_exec:
            coordinator.revert("appearance/theme")
            mock_exec.assert_called_once()

    def test_revert_unknown_key(self, coordinator):
        result = coordinator.revert("nonexistent")
        assert result["ok"] is False

    def test_revert_uses_previous_value(self, coordinator):
        with patch("core.settings_runtime_coordinator.SETTINGS") as ms:
            ms.value.return_value = "light"
            coordinator.execute("appearance/theme", "dark")
            ms.value.return_value = "light"
            result = coordinator.revert("appearance/theme")
            assert result["requested_value"] == "light"


class TestRestartPolicy:
    def test_restart_required_true(self, coordinator):
        result = coordinator.execute("mpd/host", "192.168.1.1")
        assert result["requires_restart"] is True
        assert result["applied"] is False

    def test_restart_required_false(self, coordinator):
        result = coordinator.execute("accessibility/font_size", "large")
        assert result["requires_restart"] is False
        assert result["applied"] is True

    def test_restart_from_adapter_method(self, coordinator):
        result = coordinator.execute("audio/profile", "headphones")
        assert result["requires_restart"] is True


class TestLayouts:
    def test_settings_page_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
        assert (qml / "pages/SettingsPage.qml").exists()

    def test_settings_row_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml"
        assert (qml / "components/settings/SettingsRow.qml").exists()

    def test_settings_page_desktop(self, coordinator):
        result = coordinator.execute("appearance/compact_mode", False)
        assert result["ok"] is True
        assert result["applied"] is True

    def test_settings_page_compact(self, coordinator):
        result = coordinator.execute("appearance/compact_mode", True)
        assert result["ok"] is True


class TestCoordinatorApplyResult:
    def test_defaults(self):
        r = CoordinatorApplyResult()
        assert r.ok is True
        assert r.applied is False

    def test_to_dict(self):
        r = CoordinatorApplyResult(ok=True, key="k", requested_value="v", applied=True)
        d = r.to_dict()
        assert d["applied"] is True
        assert d["ok"] is True

    def test_no_applied_without_adapter_via_result(self):
        r = CoordinatorApplyResult(ok=True, applied=False)
        assert r.applied is False
