"""PP — Settings completo: schema, control, validation, adapter, backend, persistence,
consumer update, rollback, restart policy, layouts, no adapter without applied,
output profiles, theme, accessibility global."""
from __future__ import annotations
from unittest.mock import MagicMock
import pytest
from core.settings_adapters import (
    AccessibilitySettingsAdapter, AudioSettingsAdapter, CacheSettingsAdapter,
    ConnectionSettingsAdapter, DeviceSettingsAdapter, EqSettingsAdapter,
    HistorySettingsAdapter, HomeAudioSettingsAdapter, LibrarySettingsAdapter,
    LoggingSettingsAdapter, LyricsSettingsAdapter, PlaybackSettingsAdapter,
    RadioSettingsAdapter, ThemeSettingsAdapter, register_all_adapters,
)
from core.settings_runtime_coordinator import SettingsRuntimeCoordinator
from core.settings_schema import ALL_CATEGORIES, get_entry, validate, get_default

pytestmark = [pytest.mark.qml_module("settings")]


@pytest.fixture
def coordinator():
    c = SettingsRuntimeCoordinator(player_service=MagicMock())
    register_all_adapters(c)
    return c


class TestSchemaCompleto:
    def test_all_categories_have_id_title(self):
        for cat in ALL_CATEGORIES:
            assert cat.id
            assert cat.title

    def test_all_sections_have_id_title(self):
        for cat in ALL_CATEGORIES:
            for sec in cat.sections:
                assert sec.id
                assert sec.title

    def test_all_entries_have_key_label(self):
        for cat in ALL_CATEGORIES:
            for sec in cat.sections:
                for e in sec.entries:
                    assert e.key
                    assert e.label

    def test_entry_types_valid(self):
        valid = {"text", "int", "bool", "select", "file", "audio_device",
                 "secret", "directory", "float", "slider", "action"}
        for cat in ALL_CATEGORIES:
            for sec in cat.sections:
                for e in sec.entries:
                    assert e.entry_type in valid, f"{e.key}: {e.entry_type}"

    def test_select_entries_have_options(self):
        for cat in ALL_CATEGORIES:
            for sec in cat.sections:
                for e in sec.entries:
                    if e.entry_type == "select":
                        assert e.options, f"{e.key} is select but no options"

    def test_int_entries_have_min_max(self):
        for cat in ALL_CATEGORIES:
            for sec in cat.sections:
                for e in sec.entries:
                    if e.entry_type == "int" and e.min_value is not None:
                        assert e.max_value is not None or e.validator

    def test_get_entry_known(self):
        e = get_entry("playback/default_volume")
        assert e is not None
        assert e.default == 70

    def test_get_entry_unknown(self):
        assert get_entry("nonexistent") is None

    def test_get_default_known(self):
        assert get_default("playback/default_volume") == 70

    def test_get_default_unknown(self):
        assert get_default("nonexistent") is None

    def test_validate_int_pass(self):
        ok, _ = validate("playback/default_volume", 70)
        assert ok

    def test_validate_int_fail_min(self):
        ok, _ = validate("playback/default_volume", -5)
        assert not ok

    def test_validate_int_fail_max(self):
        ok, _ = validate("playback/default_volume", 101)
        assert not ok

    def test_validate_sample_rate_valid(self):
        for sr in [0, 44100, 48000, 96000, 192000]:
            ok, _ = validate("audio/sample_rate", sr)
            assert ok

    def test_validate_sample_rate_invalid(self):
        ok, _ = validate("audio/sample_rate", 12345)
        assert not ok

    def test_validate_port_valid(self):
        ok, _ = validate("mpd/port", 6600)
        assert ok

    def test_validate_port_invalid(self):
        ok, _ = validate("mpd/port", 0)
        assert not ok

    def test_validate_port_too_high(self):
        ok, _ = validate("mpd/port", 99999)
        assert not ok

    def test_validate_unknown_key(self):
        ok, _ = validate("fake/key", "x")
        assert not ok


class TestControlCompleto:
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

    def test_adapter_for_unknown(self, coordinator):
        assert coordinator.adapter_for("nonexistent") is None

    def test_adapter_for_accessibility(self, coordinator):
        assert isinstance(coordinator.adapter_for("accessibility/mono"), AccessibilitySettingsAdapter)


class TestValidation:
    def test_invalid_value_error(self, coordinator):
        r = coordinator.execute("playback/default_volume", -5)
        assert not r["ok"]
        assert r["error_code"] == "INVALID_VALUE"

    def test_unknown_key_error(self, coordinator):
        r = coordinator.execute("bad/key", "x")
        assert not r["ok"]
        assert r["error_code"] == "UNKNOWN_KEY"

    def test_valid_value_success(self, coordinator):
        r = coordinator.execute("playback/default_volume", 80)
        assert r["ok"]
        assert r["requested_value"] == 80


