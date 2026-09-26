"""DAC-V35-010R1 — universal playback admission + semantic projection.

These gates deliberately avoid product/vendor blacklists. The deciding fact is
real playback capability; names only influence low-risk presentation grouping
after admission.
"""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from michi.application.audio_device_registry import AudioDeviceRegistry
from michi.application.audio_device_semantics import (
    AudioDeviceCategory,
    classify_audio_device,
    has_current_playback,
)
from michi.application.audio_output_selection_coordinator import (
    AudioOutputSelectionCoordinator,
    AudioOutputSelectionError,
)
from michi.domain.audio_device import BindingKind
from michi.infrastructure.audio_devices.sysfs_snapshot import (
    read_alsa_cards,
    read_usb_devices,
)
from tests.dac._fixtures import (
    AlsaCard,
    UsbDevice,
    build_linux_sysfs,
    make_roots,
    remove_playback_pcm,
)


def _ingest(registry: AudioDeviceRegistry, root: Path) -> None:
    registry.ingest(read_usb_devices(root) + read_alsa_cards(root))


def test_unknown_usb_with_real_playback_is_admitted_without_whitelist(
    tmp_path: Path,
) -> None:
    root = make_roots(tmp_path)
    unknown = UsbDevice("9-4", "dead", "beef", serial="UNSEEN-DAC-1")
    build_linux_sysfs(
        root, usb_devices=(unknown,), cards=(AlsaCard(3, "Mystery", "9-4"),)
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshots = registry.device_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].identity.vendor_id == "dead"
    assert snapshots[0].identity.product_id == "beef"
    assert has_current_playback(snapshots[0])
    assert (
        classify_audio_device(snapshots[0]).category
        is AudioDeviceCategory.EXTERNAL_AUDIO
    )


def test_arbitrary_usb_without_playback_never_enters_audio_output(
    tmp_path: Path,
) -> None:
    root = make_roots(tmp_path)
    # Names intentionally resemble the real-world bug, but correctness does not
    # depend on these strings: ANY USB identity without playback is excluded.
    devices = (
        UsbDevice("2-1", "1111", "0001", serial="KEYBOARD"),
        UsbDevice("2-2", "2222", "0002", serial="CAMERA"),
        UsbDevice("2-3", "3333", "0003", serial="HUB"),
        UsbDevice("2-4", "4444", "0004", serial="MOUSE"),
    )
    build_linux_sysfs(root, usb_devices=devices, cards=())
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    assert registry.snapshot() == ()
    assert registry.device_snapshots() == ()


