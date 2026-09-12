"""DAC-V35-010 — udev hotplug observer (spec §0G.2/§400).

`pyudev monitor -> normalized DeviceObservation -> AudioDeviceRegistry`.

pyudev es SOLO observación: nunca decide identidad canónica, output
policy, formatos soportados ni playback. El observer re-escanea
USB+ALSA en cada evento (la correlación necesita ambos lados) y delega
la decisión al registry.
"""

from __future__ import annotations

import logging
from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.infrastructure.audio_devices.sysfs_snapshot import (
    read_alsa_cards,
    read_usb_devices,
)

logger = logging.getLogger(__name__)

DEFAULT_SYSFS_ROOT = Path("/sys")


class UdevObserver:
    """Observa hotplug USB/ALSA y alimenta el registry canónico."""

    def __init__(
        self,
        registry: AudioDeviceRegistry,
        *,
        sysfs_root: Path = DEFAULT_SYSFS_ROOT,
        context: object | None = None,
    ) -> None:
        self._registry = registry
        self._sysfs_root = sysfs_root
        self._context = context
        self._monitors: list[object] = []

    def start(self) -> None:
        """Arranca los monitores netlink (usb + sound). Runtime real."""
        import pyudev  # import local: el CI/headless no necesita udev

        context = self._context if self._context is not None else pyudev.Context()
        self._context = context
        for subsystem in ("usb", "sound"):
            monitor = pyudev.Monitor.from_netlink(context)
            monitor.filter_by(subsystem=subsystem)
            monitor.start()
            self._monitors.append(monitor)
        self.rescan()

    def stop(self) -> None:
        for monitor in self._monitors:
            try:
                monitor.stop()
            except Exception:  # pragma: no cover - monitor ya cerrado
                logger.debug("monitor stop falló", exc_info=True)
        self._monitors.clear()

    def poll(self, timeout: float | None = 0.0) -> int:
        """Procesa eventos pendientes (usado por el loop del player)."""
        processed = 0
        for monitor in self._monitors:
            device = monitor.poll(timeout=timeout)
            while device is not None:
                self.handle_event(
                    action=device.action,
                    subsystem=device.subsystem,
                    sys_name=device.sys_name,
                )
                processed += 1
                device = monitor.poll(timeout=0.0)
        return processed

    def handle_event(self, *, action: str, subsystem: str, sys_name: str) -> None:
        """Normaliza un evento udev y lo aplica al registry.

        Testeable sin socket netlink real.
        """
        if action == "remove":
            self._registry.handle_removed(sys_name)
        self.rescan()

    def rescan(self) -> None:
        """Re-scan completo: USB + ALSA en una sola decisión coherente."""
        observations = read_usb_devices(self._sysfs_root) + read_alsa_cards(
            self._sysfs_root
        )
        if observations:
            self._registry.ingest(observations)
