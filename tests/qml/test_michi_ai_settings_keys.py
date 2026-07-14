"""Test MichiAIBridge — uses correct Settings Schema keys, never theme/mode or audio/volume."""
from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from ui_qml_bridge.michi_ai_bridge import MichiAIBridge


@pytest.fixture
def bridge():
    settings = MagicMock()
    settings.set_.return_value = {"ok": True}
    return MichiAIBridge(
        settings_service=settings,
    )


class TestSettingsKeys:
    def test_volume_uses_playback_default_volume(self, bridge):
        bridge._set_status("idle")
        intent = bridge._parse_intent("cambiar ajuste volumen a 80")
        assert intent is not None
        assert intent["entities"]["setting_key"] == "playback/default_volume"

    def test_volume_key_not_audio_volume(self, bridge):
        bridge._set_status("idle")
        intent = bridge._parse_intent("cambiar ajuste volumen a 50")
        assert intent is not None
        assert intent["entities"]["setting_key"] != "audio/volume"

    def test_theme_uses_appearance_theme(self, bridge):
        bridge._set_status("idle")
        intent = bridge._parse_intent("cambiar ajuste tema oscuro")
        assert intent is not None
        assert intent["entities"]["setting_key"] == "appearance/theme"

    def test_theme_key_not_theme_mode(self, bridge):
        intent = bridge._parse_intent("cambiar ajuste tema oscuro")
        assert intent is not None
        assert intent["entities"]["setting_key"] != "theme/mode"

    def test_setting_value_is_correct_type(self, bridge):
        bridge._set_status("idle")
        intent = bridge._parse_intent("cambiar ajuste volumen a 80")
        assert intent is not None
        assert intent["entities"]["setting_value"] == 80
        assert intent["entities"]["setting_key"] == "playback/default_volume"

    def test_theme_value_is_string(self, bridge):
        intent = bridge._parse_intent("cambiar ajuste tema oscuro")
        assert intent is not None
        assert isinstance(intent["entities"]["setting_value"], str)

    def test_setting_change_requires_confirmation(self, bridge):
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "awaiting_confirmation"

    def test_setting_change_confirm_executes(self, bridge):
        bridge.sendMessage("cambiar ajuste volumen a 80")
        assert bridge.status == "awaiting_confirmation"
        bridge.sendMessage("sí")
        assert bridge.status == "completed"
        bridge._settings.set_.assert_called_once()

    def test_no_audio_volume_key_leaked(self, bridge):
        intent = bridge._parse_intent("cambiar ajuste volumen a 42")
        assert intent is not None
        assert intent["entities"]["setting_key"] != "audio/volume"