def test_capture_only_usb_card_is_not_an_output(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    camera = UsbDevice("3-2", "cafe", "0001", serial="CAPTURE-ONLY")
    build_linux_sysfs(
        root,
        usb_devices=(camera,),
        cards=(AlsaCard(4, "CameraMic", "3-2", playback_pcms=(), capture_pcms=(0,)),),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    assert registry.snapshot() == ()
    assert registry.device_snapshots() == ()


def test_duplex_usb_is_admitted_without_overclaiming_interface_role(
    tmp_path: Path,
) -> None:
    root = make_roots(tmp_path)
    interface = UsbDevice("4-1", "abcd", "1000", serial="INTERFACE-1")
    build_linux_sysfs(
        root,
        usb_devices=(interface,),
        cards=(AlsaCard(5, "Interface", "4-1", playback_pcms=(0,), capture_pcms=(0,)),),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshot = registry.device_snapshots()[0]
    classification = classify_audio_device(snapshot)
    assert snapshot.capture_capable is True
    assert classification.category is AudioDeviceCategory.EXTERNAL_AUDIO
    assert "does not prove a product role" in classification.reason


def test_non_usb_motherboard_playback_remains_first_class(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    build_linux_sysfs(
        root,
        cards=(
            AlsaCard(0, "Generic", None, playback_pcms=(0,), platform_path="pci/hda"),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshot = registry.device_snapshots()[0]
    assert snapshot.identity.stable_device_id == "local:hw:CARD=Generic,DEV=0"
    assert has_current_playback(snapshot)
    assert classify_audio_device(snapshot).category is AudioDeviceCategory.LOCAL_AUDIO


def test_hdmi_playback_is_kept_but_classified_as_display_audio(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    build_linux_sysfs(
        root,
        cards=(
            AlsaCard(0, "HDMI", None, playback_pcms=(3, 7), platform_path="pci/gpu"),
        ),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshots = registry.device_snapshots()
    assert len(snapshots) == 2
    assert all(
        classify_audio_device(item).category is AudioDeviceCategory.DISPLAY_AUDIO
        for item in snapshots
    )


def test_known_audio_identity_losing_playback_is_retained_disconnected(
    tmp_path: Path,
) -> None:
    root = make_roots(tmp_path)
    dac = UsbDevice("5-1", "aaaa", "bbbb", serial="KNOWN-AUDIO")
    build_linux_sysfs(root, usb_devices=(dac,), cards=(AlsaCard(1, "DAC", "5-1"),))
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    stable_id = registry.snapshot()[0].stable_device_id
    before = registry.generation_for(stable_id)
    remove_playback_pcm(root, 1, 0)
    _ingest(registry, root)
    assert registry.snapshot() == ()
    retained = {
        item.identity.stable_device_id: item for item in registry.device_snapshots()
    }
    assert retained[stable_id].available is False
    assert retained[stable_id].bindings == ()
    assert registry.generation_for(stable_id) > before


def test_product_sources_contain_no_usb_name_vendor_blacklist() -> None:
    root = Path(__file__).resolve().parents[2]
    sources = "\n".join(
        (root / path).read_text(encoding="utf-8").casefold()
        for path in (
            "src/michi/application/audio_device_registry.py",
            "src/michi/application/audio_device_semantics.py",
        )
    )
    for forbidden in (
        "varmilo",
        "lumina",
        "sinowealth",
        "aura led",
        "genesyslogic",
        'if "keyboard"',
        'if "camera"',
        'if "mouse"',
        'if "hub"',
    ):
        assert forbidden not in sources


def test_registry_playback_capability_api_is_defensive(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    dac = UsbDevice("6-1", "1234", "5678", serial="DAC-X")
    build_linux_sysfs(root, usb_devices=(dac,), cards=(AlsaCard(2, "DACX", "6-1"),))
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    stable_id = registry.snapshot()[0].stable_device_id
    assert registry.is_playback_capable(stable_id) is True
    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is not None


def test_semantic_classification_never_controls_admission(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    build_linux_sysfs(root, cards=(AlsaCard(8, "OddDevice", None, playback_pcms=(4,)),))
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshot = registry.device_snapshots()[0]
    # Even if the category is generic/local, playback proof is sufficient.
    assert has_current_playback(snapshot)
    assert snapshot.available is True


def test_selection_firewall_rejects_available_row_without_playback_binding() -> None:
    fake_snapshot = SimpleNamespace(
        identity=SimpleNamespace(stable_device_id="synthetic:non-audio"),
        available=True,
        bindings=(),
    )
    devices = SimpleNamespace(device_snapshots=lambda: (fake_snapshot,))
    coordinator = AudioOutputSelectionCoordinator(
        profiles=object(),
        devices=devices,
        output_session=object(),
        engines=object(),
    )
    with pytest.raises(AudioOutputSelectionError) as exc_info:
        coordinator.select_device("synthetic:non-audio")
    assert exc_info.value.code == "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE"


def test_display_audio_is_collapsed_in_quick_ui_and_grouped_in_settings() -> None:
    repo = Path(__file__).resolve().parents[2]
    popup = (repo / "src/michi/presentation/qml/player/AudioOutputPopup.qml").read_text(
        encoding="utf-8"
    )
    settings = (
        repo / "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml"
    ).read_text(encoding="utf-8")
    bridge = (repo / "src/michi/presentation/audio_output_bridge.py").read_text(
        encoding="utf-8"
    )
    assert "property bool displayAudioExpanded: false" in popup
    assert "__display_audio__" in popup
    assert "AudioOutputDeviceGroup" in settings
    # The display group spec is asserted semantically, not by its source layout:
    # the original one-line tuple is >88 columns, so the mandatory ruff-format
    # gate rewrites it as a multi-line tuple and any exact-layout substring
    # would contradict that gate. group id + label + category are the contract.
    assert '"display"' in bridge
    assert '"Display Audio"' in bridge
    assert '"display_audio"' in bridge
    assert '"HDMI / DisplayPort audio outputs"' in bridge
