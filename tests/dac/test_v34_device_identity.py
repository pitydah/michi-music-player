"""DAC-V35-010 — device identity gates (§400).

- same DAC replug -> same stable id cuando la evidencia lo permite;
- dos devices simultáneos idénticos (VID/PID) NO se fusionan;
- serial duplicado simultáneo NO identifica;
- remove -> unavailable sin borrar el intent seleccionado;
- resultado async con generation vieja -> STALE, sin mutación.
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.domain.audio_device import BindingKind, IdentityConfidence
from tests.dac._fixtures import build_sysfs, make_roots

DX5 = ("2-1", "2622", "0105", "DX5ABC123")


def _ingest(registry: AudioDeviceRegistry, sysfs_root: Path, dev_root: Path) -> None:
    from michi.infrastructure.audio_devices.sysfs_snapshot import (
        read_alsa_cards,
        read_usb_devices,
    )

    registry.ingest(
        read_usb_devices(sysfs_root) + read_alsa_cards(sysfs_root, dev_root)
    )


def test_replug_same_dac_preserves_stable_id(tmp_path: Path) -> None:
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
    assert len(snapshot) == 1
    stable_id = snapshot[0].stable_device_id
    assert stable_id == "usb:2622:0105:DX5ABC123"
    assert snapshot[0].confidence is IdentityConfidence.HIGH

    # desconexión física
    registry.handle_removed("2-1")
    assert registry.snapshot() == ()
    assert registry.selected_device_id is None

    # replug: mismo DAC, misma evidencia
    _ingest(registry, sysfs_root, dev_root)
    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]


def test_identical_vid_pid_simultaneous_not_merged(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(
            ("2-1", "2622", "0105", None),
            ("2-2", "2622", "0105", None),
        ),
    )
    _ingest(registry, sysfs_root, dev_root)
    ids = [i.stable_device_id for i in registry.snapshot()]
    assert len(ids) == 2, "dos DACs idénticos simultáneos no deben fusionarse"
    assert ids == ["usb:2622:0105:2-1", "usb:2622:0105:2-2"]


def test_duplicated_serial_simultaneous_not_merged(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(
            ("2-1", "2622", "0105", "SAME123"),
            ("2-2", "2622", "0105", "SAME123"),
        ),
    )
    _ingest(registry, sysfs_root, dev_root)
    ids = [i.stable_device_id for i in registry.snapshot()]
    assert len(ids) == 2, "un serial duplicado simultáneo no identifica"
    assert all("SAME123" not in stable_id for stable_id in ids)


def test_generic_serial_not_used_for_identity(tmp_path: Path) -> None:
    registry = AudioDeviceRegistry()
    sysfs_root, dev_root = make_roots(tmp_path)
    build_sysfs(
        sysfs_root,
        usb_devices=(("2-1", "2622", "0105", "00000000"),),
    )
    _ingest(registry, sysfs_root, dev_root)
    identity = registry.snapshot()[0]
    assert identity.stable_device_id == "usb:2622:0105:2-1"
    assert identity.confidence is IdentityConfidence.MEDIUM
    assert identity.serial is None


def test_card_renumber_preserves_identity_updates_binding(tmp_path: Path) -> None:
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
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None and binding.card_index == 1
    generation_before = binding.generation

    # renumber: la card pasa de índice 1 a 2 (mismo card id)
    import shutil

    shutil.rmtree(sysfs_root / "class" / "sound" / "card1")
    build_sysfs(
        sysfs_root,
        usb_devices=(),
        cards=((2, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)

    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.card_index == 2
    assert binding.generation > generation_before, "rebind -> generation nueva"


def test_remove_marks_unavailable_and_preserves_selected_intent(tmp_path: Path) -> None:
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
    registry.select_device(stable_id)

    registry.handle_removed("2-1")

    assert registry.snapshot() == (), "removido no debe aparecer disponible"
    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is None
    assert registry.selected_device_id == stable_id, (
        "el intent seleccionado sobrevive a la desconexión"
    )


def test_stale_generation_result_ignored(tmp_path: Path) -> None:
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
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    stale_generation = binding.generation

    # rebind -> la generation avanza
    import shutil

    shutil.rmtree(sysfs_root / "class" / "sound" / "card1")
    build_sysfs(
        sysfs_root,
        usb_devices=(),
        cards=((2, "DX5", "2-1"),),
        dev_root=dev_root,
    )
    _ingest(registry, sysfs_root, dev_root)

    assert registry.apply_probe_result(stable_id, stale_generation) is False, (
        "un resultado de probe con generation vieja debe descartarse"
    )
    current = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert current is not None
    assert registry.apply_probe_result(stable_id, current.generation) is True
