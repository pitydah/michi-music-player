"""DAC-V35-010 — sysfs snapshot adapter (spec §9/§0G.2).

Lee USB devices y ALSA cards del sysfs y emite DeviceObservation
normalizadas. SOLO observación: nunca decide identidad canónica,
formatos ni playback.

El root del sysfs y el root de /dev son inyectables para tests (un
árbol fake en tmp_path).
"""

from __future__ import annotations

import time
from pathlib import Path

from michi.domain.audio_device import (
    AudioDeviceBinding,
    BindingKind,
    DeviceObservation,
)

SOURCE_SYSFS = "sysfs"


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _usb_physical_path(sysfs_root: Path, device_dir: Path) -> str | None:
    """devpath estable (p.ej. '2-1.3'), nunca el índice de bus."""
    try:
        relative = device_dir.relative_to(sysfs_root / "bus" / "usb" / "devices")
    except ValueError:
        return None
    return str(relative)


def read_usb_devices(
    sysfs_root: Path, *, observed_at_ns: int | None = None
) -> tuple[DeviceObservation, ...]:
    """USB devices observados (VID/PID/serial/strings/path)."""
    devices_dir = sysfs_root / "bus" / "usb" / "devices"
    if not devices_dir.is_dir():
        return ()
    stamp = observed_at_ns if observed_at_ns is not None else time.monotonic_ns()
    observations: list[DeviceObservation] = []
    for device_dir in sorted(devices_dir.iterdir()):
        if not device_dir.is_dir():
            continue
        vendor_id = _read_text(device_dir / "idVendor")
        product_id = _read_text(device_dir / "idProduct")
        if not vendor_id or not product_id:
            continue  # no es un device USB con identidad (hub raíz, etc.)
        observations.append(
            DeviceObservation(
                source=SOURCE_SYSFS,
                observed_at_ns=stamp,
                vendor_id=vendor_id.lower(),
                product_id=product_id.lower(),
                serial=_read_text(device_dir / "serial"),
                manufacturer=_read_text(device_dir / "manufacturer"),
                product=_read_text(device_dir / "product"),
                physical_path=_usb_physical_path(sysfs_root, device_dir),
                binding=None,
            )
        )
    return tuple(observations)


def _usb_ancestor(sysfs_root: Path, card_dir: Path) -> str | None:
    """El USB device del que cuelga la card ALSA, vía el link 'device'."""
    link = card_dir / "device"
    try:
        resolved = link.resolve()
    except OSError:
        return None
    usb_devices = (sysfs_root / "bus" / "usb" / "devices").resolve()
    try:
        relative = resolved.relative_to(usb_devices)
    except ValueError:
        return None
    # el path del device USB es el primer componente tras devices/
    return relative.parts[0] if relative.parts else None


def _playback_pcm(dev_root: Path, card_index: int) -> tuple[int, int] | None:
    """Primer PCM de playback de la card en /dev/snd."""
    for candidate in sorted(dev_root.glob(f"pcmC{card_index}D*p")):
        match = candidate.name
        try:
            pcm_device = int(match[len(f"pcmC{card_index}D") : -1])
        except ValueError:
            continue
        return card_index, pcm_device
    return None


def read_alsa_cards(
    sysfs_root: Path,
    dev_root: Path,
    *,
    observed_at_ns: int | None = None,
) -> tuple[DeviceObservation, ...]:
    """ALSA cards observadas: binding hw:CARD=<id>,DEV=<n> + ancestry USB."""
    cards_dir = sysfs_root / "class" / "sound"
    if not cards_dir.is_dir():
        return ()
    stamp = observed_at_ns if observed_at_ns is not None else time.monotonic_ns()
    observations: list[DeviceObservation] = []
    for card_dir in sorted(cards_dir.glob("card*")):
        if not card_dir.is_dir():
            continue
        try:
            card_index = int(card_dir.name[len("card") :])
        except ValueError:
            continue
        card_id = _read_text(card_dir / "id") or str(card_index)
        pcm = _playback_pcm(dev_root, card_index)
        binding = AudioDeviceBinding(
            kind=BindingKind.ALSA_PCM,
            locator=f"hw:CARD={card_id},DEV={pcm[1] if pcm else 0}",
            generation=0,
            currently_available=True,
            card_index=card_index,
            pcm_device=pcm[1] if pcm else None,
        )
        observations.append(
            DeviceObservation(
                source="alsa",
                observed_at_ns=stamp,
                vendor_id=None,
                product_id=None,
                serial=None,
                manufacturer=None,
                product=card_id,
                physical_path=_usb_ancestor(sysfs_root, card_dir),
                binding=binding,
            )
        )
    return tuple(observations)
