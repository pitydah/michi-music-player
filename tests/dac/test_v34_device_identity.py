"""DAC-V35-010 — device identity gates (§400 + DAC-C01..C03).

Topología Linux REAL (C01): /sys/devices + /sys/bus/usb/devices symlink +
/sys/class/sound symlink. Los tests atraviesan los adapters productivos
(sysfs_snapshot) y el registry productivo, no hojas fake.
"""

from __future__ import annotations

from pathlib import Path

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.domain.audio_device import BindingKind, IdentityConfidence
from michi.infrastructure.audio_devices.sysfs_snapshot import (
    read_alsa_cards,
    read_usb_devices,
)
from tests.dac._fixtures import (
    AlsaCard,
    UsbDevice,
    build_linux_sysfs,
    make_roots,
    remove_alsa_card,
    remove_playback_pcm,
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


def test_linux_topology_correlates_usb_dac_with_playback_endpoint(
    tmp_path: Path,
) -> None:
    """C01: un DAC USB físico correlaciona con su endpoint ALSA playback."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()

    _ingest(registry, sysfs_root)

    snapshot = registry.snapshot()
    assert len(snapshot) == 1, "USB+ALSA del mismo DAC: una sola identidad"
    identity = snapshot[0]
    assert identity.stable_device_id == "usb:2622:0105:DX5ABC123"
    assert identity.confidence is IdentityConfidence.HIGH
    assert identity.physical_path == "2-1"
    assert identity.bcd_device == "0x0105", "C03: bcdDevice es un hecho de identidad"
    binding = registry.binding_for(identity.stable_device_id, BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.locator == "hw:CARD=DX5,DEV=0"
    assert binding.card_index == 1
    assert binding.currently_available is True


def test_card_without_playback_pcm_produces_zero_bindings(tmp_path: Path) -> None:
    """C02: card sin PCM de playback real -> CERO bindings de playback."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(
            AlsaCard(
                card_index=1,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=(),
            ),
        ),
    )
    registry = AudioDeviceRegistry()

    _ingest(registry, sysfs_root)

    alsa = read_alsa_cards(sysfs_root)
    assert len(alsa) == 1 and alsa[0].binding is None, (
        "la card sin playback se observa SIN binding"
    )
    stable_id = "usb:2622:0105:DX5ABC123"
    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is None


def test_multiple_playback_pcms_are_preserved(tmp_path: Path) -> None:
    """C02: cero-o-más bindings: cada PCM de playback real se preserva."""
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
    alsa = read_alsa_cards(sysfs_root)
    locators = sorted(item.binding.locator for item in alsa if item.binding)
    assert locators == ["hw:CARD=DX5,DEV=0", "hw:CARD=DX5,DEV=1"]


def test_never_synthesizes_dev_zero(tmp_path: Path) -> None:
    """C02: si el único PCM es D1, el binding es DEV=1 (nunca DEV=0)."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(
            AlsaCard(
                card_index=1,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=(1,),
            ),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)

    binding = registry.binding_for("usb:2622:0105:DX5ABC123", BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.locator == "hw:CARD=DX5,DEV=1"
    assert binding.pcm_device == 1


def test_replug_same_dac_preserves_stable_id(tmp_path: Path) -> None:
    """C03: replug del mismo DAC preserva el stable_device_id."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    assert stable_id == "usb:2622:0105:DX5ABC123"

    # desconexión física
    remove_usb_device(sysfs_root, "2-1")
    remove_alsa_card(sysfs_root, 1)
    registry.handle_removed("2-1")
    assert registry.snapshot() == ()

    # replug: misma evidencia
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    _ingest(registry, sysfs_root)
    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]


