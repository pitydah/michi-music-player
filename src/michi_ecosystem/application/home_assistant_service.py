"""Home Assistant orchestration service (E11.5-D)."""

from __future__ import annotations

import contextlib
import threading
from collections.abc import Callable
from typing import Any

from michi_ecosystem.domain.device_registry import DeviceDescriptor
from michi_ecosystem.domain.home_assistant import HomeAssistantConnectionState
from michi_ecosystem.ports.home_automation import (
    HomeAutomationConfiguration,
    HomeAutomationPort,
    HomeAutomationSettingsPort,
)


class HomeAssistantService:
    """Opt-in façade; Michi remains source-of-truth when HA is unavailable.

    Registry updates and broker operations may arrive on different threads
    (Qt worker, MQTT callback, discovery refresh). A small re-entrant lock keeps
    the enabled/device/home projection coherent without making Home Assistant
    an authority over the underlying Michi state.
    """

    def __init__(
        self,
        adapter: HomeAutomationPort,
        *,
        settings: HomeAutomationSettingsPort | None = None,
        enabled: bool = False,
        privileged_authorizer: Callable[[], bool] | None = None,
    ) -> None:
        self._adapter = adapter
        self._settings = settings
        self._privileged_authorizer = privileged_authorizer
        self._enabled = False
        self._devices: dict[str, DeviceDescriptor] = {}
        self._home_summary: dict[str, Any] | None = None
        self._state_listener: Callable[[], None] | None = None
        self._last_connect_failed = False
        self._lock = threading.RLock()
        if enabled:
            self.enable()

    @property
    def configurable(self) -> bool:
        return self._settings is not None

    def configuration(self) -> HomeAutomationConfiguration:
        if self._settings is None:
            return HomeAutomationConfiguration()
        return self._settings.configuration()

    def configure(
        self,
        *,
        broker: str,
        port: int,
        tls: bool,
        username: str,
        password: str | None,
        auto_discovery: bool,
        publish_devices: bool,
        diagnostics: bool,
    ) -> None:
        self._require_owner()
        if self._settings is None:
            raise RuntimeError("HOME_AUTOMATION_SETTINGS_UNAVAILABLE")
        broker = str(broker).strip()
        if not broker:
            raise ValueError("MQTT broker must not be empty")
        port = int(port)
        if port < 1 or port > 65535:
            raise ValueError("MQTT port must be between 1 and 65535")
        with self._lock:
            if self._enabled:
                raise RuntimeError("HOME_AUTOMATION_DISABLE_BEFORE_CONFIGURE")
        # Secret is write-only: never cache it in the service or return it.
        self._settings.configure(
            broker=broker,
            port=port,
            tls=bool(tls),
            username=str(username).strip(),
            password=password if password else None,
            auto_discovery=bool(auto_discovery),
            publish_devices=bool(publish_devices),
            diagnostics=bool(diagnostics),
        )
        with self._lock:
            self._last_connect_failed = False
        self._notify_state()

    @property
    def enabled(self) -> bool:
        with self._lock:
            return self._enabled

    # ── connectivity (E12.1) ────────────────────────────────────────────
    # Activation is not connectivity: a configured but disabled integration is
    # CONFIGURED, and an enabled adapter only reports CONNECTED when its
    # transport actually observed the link.

    @property
    def connection_state(self) -> HomeAssistantConnectionState:
        with self._lock:
            enabled = self._enabled
        if not enabled:
            with self._lock:
                connect_failed = self._last_connect_failed
            if connect_failed:
                # The last attempt failed; the integration is OFF but the UI
                # must not look like a clean disabled state.
                return HomeAssistantConnectionState.ERROR
            return (
                HomeAssistantConnectionState.CONFIGURED
                if self.configuration().broker
                else HomeAssistantConnectionState.DISABLED
            )
        provider = getattr(self._adapter, "connection_state", None)
        if not callable(provider):
            # Legacy adapter: never fabricate "connected" from activation.
            return HomeAssistantConnectionState.UNKNOWN
        try:
            state = provider()
        except Exception:
            return HomeAssistantConnectionState.ERROR
        return (
            state
            if isinstance(state, HomeAssistantConnectionState)
            else HomeAssistantConnectionState.UNKNOWN
        )

    @property
    def last_publish_ok_ms(self) -> float | None:
        provider = getattr(self._adapter, "last_publish_ok_ms", None)
        try:
            value = provider() if callable(provider) else None
        except Exception:
            return None
        return value if isinstance(value, (int, float)) else None

    @property
    def last_error_code(self) -> str:
        provider = getattr(self._adapter, "last_error_code", None)
        try:
            value = provider() if callable(provider) else ""
        except Exception:
            return "ADAPTER_ERROR"
        return value if isinstance(value, str) else ""

    def set_state_listener(self, listener: Callable[[], None] | None) -> None:
        """Forward transport connectivity events (may fire off the GUI thread)."""
        with self._lock:
            self._state_listener = listener
        hook = getattr(self._adapter, "set_state_listener", None)
        if callable(hook):
            hook(self._notify_state)

    def _notify_state(self, _state: object = None) -> None:
        with self._lock:
            listener = self._state_listener
        if listener is not None:
            with contextlib.suppress(Exception):
                listener()

    def enable(self) -> None:
        self._require_owner()
        with self._lock:
            if self._enabled:
                return
        # Broker I/O happens outside the service lock; a failed start must be
        # observable as ERROR instead of a clean disabled state.
        try:
            self._adapter.start()
        except Exception:
            with self._lock:
                self._last_connect_failed = True
            self._notify_state()
            raise
        with self._lock:
            self._enabled = True
            self._last_connect_failed = False
            devices = tuple(self._devices.values())
            home_summary = dict(self._home_summary) if self._home_summary else None
        # Publish outside the service lock: adapters may invoke transport hooks.
        # If initial publication fails, roll back to a clean OFF state rather
        # than leaving the integration half-enabled.
        try:
            for device in devices:
                self._adapter.publish_device(device)
            if home_summary is not None:
                self._adapter.publish_home(**home_summary)
        except Exception:
            try:
                self._adapter.stop()
            finally:
                with self._lock:
                    self._enabled = False
                    self._last_connect_failed = True
            self._notify_state()
            raise
        self._notify_state()

    def disable(self) -> None:
        with self._lock:
            if not self._enabled:
                return
            try:
                self._adapter.stop()
            finally:
                self._enabled = False
                self._last_connect_failed = False
        self._notify_state()

    def shutdown(self) -> None:
        """Internal teardown path: stop the adapter without user authorization.

        Only the runtime lifecycle calls this; administrative disable() keeps
        the OWNER gate. Security is never relaxed for user operations.
        """
        with self._lock:
            if not self._enabled:
                return
            try:
                self._adapter.stop()
            finally:
                self._enabled = False
                self._last_connect_failed = False

    def _require_owner(self) -> None:
        if (
            self._privileged_authorizer is not None
            and not self._privileged_authorizer()
        ):
            raise PermissionError("HOME_AUTOMATION_OWNER_REQUIRED")

    def republish(self) -> None:
        self._require_owner()
        with self._lock:
            enabled = self._enabled
        if enabled:
            self._adapter.republish()

    def sync_devices(self, devices: tuple[DeviceDescriptor, ...]) -> None:
        exposable = {
            device.canonical_id: device
            for device in devices
            if device.home_assistant_allowed
        }
        with self._lock:
            removed = set(self._devices) - set(exposable)
            changed = {
                key: device
                for key, device in exposable.items()
                if self._devices.get(key) != device
            }
            enabled = self._enabled
            self._devices = exposable
        if enabled:
            for canonical_id in removed:
                self._adapter.remove_device(canonical_id)
            for device in changed.values():
                self._adapter.publish_device(device)

    def publish_state(self, canonical_id: str, state: dict[str, Any]) -> None:
        with self._lock:
            allowed = self._enabled and canonical_id in self._devices
        if allowed:
            self._adapter.publish_state(canonical_id, state)

    def publish_home_summary(
        self, *, home_id: str, name: str, device_count: int, healthy: bool
    ) -> None:
        summary = {
            "home_id": home_id,
            "name": name,
            "device_count": device_count,
            "healthy": healthy,
        }
        with self._lock:
            self._home_summary = summary
            enabled = self._enabled
        if enabled:
            self._adapter.publish_home(**summary)

    def clear_home_summary(self) -> None:
        """Clear previous Home identity and retained MQTT discovery on teardown."""
        with self._lock:
            had_home = self._home_summary is not None
            self._home_summary = None
        if had_home:
            # Also clear the adapter's in-memory snapshot when disabled;
            # otherwise the next start() can resurrect an obsolete Home.
            self._adapter.clear_home()
