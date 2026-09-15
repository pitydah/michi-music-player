"""DAC-V35-010/040-C01 — sysfs snapshot adapter (spec §9/§0G.2).

Topología Linux REAL:

    /sys/devices/pci.../usb2/2-1/            <- device USB (idVendor...)
    /sys/devices/pci.../usb2/2-1/2-1:1.0/    <- interface
    .../2-1:1.0/sound/card1/                 <- card ALSA
    /sys/bus/usb/devices/2-1 -> symlink al device USB
    /sys/class/sound/card1 -> symlink a la card
    /sys/class/sound/pcmC1D0p -> symlink al PCM de playback

El descubrimiento de PCMs de playback se hace por la sound class del
sysfs (nunca por /dev). Cero-o-más bindings: una card sin PCM de
playback REAL produce CERO bindings; DEV nunca se sintetiza.

SOLO observación: nunca decide identidad canónica, formatos ni playback.
"""

from __future__ import annotations

import hashlib
import re
import time
from pathlib import Path

from michi.domain.audio_device import (
    AudioDeviceBinding,
    BindingKind,
    DeviceObservation,
)

SOURCE_SYSFS = "sysfs"

_PCM_PLAYBACK_RE = re.compile(r"pcmC(\d+)D(\d+)p$")
_PCM_SUBDEVICE_RE = re.compile(r"sub(\d+)$")
DEFAULT_PROC_ASOUND_ROOT = Path("/proc/asound")


def _read_text(path: Path) -> str | None:
    try:
        value = path.read_text(encoding="utf-8").strip()
    except OSError:
        return None
    return value or None


def _sha256_file(path: Path) -> str | None:
    try:
        payload = path.read_bytes()
    except OSError:
        return None
    return hashlib.sha256(payload).hexdigest() if payload else None


def _usb_physical_path(sysfs_root: Path, device_dir: Path) -> str | None:
    """devpath estable (p.ej. '2-1'), nunca el índice de bus."""
    try:
        relative = device_dir.relative_to(sysfs_root / "bus" / "usb" / "devices")
    except ValueError:
        return None
    return str(relative)


def read_usb_devices(
    sysfs_root: Path, *, observed_at_ns: int | None = None
) -> tuple[DeviceObservation, ...]:
    """USB devices observados (VID/PID/serial/strings/path/bcdDevice)."""
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
                bcd_device=_read_text(device_dir / "bcdDevice"),
                binding=None,
                descriptor_sha256=_sha256_file(device_dir / "descriptors"),
            )
        )
    return tuple(observations)


def _usb_ancestor(sysfs_root: Path, card_dir: Path) -> str | None:
    """El device USB del que cuelga la card ALSA.

    Linux-realista: el link `device` apunta al interface USB
    (p.ej. `.../usb2/2-1/2-1:1.0`); se camina hacia arriba por
    /sys/devices hasta el ancestro con idVendor/idProduct y se devuelve
    su devpath (basename).
    """
    link = card_dir / "device"
    try:
        resolved = link.resolve()
    except OSError:
        return None
    devices_root = (sysfs_root / "devices").resolve()
    for candidate in (resolved, *resolved.parents):
        try:
            candidate.relative_to(devices_root)
        except ValueError:
            return None  # fuera de /sys/devices: no es un ancestro USB
        if (candidate / "idVendor").is_file() and (candidate / "idProduct").is_file():
            return candidate.name
    return None


def _playback_pcms(sysfs_root: Path, card_index: int) -> tuple[int, ...]:
    """PCMs de playback REALES de la card, por la sound class del sysfs.

    Nunca sintetiza: una card sin `pcmC<card>D<p>p` produce tupla vacía.
    """
    sound_dir = sysfs_root / "class" / "sound"
    if not sound_dir.is_dir():
        return ()
    devices: list[int] = []
    for entry in sorted(sound_dir.iterdir()):
        match = _PCM_PLAYBACK_RE.fullmatch(entry.name)
        if match is None or int(match.group(1)) != card_index:
            continue
        devices.append(int(match.group(2)))
    return tuple(devices)


def _playback_subdevices(
    proc_asound_root: Path, card_index: int, pcm_device: int
) -> tuple[int, ...]:
    """Enumerate only subdevices that procfs proves exist for this PCM."""
    pcm_root = proc_asound_root / f"card{card_index}" / f"pcm{pcm_device}p"
    try:
        entries = tuple(pcm_root.iterdir())
    except OSError:
        return ()
    subdevices: list[int] = []
    for entry in entries:
        match = _PCM_SUBDEVICE_RE.fullmatch(entry.name)
        if match is not None and entry.is_dir():
            subdevices.append(int(match.group(1)))
    return tuple(sorted(set(subdevices)))


def _stable_endpoint_signature(
    card_dir: Path, pcm_device: int, pcm_subdevice: int | None
) -> str | None:
    """USB interface + PCM identity, deliberately independent of cardN."""
    try:
        interface_name = (card_dir / "device").resolve().name
    except OSError:
        return None
    _device_name, separator, interface = interface_name.partition(":")
    if not separator or not interface:
        return None
    signature = f"usb-interface:{interface}:pcm:{pcm_device}"
    if pcm_subdevice is not None:
        signature += f":sub:{pcm_subdevice}"
    return signature


def read_alsa_cards(
    sysfs_root: Path,
    *,
    observed_at_ns: int | None = None,
    proc_asound_root: Path = DEFAULT_PROC_ASOUND_ROOT,
) -> tuple[DeviceObservation, ...]:
    """ALSA cards observadas: cero-o-más bindings de playback.

    Cada PCM de playback real produce su propio binding
    `hw:CARD=<id>,DEV=<n>` (nunca DEV sintetizado). Una card sin
    playback produce UNA observación sin binding.
    """
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
        physical_path = _usb_ancestor(sysfs_root, card_dir)
        playback_pcms = _playback_pcms(sysfs_root, card_index)
        if not playback_pcms:
            observations.append(
                DeviceObservation(
                    source="alsa",
                    observed_at_ns=stamp,
                    vendor_id=None,
                    product_id=None,
                    serial=None,
                    manufacturer=None,
                    product=card_id,
                    physical_path=physical_path,
                    bcd_device=None,
                    binding=None,
                )
            )
            continue
        for pcm_device in playback_pcms:
            subdevices = _playback_subdevices(proc_asound_root, card_index, pcm_device)
            pcm_subdevice = subdevices[0] if len(subdevices) == 1 else None
            observations.append(
                DeviceObservation(
                    source="alsa",
                    observed_at_ns=stamp,
                    vendor_id=None,
                    product_id=None,
                    serial=None,
                    manufacturer=None,
                    product=card_id,
                    physical_path=physical_path,
                    bcd_device=None,
                    binding=AudioDeviceBinding(
                        kind=BindingKind.ALSA_PCM,
                        locator=f"hw:CARD={card_id},DEV={pcm_device}",
                        generation=0,
                        currently_available=True,
                        card_index=card_index,
                        pcm_device=pcm_device,
                        pcm_subdevice=pcm_subdevice,
                        stable_endpoint_signature=_stable_endpoint_signature(
                            card_dir, pcm_device, pcm_subdevice
                        ),
                    ),
                )
            )
    return tuple(observations)
