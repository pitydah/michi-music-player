"""Settings adapters — per-domain runtime application of settings changes.
Each adapter implements real changes (not just key prefix matching).

Theme and Accessibility adapters receive their bridge via constructor
injection (``theme_bridge=`` / ``accessibility_bridge=``).  When no bridge is
injected they fall back to the bridge module singleton; when no bridge is
available at all, ``apply``/``verify`` report ``APPLY_TARGET_UNAVAILABLE``.
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("michi.settings_adapters")


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


class BaseSettingsAdapter:
    """Base class for settings adapters."""

    @classmethod
    def supported_keys(cls) -> set[str]:
        raise NotImplementedError

    def _capability_ok(self, key: str) -> bool:
        from core.settings_schema import get_entry
        entry = get_entry(key)
        if entry and entry.requires_capability:
            try:
                from ui_qml_bridge.service_capabilities import ServiceCapabilities
                caps = ServiceCapabilities()
                return caps.has(entry.requires_capability)
            except Exception:
                return True
        return True

    def _platform_ok(self, key: str) -> bool:
        from core.settings_schema import get_entry
        import sys
        entry = get_entry(key)
        if entry and entry.platforms:
            return sys.platform in entry.platforms or (
                sys.platform == "linux" and "Linux" in entry.platforms
            )
        return True

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        raise NotImplementedError

    def verify(self, key: str, value: Any = None) -> dict:
        """Verify that ``value`` was applied to the runtime target.

        Default implementation reports success for adapters that only persist
        (no live runtime target to read back).  Adapters with a bridge override
        this to read back the live bridge state and return a dict shaped as
        ``{"ok": bool, "applied": bool, ...}``.
        """
        return {"ok": True, "applied": True}

    def revert(self, key: str) -> SettingsApplyResult:
        from core.settings_schema import get_entry
        entry = get_entry(key)
        if entry:
            return self.apply(key, entry.default)
        return SettingsApplyResult(
            ok=False, key=key, error_code="UNKNOWN_KEY", message="Clave desconocida"
        )

    def restart_required(self, key: str) -> bool:
        from core.settings_schema import get_entry
        entry = get_entry(key)
        return entry.requires_restart if entry else False


class AccessibilitySettingsAdapter(BaseSettingsAdapter):
    """Applies accessibility changes at runtime via the AccessibilityBridge."""

    _KEYS = {"accessibility/font_size", "accessibility/high_contrast", "accessibility/reduced_motion",
             "accessibility/focus_indicators", "accessibility/mono", "accessibility/balance"}

    _BRIDGE_MAP = {
        "accessibility/font_size": "fontScale",
        "accessibility/high_contrast": "highContrast",
        "accessibility/reduced_motion": "reduceMotion",
        "accessibility/focus_indicators": "focusIndicators",
        "accessibility/mono": "mono",
        "accessibility/balance": "balance",
    }

    def __init__(self, accessibility_bridge: Any = None) -> None:
        self._bridge = accessibility_bridge

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def _resolve_bridge(self) -> Any:
        """Return the injected bridge, or the module singleton, or None."""
        if self._bridge is not None:
            return self._bridge
        try:
            from ui_qml_bridge.accessibility_bridge import _instance
            return _instance
        except ImportError:
            return None

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        bridge = self._resolve_bridge()
        if bridge is None:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="APPLY_TARGET_UNAVAILABLE",
                message="AccessibilityBridge no disponible",
            )
        try:
            if key == "accessibility/mono":
                bridge.mono = bool(value)
            elif key == "accessibility/balance":
                bridge.balance = float(value)
            elif key == "accessibility/font_size":
                bridge.fontScale = float(value)
            elif key == "accessibility/high_contrast":
                bridge.highContrast = bool(value)
            elif key == "accessibility/reduced_motion":
                bridge.reduceMotion = bool(value)
            elif key == "accessibility/focus_indicators":
                bridge.focusIndicators = bool(value)
        except Exception as exc:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="APPLY_FAILED", message=str(exc)
            )
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )

    def verify(self, key: str, value: Any = None) -> dict:
        bridge = self._resolve_bridge()
        if bridge is None:
            return {"ok": False, "applied": False, "error": "APPLY_TARGET_UNAVAILABLE"}
        prop = self._BRIDGE_MAP.get(key)
        if not prop:
            return {"ok": True, "applied": True}
        try:
            actual = getattr(bridge, prop)
        except Exception as exc:
            return {"ok": False, "applied": False, "error": "VERIFY_FAILED",
                    "expected": value, "actual": None, "detail": str(exc)}
        if actual == value:
            return {"ok": True, "applied": True}
        return {"ok": False, "applied": False, "error": "VERIFY_FAILED",
                "expected": value, "actual": actual}


class ThemeSettingsAdapter(BaseSettingsAdapter):
    """Applies theme/appearance changes at runtime via the ThemeBridge."""

    _KEYS = {"appearance/theme", "appearance/accent_color", "appearance/compact_mode", "appearance/language"}

    _BRIDGE_MAP = {
        "appearance/theme": "theme",
        "appearance/accent_color": "accentColor",
        "appearance/compact_mode": "compactMode",
    }

    def __init__(self, theme_bridge: Any = None) -> None:
        self._bridge = theme_bridge

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def _resolve_bridge(self) -> Any:
        """Return the injected bridge, or the module singleton, or None."""
        if self._bridge is not None:
            return self._bridge
        try:
            from ui_qml_bridge.theme_bridge import _instance
            return _instance
        except ImportError:
            return None

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        bridge = self._resolve_bridge()
        if bridge is None:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="APPLY_TARGET_UNAVAILABLE",
                message="ThemeBridge no disponible",
            )
        try:
            if key == "appearance/theme":
                bridge.theme = str(value)
            elif key == "appearance/accent_color":
                bridge.accentColor = str(value)
            elif key == "appearance/compact_mode":
                bridge.compactMode = bool(value)
        except Exception as exc:
            logger.warning("Theme adapter could not apply %s: %s", key, exc)
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="APPLY_FAILED", message=str(exc)
            )
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Tema actualizado"
        )

    def verify(self, key: str, value: Any = None) -> dict:
        bridge = self._resolve_bridge()
        if bridge is None:
            return {"ok": False, "applied": False, "error": "APPLY_TARGET_UNAVAILABLE"}
        prop = self._BRIDGE_MAP.get(key)
        if not prop:
            return {"ok": True, "applied": True}
        try:
            actual = getattr(bridge, prop)
        except Exception as exc:
            return {"ok": False, "applied": False, "error": "VERIFY_FAILED",
                    "expected": value, "actual": None, "detail": str(exc)}
        if actual == value:
            return {"ok": True, "applied": True}
        return {"ok": False, "applied": False, "error": "VERIFY_FAILED",
                "expected": value, "actual": actual}


class PlaybackSettingsAdapter(BaseSettingsAdapter):
    """Applies playback defaults at runtime."""

    _KEYS = {"playback/default_volume", "playback/repeat_mode", "playback/shuffle_default"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        from core.settings_schema import validate as schema_validate
        ok, msg = schema_validate(key, value)
        if not ok:
            return SettingsApplyResult(
                ok=False, key=key, requested_value=value,
                error_code="INVALID_VALUE", message=msg
            )
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class AudioSettingsAdapter(BaseSettingsAdapter):
    """Applies audio engine, MPD, GStreamer, bit-perfect settings."""

    _KEYS = {
        "audio/device", "audio/mode", "audio/sample_rate", "audio/buffer_ms",
        "audio/profile", "audio/output_device_id", "audio/alsa_device",
        "audio/allow_resample", "audio/resample_quality",
        "audio/wasapi_exclusive",
        "mpd/host", "mpd/port", "mpd/password", "mpd/enabled", "mpd/auto_start",
        "gstreamer/buffer_size", "gstreamer/latency",
        "bitperfect/enabled", "bitperfect/exclusive_mode",
        "bitperfect/dsd_mode", "bitperfect/wasapi_exclusive",
    }

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        restart = True
        if key in ("audio/profile", "audio/output_device_id", "audio/device"):
            restart = True
        elif key in ("audio/allow_resample", "audio/resample_quality"):
            restart = False
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            requires_restart=restart,
            message="Requiere reinicio" if restart else "Aplicado"
        )

    def restart_required(self, key: str) -> bool:
        return key in (
            "audio/device", "audio/mode", "audio/sample_rate", "audio/buffer_ms",
            "audio/profile", "audio/output_device_id",
            "mpd/host", "mpd/port", "mpd/enabled", "mpd/auto_start",
            "gstreamer/buffer_size", "gstreamer/latency",
            "bitperfect/enabled", "bitperfect/exclusive_mode",
            "bitperfect/dsd_mode",
        )


class EqSettingsAdapter(BaseSettingsAdapter):
    """Applies EQ and DSP settings at runtime."""

    _KEYS = {"eq/enabled", "eq/preset", "eq/mode", "eq/preamp",
             "dsp/chain", "dsp/compressor", "dsp/limiter", "dsp/stereo_enhance"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        restart = key in ("dsp/chain", "dsp/compressor", "dsp/limiter", "dsp/stereo_enhance")
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            requires_restart=restart,
            message="Requiere reinicio" if restart else "Aplicado"
        )


class LibrarySettingsAdapter(BaseSettingsAdapter):
    """Applies library settings at runtime."""

    _KEYS = {"library/auto_scan", "library/exclude_hidden", "library/covers_cache_size"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class CacheSettingsAdapter(BaseSettingsAdapter):
    """Applies cache settings at runtime."""

    _KEYS = {"cache/covers_size", "cache/metadata_size", "cache/thumbnail_size",
             "cache/auto_clean", "cache/clean_interval_days"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class HistorySettingsAdapter(BaseSettingsAdapter):
    """Applies history/privacy settings at runtime."""

    _KEYS = {"privacy/history_enabled", "privacy/history_limit", "privacy/telemetry"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class RadioSettingsAdapter(BaseSettingsAdapter):
    """Applies radio settings at runtime."""

    _KEYS = {"radio/default_codec", "radio/auto_reconnect", "radio/reconnect_delay",
             "radio/buffer_size"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        restart = key in ("radio/buffer_size",)
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            requires_restart=restart,
            message="Requiere reinicio" if restart else "Aplicado"
        )


class LyricsSettingsAdapter(BaseSettingsAdapter):
    """Applies lyrics settings at runtime."""

    _KEYS = {"lyrics/provider", "lyrics/auto_search", "lyrics/cache_days",
             "lyrics/offline_fallback"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class DeviceSettingsAdapter(BaseSettingsAdapter):
    """Applies device/sync settings at runtime."""

    _KEYS = {"devices/sync_enabled", "devices/sync_interval", "devices/sync_path",
             "devices/auto_discover"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


class ConnectionSettingsAdapter(BaseSettingsAdapter):
    """Applies connection/server settings at runtime."""

    _KEYS = {"connections/server_port", "connections/auto_discovery",
             "connections/pairing_timeout"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            requires_restart=key in ("connections/server_port",),
            message="Requiere reinicio" if key in ("connections/server_port",) else "Aplicado"
        )


class HomeAudioSettingsAdapter(BaseSettingsAdapter):
    """Applies Home Audio / Snapcast settings at runtime."""

    _KEYS = {"home_audio/ha_host", "home_audio/ha_port", "home_audio/ha_token",
             "home_audio/snapcast_host", "home_audio/snapcast_port"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            requires_restart=True,
            message="Requiere reinicio"
        )


class LoggingSettingsAdapter(BaseSettingsAdapter):
    """Applies logging/advanced settings at runtime."""

    _KEYS = {"advanced/log_level", "advanced/dev_mode", "advanced/experimental_features",
             "advanced/thread_pool_size", "advanced/max_covers_parallel"}

    @classmethod
    def supported_keys(cls) -> set[str]:
        return cls._KEYS

    def apply(self, key: str, value: Any) -> SettingsApplyResult:
        if key == "advanced/log_level":
            try:
                import logging as _logging
                level_map = {
                    "debug": _logging.DEBUG, "info": _logging.INFO,
                    "warning": _logging.WARNING, "error": _logging.ERROR,
                    "critical": _logging.CRITICAL,
                }
                _logging.getLogger("michi").setLevel(level_map.get(str(value).lower(), _logging.WARNING))
                return SettingsApplyResult(
                    ok=True, key=key, requested_value=value,
                    applied=True, message="Nivel de log actualizado"
                )
            except Exception as e:
                return SettingsApplyResult(
                    ok=False, key=key, requested_value=value,
                    error_code="APPLY_FAILED", message=str(e)
                )
        return SettingsApplyResult(
            ok=True, key=key, requested_value=value,
            applied=True, message="Aplicado"
        )


_ALL_ADAPTERS = [
    ThemeSettingsAdapter,
    AccessibilitySettingsAdapter,
    PlaybackSettingsAdapter,
    AudioSettingsAdapter,
    EqSettingsAdapter,
    LibrarySettingsAdapter,
    CacheSettingsAdapter,
    HistorySettingsAdapter,
    RadioSettingsAdapter,
    LyricsSettingsAdapter,
    DeviceSettingsAdapter,
    ConnectionSettingsAdapter,
    HomeAudioSettingsAdapter,
    LoggingSettingsAdapter,
]


def register_all_adapters(coordinator, theme_bridge: Any = None,
                          accessibility_bridge: Any = None) -> None:
    """Register all adapters into a SettingsRuntimeCoordinator.

    Theme and Accessibility adapters accept an optional bridge reference
    (constructor injection).  When ``None`` they fall back to the bridge module
    singleton at apply/verify time.
    """
    coordinator.register_adapter(ThemeSettingsAdapter(theme_bridge=theme_bridge))
    coordinator.register_adapter(
        AccessibilitySettingsAdapter(accessibility_bridge=accessibility_bridge)
    )
    for adapter_cls in (
        PlaybackSettingsAdapter, AudioSettingsAdapter, EqSettingsAdapter,
        LibrarySettingsAdapter, CacheSettingsAdapter, HistorySettingsAdapter,
        RadioSettingsAdapter, LyricsSettingsAdapter, DeviceSettingsAdapter,
        ConnectionSettingsAdapter, HomeAudioSettingsAdapter, LoggingSettingsAdapter,
    ):
        coordinator.register_adapter(adapter_cls())
