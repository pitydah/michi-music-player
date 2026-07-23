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
    """Describe the outcome of one transactional settings change."""

    def __init__(self, ok: bool = True, key: str = "", requested_value: Any = None,
                 previous_value: Any = None, persisted: bool = False,
                 applied: bool = False, requires_restart: bool = False,
                 error_code: str = "", message: str = "",
                  affected_service: str = "") -> None:
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

    def to_dict(self) -> dict[str, Any]:
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
    """Validate, apply, persist, and roll back runtime settings."""

    def __init__(self, player_service: Any = None, queue_service: Any = None,
                 worker_manager: Any = None) -> None:
        self._player = player_service
        self._queue = queue_service
        self._wm = worker_manager
        self._adapters = []

    def register_adapter(self, adapter: Any) -> None:
        self._adapters.append(adapter)

    def execute(self, key: str, value: Any) -> dict[str, Any]:
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
        adapter = self.adapter_for(key)
        affected_service = adapter.__class__.__name__ if adapter else ""

        if adapter:
            try:
                adapter_result = adapter.apply(key, value)
                if hasattr(adapter_result, "ok") and not adapter_result.ok:
                    return SettingsApplyResult(
                        ok=False,
                        key=key,
                        requested_value=value,
                        previous_value=previous,
                        error_code=adapter_result.error_code or "APPLY_FAILED",
                        message=adapter_result.message or "No se pudo aplicar el ajuste",
                        affected_service=affected_service,
                    ).to_dict()
            except Exception as e:
                logger.exception("Service change failed for %s, reverting", key)
                return SettingsApplyResult(
                    ok=False, key=key, requested_value=value,
                    previous_value=previous, error_code="APPLY_FAILED",
                    message=str(e), affected_service=affected_service
                ).to_dict()

        try:
            SETTINGS.setValue(key, value)
            SETTINGS.sync()
            status = SETTINGS.status()
            raw_status = getattr(status, "value", status)
            status_code = raw_status if isinstance(raw_status, int) else 0
            if status_code != 0:
                raise RuntimeError(f"QSettings status {status_code}")
            persisted = True
        except (OSError, RuntimeError) as exc:
            SETTINGS.setValue(key, previous)
            SETTINGS.sync()
            if adapter:
                try:
                    adapter.apply(key, previous)
                except Exception:
                    logger.exception("Runtime rollback failed after persistence error for %s", key)
            return SettingsApplyResult(
                ok=False,
                key=key,
                requested_value=value,
                previous_value=previous,
                persisted=False,
                error_code="PERSIST_FAILED",
                message=str(exc),
                affected_service=affected_service,
            ).to_dict()

        restart = entry.requires_restart
        if adapter:
            try:
                restart = adapter.restart_required(key)
            except Exception:
                logger.debug("Restart policy lookup failed for %s", key, exc_info=True)

        result = SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            previous_value=previous, persisted=persisted,
            requires_restart=restart, affected_service=affected_service
        )

        if adapter:
            verified = False
            if not restart:
                try:
                    verified = bool(adapter.verify(key))
                except Exception:
                    logger.exception("Settings verification failed for %s", key)
            if not restart and verified:
                result.applied = True
                result.message = "Aplicado"
            else:
                result.message = "Requiere reinicio" if restart else "No aplicado"
                if not restart:
                    result.ok = False
                    result.error_code = "VERIFY_FAILED"
        else:
            result.message = "Sin adapter — sólo persistido"

        if result.applied and not restart:
            self._emit_change(key, value)

        return result.to_dict()

    def revert(self, key: str) -> dict[str, Any]:
        """Revert a key to its previous value (before last change)."""
        entry = get_entry(key)
        if not entry:
            return SettingsApplyResult(
                ok=False, key=key, error_code="UNKNOWN_KEY", message="Clave desconocida"
            ).to_dict()

        previous = SETTINGS.value(key, entry.default)
        return self.execute(key, previous)

    def _emit_change(self, key: str, value: Any) -> None:
        if key.startswith("playback/") and (self._player or self._queue):
            self._apply_playback_hot(key, value)
        elif key == "advanced/log_level":
            self._apply_log_level(value)

    def _apply_playback_hot(self, key: str, value: Any) -> None:
        if key == "playback/default_volume" and hasattr(self._player, "set_volume"):
            self._player.set_volume(int(value))
        elif key == "playback/repeat_mode" and self._queue:
            self._queue.set_repeat(str(value))
        elif key == "playback/shuffle_default" and self._queue:
            self._queue.set_shuffle(bool(value))

    def _apply_log_level(self, value: Any) -> None:
        try:
            level_map = {
                "debug": logging.DEBUG, "info": logging.INFO,
                "warning": logging.WARNING, "error": logging.ERROR,
                "critical": logging.CRITICAL,
            }
            logging.getLogger("michi").setLevel(
                level_map.get(str(value).lower(), logging.WARNING)
            )
        except Exception:
            logger.exception("Unable to apply log level %r", value)

    def adapter_for(self, key: str) -> Any | None:
        for adapter in self._adapters:
            if key in adapter.supported_keys():
                return adapter
        return None

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        """Legacy alias for backward compatibility."""
        result_dict = self.execute(key, value)
        return SettingsApplyResult(
            ok=result_dict.get("ok", False),
            key=result_dict.get("key", key),
            requested_value=result_dict.get("requested_value", value),
            previous_value=result_dict.get("previous_value"),
            persisted=result_dict.get("persisted", False),
            applied=result_dict.get("applied", False),
            requires_restart=result_dict.get("requires_restart", False),
            error_code=result_dict.get("error_code", ""),
            message=result_dict.get("message", ""),
            affected_service=result_dict.get("affected_service", ""),
        )
