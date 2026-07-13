"""SettingsRuntimeCoordinator — validates, applies, rolls back settings at runtime.
Owns the transaction lifecycle: validate → capture previous → apply service change → persist → emit.
"""
from __future__ import annotations

import logging
from typing import Any

from core.settings_schema import get_entry, validate
from core.settings_manager import SETTINGS

logger = logging.getLogger("michi.settings_runtime")


class SettingsApplyResult:
    def __init__(self, ok: bool = True, key: str = "", requested_value: Any = None,
                 previous_value: Any = None, persisted: bool = False,
                 applied: bool = False, requires_restart: bool = False,
                 error_code: str = "", message: str = "",
                 affected_service: str = ""):
        self.ok = ok
        self.key = key
        self.requested_value = requested_value
        self.previous_value = previous_value
        self.persisted = persisted
        self.applied = applied
        self.requires_restart = requires_restart
        self.error_code = error_code
        self.message = message
        self.affected_service = affected_service

    def to_dict(self) -> dict:
        return {
            "ok": self.ok,
            "key": self.key,
            "requested_value": self.requested_value,
            "previous_value": self.previous_value,
            "persisted": self.persisted,
            "applied": self.applied,
            "requires_restart": self.requires_restart,
            "error_code": self.error_code,
            "message": self.message,
            "affected_service": self.affected_service,
        }


class SettingsRuntimeCoordinator:
    def __init__(self, player_service=None, worker_manager=None):
        self._player = player_service
        self._wm = worker_manager
        self._adapters = []

    def register_adapter(self, adapter):
        self._adapters.append(adapter)

    def execute(self, key: str, value: Any) -> dict:
        """Full transaction: validate → capture previous → apply service change → persist → emit."""
        entry = get_entry(key)
        if not entry:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="UNKNOWN_KEY", message="Clave desconocida"
            ).to_dict()

        ok, msg = validate(key, value)
        if not ok:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="INVALID_VALUE", message=msg
            ).to_dict()

        previous = SETTINGS.value(key, entry.default)
        adapter = self._find_adapter(key)
        affected_service = adapter.__class__.__name__ if adapter else ""

        if adapter:
            try:
                adapter.apply(key, value)
            except Exception as e:
                logger.exception("Service change failed for %s, reverting", key)
                return SettingsApplyResult(
                    ok=False, key=key, requested_value=value,
                    previous_value=previous, error_code="APPLY_FAILED",
                    message=str(e), affected_service=affected_service
                ).to_dict()

        SETTINGS.setValue(key, value)
        SETTINGS.sync()
        persisted = True

        restart = entry.requires_restart
        if adapter:
            try:
                restart = adapter.restart_required(key)
            except Exception:
                _ = None

        result = SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            previous_value=previous, persisted=persisted,
            requires_restart=restart, affected_service=affected_service
        )

        if adapter:
            if not restart and adapter.verify(key):
                result.applied = True
                result.message = "Aplicado"
            else:
                result.message = "Requiere reinicio" if restart else "No aplicado"
        else:
            result.applied = True
            result.message = "Aplicado"

        if result.applied and not restart:
            self._emit_change(key, value)

        return result.to_dict()

    def revert(self, key: str) -> dict:
        """Revert a key to its previous value (before last change)."""
        entry = get_entry(key)
        if not entry:
            return SettingsApplyResult(
                ok=False, key=key, error_code="UNKNOWN_KEY", message="Clave desconocida"
            ).to_dict()

        previous = SETTINGS.value(key, entry.default)
        return self.execute(key, previous)

    def _find_adapter(self, key: str):
        for adapter in self._adapters:
            if key in adapter.supported_keys():
                return adapter
        return None

    def _emit_change(self, key: str, value: Any):
        if key.startswith("playback/") and self._player:
            self._apply_playback_hot(key, value)
        elif key == "advanced/log_level":
            self._apply_log_level(value)

    def _apply_playback_hot(self, key: str, value: Any):
        if key == "playback/default_volume" and hasattr(self._player, "set_volume"):
            self._player.set_volume(int(value))
        elif key == "playback/repeat_mode" and hasattr(self._player, "set_repeat_mode"):
            self._player.set_repeat_mode(str(value))
        elif key == "playback/shuffle_default" and hasattr(self._player, "set_shuffle"):
            self._player.set_shuffle(bool(value))

    def _apply_log_level(self, value: Any):
        try:
            import logging as _logging
            level_map = {
                "debug": _logging.DEBUG, "info": _logging.INFO,
                "warning": _logging.WARNING, "error": _logging.ERROR,
                "critical": _logging.CRITICAL,
            }
            _logging.getLogger("michi").setLevel(level_map.get(str(value).lower(), _logging.WARNING))
        except Exception:
            pass

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        """Legacy alias for backward compatibility."""
        result_dict = self.execute(key, value)
        return SettingsApplyResult(
            ok=result_dict.get("ok", False),
            key=result_dict.get("key", key),
            value=result_dict.get("requested_value", value),
            previous_value=result_dict.get("previous_value"),
            applied=result_dict.get("applied", False),
            requires_restart=result_dict.get("requires_restart", False),
            error_code=result_dict.get("error_code", ""),
            message=result_dict.get("message", ""),
            affected_service=result_dict.get("affected_service", ""),
        )