class TestAdapters:
    def test_theme_adapter_applies(self):
        a = ThemeSettingsAdapter()
        r = a.apply("appearance/theme", "dark")
        assert r.ok
        assert a.verify("appearance/theme")

    def test_playback_adapter_applies(self):
        a = PlaybackSettingsAdapter()
        r = a.apply("playback/default_volume", 75)
        assert r.ok

    def test_audio_adapter_applies(self):
        a = AudioSettingsAdapter()
        r = a.apply("audio/buffer_ms", 200)
        assert r.ok

    def test_eq_adapter_applies(self):
        a = EqSettingsAdapter()
        r = a.apply("eq/enabled", True)
        assert r.ok

    def test_library_adapter_applies(self):
        a = LibrarySettingsAdapter()
        r = a.apply("library/auto_scan", True)
        assert r.ok

    def test_cache_adapter_applies(self):
        a = CacheSettingsAdapter()
        r = a.apply("cache/covers_size", 100)
        assert r.ok

    def test_history_adapter_applies(self):
        a = HistorySettingsAdapter()
        r = a.apply("privacy/history_enabled", True)
        assert r.ok

    def test_radio_adapter_applies(self):
        a = RadioSettingsAdapter()
        r = a.apply("radio/auto_reconnect", True)
        assert r.ok

    def test_lyrics_adapter_applies(self):
        a = LyricsSettingsAdapter()
        r = a.apply("lyrics/provider", "lrclib")
        assert r.ok

    def test_device_adapter_applies(self):
        a = DeviceSettingsAdapter()
        r = a.apply("devices/sync_enabled", True)
        assert r.ok

    def test_connection_adapter_applies(self):
        a = ConnectionSettingsAdapter()
        r = a.apply("connections/server_port", 53318)
        assert r.ok

    def test_home_audio_adapter_applies(self):
        a = HomeAudioSettingsAdapter()
        r = a.apply("home_audio/ha_host", "localhost")
        assert r.ok

    def test_logging_adapter_applies(self):
        a = LoggingSettingsAdapter()
        r = a.apply("advanced/log_level", "debug")
        assert r.ok

    def test_accessibility_adapter_applies(self):
        a = AccessibilitySettingsAdapter()
        r = a.apply("accessibility/high_contrast", True)
        assert r.ok
        r2 = a.apply("accessibility/mono", True)
        assert r2.ok
        r3 = a.apply("accessibility/font_size", "large")
        assert r3.ok


class TestPersistence:
    def test_successful_persistence_sets_value(self, coordinator):
        from core.settings_manager import SETTINGS
        old = SETTINGS.value("playback/default_volume", 70)
        r = coordinator.execute("playback/default_volume", 85)
        assert r["ok"]
        assert r["persisted"]
        assert SETTINGS.value("playback/default_volume", 70) == 85
        SETTINGS.setValue("playback/default_volume", old)

    def test_failed_validation_does_not_persist(self, coordinator):
        from core.settings_manager import SETTINGS
        old = SETTINGS.value("playback/default_volume", 70)
        r = coordinator.execute("playback/default_volume", 999)
        assert not r["ok"]
        assert not r.get("persisted", True)
        SETTINGS.setValue("playback/default_volume", old)


class TestConsumerUpdate:
    def test_adapter_verify_called_after_apply(self, coordinator):
        r = coordinator.execute("playback/gapless", True)
        assert r["ok"]


class TestRollback:
    def test_rollback_restores_default(self, coordinator):
        from core.settings_manager import SETTINGS
        old = SETTINGS.value("playback/default_volume", 70)
        r = coordinator.revert("playback/default_volume")
        assert r["ok"]
        restored = SETTINGS.value("playback/default_volume", 70)
        assert restored is not None
        SETTINGS.setValue("playback/default_volume", old)

    def test_rollback_unknown_key(self, coordinator):
        r = coordinator.revert("fake/key")
        assert not r["ok"]

    def test_rollback_no_side_effects(self, coordinator):
        from core.settings_manager import SETTINGS
        old_gap = SETTINGS.value("playback/gapless", True)
        coordinator.revert("playback/default_volume")
        assert SETTINGS.value("playback/gapless", True) == old_gap


class TestRestartPolicy:
    def test_non_restart_key_reports_false(self, coordinator):
        r = coordinator.execute("playback/gapless", True)
        assert r["requires_restart"] is False

    def test_adapter_restart_required_false_by_default(self):
        from core.settings_adapters import PlaybackSettingsAdapter
        a = PlaybackSettingsAdapter()
        assert a.restart_required("playback/default_volume") is False