def test_identical_vid_pid_simultaneous_not_merged(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105"),
            UsbDevice("2-2", "2622", "0105"),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    ids = [i.stable_device_id for i in registry.snapshot()]
    assert len(ids) == 2, "dos DACs idénticos simultáneos no deben fusionarse"
    assert ids == ["usb:2622:0105:2-1", "usb:2622:0105:2-2"]


def test_duplicated_serial_simultaneous_not_merged(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(
            UsbDevice("2-1", "2622", "0105", serial="SAME123"),
            UsbDevice("2-2", "2622", "0105", serial="SAME123"),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    ids = [i.stable_device_id for i in registry.snapshot()]
    assert len(ids) == 2, "un serial duplicado simultáneo no identifica"
    assert all("SAME123" not in stable_id for stable_id in ids)


def test_generic_serial_not_used_for_identity(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(UsbDevice("2-1", "2622", "0105", serial="00000000"),),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    identity = registry.snapshot()[0]
    assert identity.stable_device_id == "usb:2622:0105:2-1"
    assert identity.confidence is IdentityConfidence.MEDIUM
    assert identity.serial is None


def test_card_renumber_preserves_identity_updates_binding(tmp_path: Path) -> None:
    """C03: renumber de card cambia binding/generation, no la identidad."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None and binding.card_index == 1
    generation_before = binding.generation

    remove_alsa_card(sysfs_root, 1)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(AlsaCard(card_index=2, card_id="DX5", usb_devpath="2-1"),),
    )
    _ingest(registry, sysfs_root)

    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    assert binding.card_index == 2
    assert binding.generation > generation_before, "rebind -> generation nueva"


def test_remove_marks_unavailable_and_preserves_selected_intent(
    tmp_path: Path,
) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    registry.select_device(stable_id)

    registry.handle_removed("2-1")

    assert registry.snapshot() == (), "removido no debe aparecer disponible"
    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is None
    assert registry.selected_device_id == stable_id, (
        "el intent seleccionado sobrevive a la desconexión"
    )


def test_stale_generation_result_ignored(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(CARD_DX5,))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    binding = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert binding is not None
    stale_generation = binding.generation

    remove_alsa_card(sysfs_root, 1)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(AlsaCard(card_index=2, card_id="DX5", usb_devpath="2-1"),),
    )
    _ingest(registry, sysfs_root)

    assert registry.apply_probe_result(stable_id, stale_generation) is False, (
        "un resultado de probe con generation vieja debe descartarse"
    )
    current = registry.binding_for(stable_id, BindingKind.ALSA_PCM)
    assert current is not None
    assert registry.apply_probe_result(stable_id, current.generation) is True


# ── DAC-B: generation representa el SET de endpoints ─────────────────


def _single_card(playback_pcms: tuple[int, ...]) -> AlsaCard:
    return AlsaCard(
        card_index=1,
        card_id="DX5",
        usb_devpath="2-1",
        playback_pcms=playback_pcms,
    )


def test_g1_endpoint_disappears_invalidates_generation(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)
    assert generation_before is not None

    # desaparece SOLO el endpoint ALSA; el USB sigue presente
    remove_playback_pcm(sysfs_root, 1, 0)
    _ingest(registry, sysfs_root)

    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]
    assert registry.bindings_for(stable_id, BindingKind.ALSA_PCM) == ()
    assert registry.generation_for(stable_id) > generation_before
    assert registry.apply_probe_result(stable_id, generation_before) is False, (
        "un probe iniciado antes de perder el endpoint debe descartarse"
    )


def test_g2_endpoint_appears_invalidates_generation(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card(()),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)
    assert registry.bindings_for(stable_id, BindingKind.ALSA_PCM) == ()

    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))
    _ingest(registry, sysfs_root)

    assert registry.generation_for(stable_id) > generation_before
    assert [b.locator for b in registry.bindings_for(stable_id)] == [
        "hw:CARD=DX5,DEV=0"
    ]


def test_g3_second_endpoint_invalidates_generation(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)

    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0, 1)),))
    _ingest(registry, sysfs_root)

    assert registry.generation_for(stable_id) > generation_before
    assert [b.locator for b in registry.bindings_for(stable_id)] == [
        "hw:CARD=DX5,DEV=0",
        "hw:CARD=DX5,DEV=1",
    ]


def test_g4_no_topology_change_keeps_generation(tmp_path: Path) -> None:
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0, 1)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)

    _ingest(registry, sysfs_root)
    _ingest(registry, sysfs_root)

    assert registry.generation_for(stable_id) == generation_before, (
        "un rescan sin cambio topológico NO incrementa generation"
    )


def test_replug_with_multi_endpoints_restores_all(tmp_path: Path) -> None:
    """§17: identidad + multi-binding + generation + selected intent."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0, 1)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)
    registry.select_device(stable_id)

    remove_usb_device(sysfs_root, "2-1")
    remove_alsa_card(sysfs_root, 1)
    registry.handle_removed("2-1")
    assert registry.snapshot() == ()
    assert registry.selected_device_id == stable_id, "el intent sobrevive"

    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0, 1)),))
    _ingest(registry, sysfs_root)

    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]
    assert registry.generation_for(stable_id) > generation_before
    assert [b.locator for b in registry.bindings_for(stable_id)] == [
        "hw:CARD=DX5,DEV=0",
        "hw:CARD=DX5,DEV=1",
    ]


def test_card_renumber_with_multi_endpoints_keeps_all(tmp_path: Path) -> None:
    """§18: renumber no pierde endpoints ni identidad."""
    sysfs_root = make_roots(tmp_path)
    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0, 1)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, sysfs_root)
    stable_id = registry.snapshot()[0].stable_device_id
    generation_before = registry.generation_for(stable_id)

    remove_alsa_card(sysfs_root, 1)
    build_linux_sysfs(
        sysfs_root,
        usb_devices=(DX5,),
        cards=(
            AlsaCard(
                card_index=2,
                card_id="DX5",
                usb_devpath="2-1",
                playback_pcms=(0, 1),
            ),
        ),
    )
    _ingest(registry, sysfs_root)

    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]
    assert registry.generation_for(stable_id) > generation_before
    bindings = registry.bindings_for(stable_id, BindingKind.ALSA_PCM)
    assert [b.locator for b in bindings] == [
        "hw:CARD=DX5,DEV=0",
        "hw:CARD=DX5,DEV=1",
    ]
    assert all(b.card_index == 2 for b in bindings), "card_index 1 -> 2"
