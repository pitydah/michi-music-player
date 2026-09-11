"""DAC-V35-010 — registry convergence gates (§400/§0G.2).

- el snapshot correlaciona USB + ALSA en una identidad coherente;
- re-scan repetido es convergente (sin duplicados);
- un device que desaparece sin evento queda unavailable (reconcile);
- cards huérfanas obtienen identidad local determinística;
- el observer udev normaliza eventos -> registry (pyudev solo observa).
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.domain.audio_device import BindingKind, IdentityConfidence
from michi.infrastructure.audio_devices.sysfs_snapshot import (
    read_alsa_cards,
    read_usb_devices,
)
from michi.infrastructure.audio_devices.udev_observer import UdevObserver
from tests.dac._fixtures import build_sysfs, make_roots

DX5 = ("2-1", "2622", "0105", "DX5ABC123")


def _ingest(registry: AudioDeviceRegistry, sysfs_root: Path, dev_root: Path) -> None:
    registry.ingest(
        read_usb_devices(sysfs_root) + read_alsa_cards(sysfs_root, dev_root)
    )


def test_ingest_correlates_usb_and_alsa(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=((1, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1, "USB+ALSA del mismo DAC: una sola identidad"
    stable_id = snapshot[0].stable_device_id
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.locator == "hw:CARD=DX5,DEV=0"
    assert binding.currently_available is True
    assert binding.card_index == 1


def test_rescan_is_convergent(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=((1, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)
    first = registry.snapshot()
    first_binding = registry.binding_for(
        first[0].stable_device_id, BindingKind.ALSA_PCM
    )

    _ingest(registry, sysfs_root, dev_root)
    second = registry.snapshot()

    assert second == first
    assert len(second) == 1, "re-scan no debe duplicar identidades"
    second_binding = registry.binding_for(
        second[0].stable_device_id, BindingKind.ALSA_PCM
    )
    assert second_binding is not None and first_binding is not None
    assert second_binding.generation == first_binding.generation


def test_missing_device_reconciled_unavailable(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=((1, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)
    assert len(registry.snapshot()) == 1

    import shutil

    shutil.rmtree(sysfs_root / "bus" / "usb" / "devices" / "2-1")
    shutil.rmtree(sysfs_root / "class" / "sound" / "card1")
    _ingest(registry, sysfs_root, dev_root)

    assert registry.snapshot() == (), (
        "un device ausente en el re-scan queda unavailable"
    )


def test_orphan_card_gets_local_identity(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(),
        cards=((1, "Headset", None),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].stable_device_id == "local:hw:CARD=Headset,DEV=0"
    assert snapshot[0].confidence is IdentityConfidence.LOW
    binding = registry.binding_for(snapshot[0].stable_device_id, BindingKind.ALSA_PCM)
    assert binding is not None and binding.locator == "hw:CARD=Headset,DEV=0"


def test_binding_for_respects_kind(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=((1, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)
    stable_id = registry.snapshot()[0].stable_device_id

    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is not None
    assert registry.binding_for(stable_id, BindingKind.PIPEWIRE_NODE) is None
    assert registry.binding_for("usb:no:existe", BindingKind.ALSA_PCM) is None


def test_udev_observer_normalizes_events_to_registry(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=((1, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    observer = UdevObserver(registry, sysfs_root=sysfs_root, dev_root=dev_root)

    observer.handle_event(action="add", subsystem="usb", sys_name="2-1")
    assert len(registry.snapshot()) == 1

    import shutil

    shutil.rmtree(sysfs_root / "bus" / "usb" / "devices" / "2-1")
    shutil.rmtree(sysfs_root / "class" / "sound" / "card1")
    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")

    assert registry.snapshot() == (), "remove udev -> unavailable vía registry"