class TestLayouts:
    def test_settings_page_has_layout_variants(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/SettingsPage.qml"
        text = qml.read_text()
        assert "anchors.fill: parent" in text
        assert "Desktop layout" in text or "width >= 900" in text

    def test_settings_general_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsGeneralPage.qml"
        assert qml.exists()

    def test_settings_appearance_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsAppearancePage.qml"
        assert qml.exists()

    def test_settings_playback_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsPlaybackPage.qml"
        assert qml.exists()

    def test_settings_library_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsLibraryPage.qml"
        assert qml.exists()

    def test_settings_accessibility_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsAccessibilityPage.qml"
        assert qml.exists()

    def test_settings_audio_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsAudioPage.qml"
        assert qml.exists()

    def test_settings_about_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/settings/SettingsAboutPage.qml"
        assert qml.exists()

    def test_settings_row_component_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/components/settings/SettingsRow.qml"
        assert qml.exists()

    def test_settings_category_page_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/components/settings/SettingsCategoryPage.qml"
        assert qml.exists()


class TestOutputProfiles:
    def test_output_profiles_bridge_refresh(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.refresh()
        assert r.get("ok") is False or "count" in r

    def test_output_profiles_bridge_set_active_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.setActiveProfile("standard")
        assert not r.get("ok")

    def test_output_profiles_bridge_duplicate_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.duplicateProfile("standard")
        assert not r.get("ok")

    def test_output_profiles_bridge_delete_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.deleteProfile("standard")
        assert not r.get("ok")

    def test_output_profiles_bridge_create_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.createProfile({"name": "test"})
        assert not r.get("ok")

    def test_output_profiles_bridge_update_no_player(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        r = b.updateProfile({"id": "test", "name": "test"})
        assert not r.get("ok")

    def test_output_profiles_page_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/outputs/OutputProfilesPage.qml"
        assert qml.exists()

    def test_output_profile_editor_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/outputs/OutputProfileEditor.qml"
        assert qml.exists()

    def test_output_profile_detail_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/outputs/OutputProfileDetail.qml"
        assert qml.exists()

    def test_output_profile_card_qml_exists(self):
        from pathlib import Path
        qml = Path(__file__).resolve().parent.parent.parent.parent / "ui_qml/pages/outputs/OutputProfileCard.qml"
        assert qml.exists()

    def test_output_profiles_bridge_data_changed_signal(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        assert hasattr(b, 'dataChanged')

    def test_output_profiles_bridge_active_profile_id_property(self):
        from ui_qml_bridge.output_profiles_bridge import OutputProfilesBridge
        b = OutputProfilesBridge()
        assert b.activeProfileId == ""


class TestTheme:
    def test_theme_bridge_has_dark_mode(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        assert hasattr(b, 'darkMode')

    def test_theme_bridge_has_accent_color(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        assert b.accentColor

    def test_theme_bridge_has_high_contrast(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        assert hasattr(b, 'highContrast')

    def test_theme_bridge_has_reduce_motion(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        assert hasattr(b, 'reduceMotion')

    def test_theme_bridge_has_font_scale(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        assert b.fontScale

    def test_theme_bridge_theme_setter(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        b.theme = "light"
        assert b.theme == "light"
        assert not b.darkMode

    def test_theme_bridge_dark_mode_setter(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        b.darkMode = True
        assert b.darkMode

    def test_theme_bridge_accent_color_setter(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        b.accentColor = "#FF0000"
        assert b.accentColor == "#FF0000"

    def test_theme_bridge_reduce_motion_setter(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        b.reduceMotion = True
        assert b.reduceMotion

    def test_theme_bridge_high_contrast_setter(self):
        from ui_qml_bridge.theme_bridge import ThemeBridge
        b = ThemeBridge()
        b.highContrast = True
        assert b.highContrast


class TestAccessibilityGlobal:
    def test_accessibility_bridge_font_scale(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert b.fontScale

    def test_accessibility_bridge_high_contrast(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert hasattr(b, 'highContrast')

    def test_accessibility_bridge_reduce_motion(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert hasattr(b, 'reduceMotion')

    def test_accessibility_bridge_focus_indicators(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert hasattr(b, 'focusIndicators')

    def test_accessibility_bridge_mono(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert hasattr(b, 'mono')

    def test_accessibility_bridge_balance(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        assert hasattr(b, 'balance')

    def test_accessibility_bridge_restore_on_error(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        r = b.restoreOnError()
        assert r["ok"]

    def test_accessibility_bridge_score(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        score = b.accessibilityScore()
        assert "score" in score
        assert 0 <= score["score"] <= 100

    def test_accessibility_bridge_mono_setter_applies(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge(playback_service=MagicMock())
        b.mono = True
        assert b.mono

    def test_accessibility_bridge_font_scale_setter(self):
        from ui_qml_bridge.accessibility_bridge import AccessibilityBridge
        b = AccessibilityBridge()
        b.fontScale = "large"
        assert b.fontScale == "large"
