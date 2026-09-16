"""DAC-V35-080 canonical topology and hotplug gates."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.domain.audio_device import BindingKind
from michi.infrastructure.audio_devices.udev_observer import UdevObserver
from tests.dac._fixtures import (
    AlsaCard,
    UsbDevice,
    build_linux_sysfs,
    make_roots,
    remove_alsa_card,
    remove_usb_device,
)

DAC_A = UsbDevice("2-1", "2622", "0105", serial="DX5ABC123")
DAC_B = UsbDevice("2-2", "2622", "0105", serial="DX5OTHER9")


def _topology(tmp_path: Path):
    sysfs = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs,
        usb_devices=(DAC_A,),
        cards=(AlsaCard(1, "DX5", "2-1"),),
    )
    registry = AudioDeviceRegistry()
    observer = UdevObserver(registry, sysfs_root=sysfs)
    observer.rescan()
    stable_id = registry.snapshot()[0].stable_device_id
    return sysfs, registry, observer, stable_id


def test_r80_10_empty_linux_topology_reconciles_final_removed_dac(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, _stable_id = _topology(tmp_path)

    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    observer.handle_event(action="remove", subsystem="sound", sys_name="card1")

    assert registry.snapshot() == ()


def test_r80_11_repeated_identical_rescan_has_no_generation_or_event_churn(
    tmp_path: Path,
) -> None:
    _sysfs, registry, observer, stable_id = _topology(tmp_path)
    changes = []
    registry.subscribe_topology_changed(changes.append)
    generation = registry.generation_for(stable_id)

    observer.rescan()
    observer.rescan()

    assert registry.generation_for(stable_id) == generation
    assert changes == []


def test_r80_12_one_remove_snapshot_publishes_one_semantic_generation_change(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    changes = []
    registry.subscribe_topology_changed(changes.append)
    generation = registry.generation_for(stable_id)

    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")
    observer.handle_event(action="remove", subsystem="sound", sys_name="card1")

    assert len(changes) == 1
    change = changes[0]
    assert change.stable_device_id == stable_id
    assert change.previous_available is True
    assert change.current_available is False
    assert change.previous_generation == generation
    assert change.current_generation != generation
    assert change.previous_bindings
    assert change.current_bindings == ()
    with pytest.raises(FrozenInstanceError):
        change.current_available = True


def test_r80_13_14_15_same_dac_rebinds_new_card_generation_without_old_binding(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    old_binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert old_binding is not None and old_binding.card_index == 1

    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")
    lost_generation = registry.generation_for(stable_id)

    build_linux_sysfs(
        sysfs,
        usb_devices=(DAC_A,),
        cards=(AlsaCard(4, "DX5", "2-1"),),
    )
    observer.handle_event(action="add", subsystem="sound", sys_name="card4")

    assert registry.snapshot()[0].stable_device_id == stable_id
    new_binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert new_binding is not None
    assert new_binding.card_index == 4
    assert new_binding.generation != old_binding.generation
    assert new_binding.generation != lost_generation
    assert all(binding.card_index != 1 for binding in registry.bindings_for(stable_id))


def test_r80_18_same_model_vid_pid_device_cannot_impersonate_selected_dac(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    registry.select_device(stable_id)
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)
    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")

    build_linux_sysfs(
        sysfs,
        usb_devices=(DAC_B,),
        cards=(AlsaCard(1, "DX5", "2-2"),),
    )
    observer.handle_event(action="add", subsystem="usb", sys_name="2-2")

    assert registry.selected_device_id == stable_id
    assert stable_id not in registry.available_ids()
    assert registry.snapshot()[0].stable_device_id != stable_id


def test_r80_27_late_udev_callback_after_stop_is_ignored(tmp_path: Path) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    generation = registry.generation_for(stable_id)
    observer.stop()
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)

    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")

    assert registry.generation_for(stable_id) == generation
    assert stable_id in registry.available_ids()


def test_topology_unsubscribe_prevents_late_delivery(tmp_path: Path) -> None:
    sysfs, registry, observer, _stable_id = _topology(tmp_path)
    changes = []
    registry.subscribe_topology_changed(changes.append)
    registry.unsubscribe_topology_changed(changes.append)
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)

    observer.rescan()

    assert changes == []


def test_topology_callback_observes_already_mutated_registry(tmp_path: Path) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    observed = []
    registry.subscribe_topology_changed(
        lambda _change: observed.append(registry.snapshot())
    )
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)

    observer.rescan()

    assert observed == [()]
    assert stable_id not in registry.available_ids()


def test_failing_topology_subscriber_cannot_block_other_subscribers(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, _stable_id = _topology(tmp_path)
    delivered = []

    def fail(_change):
        raise RuntimeError("subscriber failure")

    registry.subscribe_topology_changed(fail)
    registry.subscribe_topology_changed(delivered.append)
    remove_usb_device(sysfs, "2-1")
    remove_alsa_card(sysfs, 1)

    observer.rescan()

    assert len(delivered) == 1


def test_adding_second_dac_does_not_churn_first_device_generation(
    tmp_path: Path,
) -> None:
    sysfs, registry, observer, stable_id = _topology(tmp_path)
    generation = registry.generation_for(stable_id)
    changes = []
    registry.subscribe_topology_changed(changes.append)
    build_linux_sysfs(
        sysfs,
        usb_devices=(DAC_A, DAC_B),
        cards=(AlsaCard(1, "DX5", "2-1"), AlsaCard(2, "DX5B", "2-2")),
    )

    observer.rescan()

    assert registry.generation_for(stable_id) == generation
    assert len(registry.available_ids()) == 2
    assert len(changes) == 1
    assert changes[0].stable_device_id != stable_id
