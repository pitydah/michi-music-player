"""Helpers compartidos de los tests DAC-V35 (§397).

No es un `conftest.py` a propósito: el repo importa `from conftest import
...` (tests/conftest.py global) y un conftest en tests/dac/ lo
shadowearía en sys.path.
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry


def make_roots(tmp_path: Path) -> tuple[Path, Path]:
    sysfs_root = tmp_path / "sys"
    sysfs_root.mkdir()
    dev_root = tmp_path / "dev"
    dev_root.mkdir()
    return sysfs_root, dev_root


def build_sysfs(
    root: Path,
    *,
    usb_devices: tuple[tuple[str, str, str, str | None], ...] = (),
    cards: tuple[tuple[int, str, str | None], ...] = (),
    dev_root: Path | None = None,
) -> None:
    """Construye un árbol sysfs fake.

    usb_devices: (devpath, vid, pid, serial|None)
    cards: (card_index, card_id, usb_devpath|None)
    """
    for devpath, vid, pid, serial in usb_devices:
        device_dir = root / "bus" / "usb" / "devices" / devpath
        device_dir.mkdir(parents=True)
        (device_dir / "idVendor").write_text(vid + "\n", encoding="utf-8")
        (device_dir / "idProduct").write_text(pid + "\n", encoding="utf-8")
        if serial is not None:
            (device_dir / "serial").write_text(serial + "\n", encoding="utf-8")
        (device_dir / "manufacturer").write_text("MichiAudio\n", encoding="utf-8")
        (device_dir / "product").write_text("DAC Test\n", encoding="utf-8")
    sound_dir = root / "class" / "sound"
    sound_dir.mkdir(parents=True, exist_ok=True)
    for card_index, card_id, usb_devpath in cards:
        card_dir = sound_dir / f"card{card_index}"
        card_dir.mkdir(parents=True, exist_ok=True)
        (card_dir / "id").write_text(card_id + "\n", encoding="utf-8")
        if usb_devpath is not None:
            link = card_dir / "device"
            if not link.exists():
                link.symlink_to(f"../../../bus/usb/devices/{usb_devpath}")
        if dev_root is not None:
            snd = dev_root / "snd"
            snd.mkdir(parents=True, exist_ok=True)
            (snd / f"pcmC{card_index}D0p").touch()


__all__ = ["AudioDeviceRegistry", "build_sysfs", "make_roots"]
