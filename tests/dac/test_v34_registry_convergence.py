"""DAC-V35-010 — registry convergence gates (§400/§0G.2 + DAC-C01..C03).

Los tests atraviesan la topología Linux real y los adapters productivos;
el observer udev normaliza eventos hacia el registry (pyudev solo observa).
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
from tests.dac._fixtures import (
    AlsaCard,
    UsbDevice,
    build_linux_sysfs,
    make_roots,
    remove_alsa_card,
    remove_usb_device,
)

DX5 = UsbDevice(
    devpath="2-1",
    vendor_id="2622",
    product_id="0105",
    serial="DX5ABC123",
    bcd_device="0x0105",
)
CARD_DX5 = AlsaCard(card_index=1, card_id="DX5", usb_devpath="2-1")


def _ingest(registry: AudioDeviceRegistry, sysfs_root: Path) -> None:
    registry.ingest(read_usb_devices(sysfs_root) + read_alsa_cards(sysfs_root))


def test_ingest_correlates_usb_and_alsa(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()

    _ingest(registry, sysfs_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1, "USB+ALSA del mismo DAC: una sola identidad"
    stable_id = snapshot[0].stable_device_id
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.locator == "hw:CARD=DX5,DEV=0"
    assert binding.currently_available is True
    assert binding.card_index == 1


def test_rescan_is_convergent(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    first = registry.snapshot()
    first_binding = registry.binding_for(
        first[0].stable_device_id, BindingKind.ALSA_PCM
    )

    _ingest(registry, sysfs_root)
    second = registry.snapshot()

    assert second == first
    assert len(second) == 1, "re-scan no debe duplicar identidades"
    second_binding = registry.binding_for(
        second[0].stable_device_id, BindingKind.ALSA_PCM
    )
    assert second_binding is not None and first_binding is not None
    assert second_binding.generation == first_binding.generation


def test_missing_device_reconciled_unavailable(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    assert len(registry.snapshot()) == 1

    remove_usb_device(sysfs_root, "2-1")
    remove_alsa_card(sysfs_root, 1)
    _ingest(registry, sysfs_root)

    assert registry.snapshot() == (), (
        "un device ausente en el re-scan queda unavailable"
    )


def test_orphan_card_gets_local_identity(tmp_path: Path) -> None:
    """Card no-USB (platform): identidad local determinística."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(),
        cards=(
            AlsaCard(
                card_index=0,
                card_id="Headset",
                usb_devpath=None,
                playback_pcms=(0,),
            ),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1
    assert snapshot[0].stable_device_id == "local:hw:CARD=Headset,DEV=0"
    assert snapshot[0].confidence is IdentityConfidence.LOW
    binding = registry.binding_for(snapshot[0].stable_device_id, BindingKind.ALSA_PCM)
    assert binding is not None and binding.locator == "hw:CARD=Headset,DEV=0"


def test_binding_for_respects_kind(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id

    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is not None
    assert registry.binding_for(stable_id, BindingKind.PIPEWIRE_NODE) is None
    assert registry.binding_for("usb:no:existe", BindingKind.ALSA_PCM) is None


def test_udev_observer_normalizes_events_to_registry(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    observer = UdevObserver(registry, sysfs_root=sysfs_root)

    observer.handle_event(action="add", subsystem="usb", sys_name="2-1")
    assert len(registry.snapshot()) == 1

    remove_usb_device(sysfs_root, "2-1")
    remove_alsa_card(sysfs_root, 1)
    observer.handle_event(action="remove", subsystem="usb", sys_name="2-1")

    assert registry.snapshot() == (), "remove udev -> unavailable vía registry"


# ── DAC-A: multi-endpoint REAL en el registry canónico ───────────────


def test_registry_preserves_all_playback_endpoints(tmp_path: Path) -> None:
    """A-RED: un DAC físico con DEV0+DEV1 conserva AMBOS endpoints en la
    autoridad canónica (no sólo en el adapter)."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(
            AlsaCard(
                card_index=1,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=(0, 1),
            ),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1, "una sola identidad física"
    stable_id = snapshot[0].stable_device_id
    bindings = registry.bindings_for(stable_id, BindingKind.ALSA_PCM)
    assert [b.locator for b in bindings] == [
        "hw:CARD=DX5,DEV=0",
        "hw:CARD=DX5,DEV=1",
    ], "ningún endpoint puede perderse en la autoridad canónica"


def test_bindings_for_without_kind_returns_all(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(
            AlsaCard(
                card_index=1,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=(0, 1),
            ),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    assert len(registry.bindings_for(stable_id)) == 2
    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is not None
