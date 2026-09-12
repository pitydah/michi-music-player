"""Helpers compartidos de los tests DAC-V35 (§397).

No es un `conftest.py` a propósito: el repo importa `from conftest import
...` (tests/conftest.py global) y un conftest en tests/dac/ lo
shadowearía en sys.path.

`build_linux_sysfs` construye la topología Linux REAL:
/sys/devices/<bus>/... + /sys/bus/usb/devices symlinks +
/sys/class/sound symlinks (cards y PCMs de playback).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry

_USB_BUS_PATH = "pci0000:00/0000:00:14.0/usb2"


@dataclass(frozen=True)
class UsbDevice:
    devpath: str
    vendor_id: str
    product_id: str
    serial: str | None = None
    bcd_device: str | None = None
    bus_path: str = _USB_BUS_PATH


@dataclass(frozen=True)
class AlsaCard:
    card_index: int
    card_id: str
    usb_devpath: str | None = None
    playback_pcms: tuple[int, ...] = (0,)
    platform_path: str = "platform/michi-sound"


def make_roots(tmp_path: Path) -> Path:
    sysfs_root = tmp_path / "sys"
    sysfs_root.mkdir()
    return sysfs_root


def _write_text(path: Path, value: str) -> None:
    path.write_text(value + "\n", encoding="utf-8")


def _usb_device_dir(root: Path, device: UsbDevice) -> Path:
    return root / "devices" / device.bus_path / device.devpath


def _usb_interface_dir(root: Path, device: UsbDevice) -> Path:
    return _usb_device_dir(root, device) / f"{device.devpath}:1.0"


def build_linux_sysfs(
    root: Path,
    *,
    usb_devices: tuple[UsbDevice, ...] = (),
    cards: tuple[AlsaCard, ...] = (),
) -> None:
    """Topología Linux-realista bajo `root` (que hace de /sys)."""
    for device in usb_devices:
        device_dir = _usb_device_dir(root, device)
        device_dir.mkdir(parents=True, exist_ok=True)
        _write_text(device_dir / "idVendor", device.vendor_id)
        _write_text(device_dir / "idProduct", device.product_id)
        if device.serial is not None:
            _write_text(device_dir / "serial", device.serial)
        if device.bcd_device is not None:
            _write_text(device_dir / "bcdDevice", device.bcd_device)
        _write_text(device_dir / "manufacturer", "MichiAudio")
        _write_text(device_dir / "product", "DAC Test")
        # interface USB
        _usb_interface_dir(root, device).mkdir(parents=True, exist_ok=True)
        # symlink del bus: /sys/bus/usb/devices/<devpath>
        bus_link = root / "bus" / "usb" / "devices" / device.devpath
        bus_link.parent.mkdir(parents=True, exist_ok=True)
        if not bus_link.exists():
            bus_link.symlink_to(f"../../../devices/{device.bus_path}/{device.devpath}")

    for card in cards:
        if card.usb_devpath is not None:
            device = next(
                (d for d in usb_devices if d.devpath == card.usb_devpath), None
            )
            if device is None:
                raise ValueError(f"card USB sin device: {card.usb_devpath}")
            parent = _usb_interface_dir(root, device) / "sound"
        else:
            parent = root / "devices" / card.platform_path
        card_dir = parent / f"card{card.card_index}"
        card_dir.mkdir(parents=True, exist_ok=True)
        _write_text(card_dir / "id", card.card_id)
        # link `device` al interface USB (Linux-realista) o al platform dir
        device_link = card_dir / "device"
        if not device_link.exists():
            if card.usb_devpath is not None:
                device_link.symlink_to("../..")
            else:
                device_link.symlink_to("../../..")
        # PCMs de playback reales dentro de la card + symlinks en la class
        class_sound = root / "class" / "sound"
        class_sound.mkdir(parents=True, exist_ok=True)
        for pcm in card.playback_pcms:
            pcm_name = f"pcmC{card.card_index}D{pcm}p"
            (card_dir / pcm_name).mkdir(exist_ok=True)
            pcm_link = class_sound / pcm_name
            if not pcm_link.exists():
                relative_card = card_dir.relative_to(root)
                pcm_link.symlink_to(f"../../{relative_card}/{pcm_name}")
        card_link = class_sound / f"card{card.card_index}"
        if not card_link.exists():
            relative_card = card_dir.relative_to(root)
            card_link.symlink_to(f"../../{relative_card}")


def remove_alsa_card(root: Path, card_index: int) -> None:
    """Quita una card de la class (simula renumber/desconexión ALSA)."""
    link = root / "class" / "sound" / f"card{card_index}"
    if link.is_symlink():
        link.unlink()


def remove_playback_pcm(root: Path, card_index: int, pcm: int) -> None:
    """Quita UN endpoint de playback (el USB permanece presente)."""
    import shutil

    name = f"pcmC{card_index}D{pcm}p"
    link = root / "class" / "sound" / name
    if link.is_symlink():
        link.unlink()
    for candidate in root.glob(f"**/{name}"):
        if candidate.is_dir() and not candidate.is_symlink():
            shutil.rmtree(candidate)


def remove_usb_device(root: Path, devpath: str) -> None:

    link = root / "bus" / "usb" / "devices" / devpath
    if link.is_symlink():
        link.unlink()


def make_registry() -> AudioDeviceRegistry:
    return AudioDeviceRegistry()


__all__ = [
    "AlsaCard",
    "AudioDeviceRegistry",
    "UsbDevice",
    "build_linux_sysfs",
    "make_registry",
    "make_roots",
    "remove_alsa_card",
    "remove_playback_pcm",
    "remove_usb_device",
]
