"""SettingsRuntimeCoordinator — validates, applies, rolls back settings at runtime."""
from __future__ import annotations

import logging
from typing import Any

from core.settings_schema import get_entry, validate
from core.settings_manager import SETTINGS

logger = logging.getLogger("michi.settings_runtime")


class SettingsApplyResult:
    def __init__(self, ok: bool = True, key: str = "", value: Any = None,
                 previous_value: Any = None, applied: bool = False,
                 requires_restart: bool = False, error_code: str = "",
                 message: str = "", affected_service: str = ""):
        self.ok = ok
        self.key = key
        self.value = value
        self.previous_value = previous_value
        self.applied = applied
        self.requires_restart = requires_restart
        self.error_code = error_code
        self.message = message
        self.affected_service = affected_service

    def to_dict(self) -> dict:
        return {
            "ok": self.ok, "key": self.key, "value": self.value,
            "previous_value": self.previous_value, "applied": self.applied,
            "requires_restart": self.requires_restart,
            "error_code": self.error_code, "message": self.message,
            "affected_service": self.affected_service,
        }


class SettingsRuntimeCoordinator:
    def __init__(self, player_service=None, worker_manager=None):
        self._player = player_service
        self._wm = worker_manager

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        entry = get_entry(key)
        if not entry:
            return SettingsApplyResult(ok=False, error_code="UNKNOWN_KEY",
                                       message="Clave desconocida")

        ok, msg = validate(key, value)
        if not ok:
            return SettingsApplyResult(ok=False, error_code="INVALID_VALUE", message=msg,
                                       key=key, value=value)

        previous = SETTINGS.value(key, entry.default)
        SETTINGS.setValue(key, value)
        SETTINGS.sync()

        result = SettingsApplyResult(key=key, value=value, previous_value=previous,
                                     requires_restart=entry.requires_restart)

        # Apply hot if possible
        try:
            applied = self._apply_hot(key, value)
            if applied:
                result.applied = True
                result.message = "Aplicado"
            else:
                result.applied = False
                result.message = "Requiere reinicio"
        except Exception as e:
            logger.exception("Hot apply failed for %s, rolling back", key)
            SETTINGS.setValue(key, previous)
            SETTINGS.sync()
            return SettingsApplyResult(ok=False, error_code="APPLY_FAILED",
                                       message=str(e), key=key, value=value,
                                       previous_value=previous)

        return result

    def _apply_hot(self, key: str, value: Any) -> bool:
        """Apply a setting change without restart. Returns True if applied."""
        if key.startswith("general/"):
            return True
        if key.startswith("appearance/"):
            return True
        if key.startswith("accessibility/"):
            return True
        if key.startswith("privacy/"):
            return True
        if key.startswith("cache/"):
            return True
        if key == "playback/default_volume" and self._player:
            if hasattr(self._player, 'set_volume'):
                self._player.set_volume(int(value))
            return True
        if key == "playback/repeat_mode" and self._player:
            if hasattr(self._player, 'set_repeat_mode'):
                self._player.set_repeat_mode(str(value))
            return True
        if key == "playback/shuffle_default" and self._player:
            if hasattr(self._player, 'set_shuffle'):
                self._player.set_shuffle(bool(value))
            return True
        if key.startswith("audio/") or key.startswith("mpd/"):
            return False  # requires restart
        if key.startswith("gstreamer/"):
            return False
        if key.startswith("bitperfect/"):
            return False
        if key.startswith("eq_"):
            return False
        if key.startswith("dsp/"):
            return False
        if key.startswith("buffer/"):
            return False
        if key.startswith("gapless/"):
            return False
        if key.startswith("replaygain/"):
            return False
        if key.startswith("network/"):
            return True
        if key.startswith("radio_"):
            return True
        if key.startswith("lyrics_"):
            return True
        if key.startswith("devices_"):
            return False
        if key.startswith("connections_"):
            return False
        if key.startswith("home_audio_"):
            return False
        if key.startswith("advanced/"):
            return key == "advanced/log_level"
        return True
