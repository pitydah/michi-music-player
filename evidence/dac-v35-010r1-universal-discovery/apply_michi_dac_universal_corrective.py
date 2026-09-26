#!/usr/bin/env python3
"""One-shot exact applicator for Michi DAC universal audio discovery corrective.

BASE HEAD: e0eb9fc3df4648bb3d6341341427f16b800be2f2

This applicator is intentionally fail-closed. It verifies the exact Git blob SHA
of every pre-existing file it edits before changing anything. It never uses
fuzzy patching, name/vendor blacklists, or hardware-specific admission rules.

Apply workflow:
  python scripts/apply_michi_dac_universal_corrective.py --check
  python scripts/apply_michi_dac_universal_corrective.py --apply

The script deletes itself after a successful --apply unless --keep-bootstrap is
passed. The resulting working-tree diff contains only product/tests/docs changes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import sys
from pathlib import Path

BASE_HEAD = "e0eb9fc3df4648bb3d6341341427f16b800be2f2"
ROOT = Path(__file__).resolve().parents[1]
SELF = Path(__file__).resolve()
DRY_RUN = False
VIRTUAL_FILES: dict[str, str] = {}

EXPECTED_BLOBS = {
    "src/michi/domain/audio_device.py": "9751dfb9298724424fb39cd0cb7133f5dd113b01",
    "src/michi/infrastructure/audio_devices/sysfs_snapshot.py": "aba9b59cb3d5104e6ecf9e32a9865f28cfb80dff",
    "src/michi/application/audio_device_registry.py": "fc8331773f44871e6046a7a17332c740ea2b45f3",
    "src/michi/application/audio_output_selection_coordinator.py": "001a0dab60e8f618b5d394a8a63102d328ea5514",
    "src/michi/application/playback_failure.py": "7ce438eb48ce3639d9ec48ade1c7b6e1b2e1b4da",
    "src/michi/presentation/audio_output_bridge.py": "c299fc8304b7e32941f6a190da598ae6d0aa6cbc",
    "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml": "fc9d1ef78445751cd89d9f5dbb617f2e163c35b6",
    "src/michi/presentation/qml/player/AudioOutputPopup.qml": "4ed271f38d11e7c3a23713b26b775173b3daddb0",
    "src/michi/presentation/qml/player/NowPlayingBar.qml": "508a3058043ec7c97012b42f065a5be368900db0",
    "src/michi/presentation/qml/shell/AppShell.qml": "6d8165a6c3223224e63ab41eef59b6430a480e41",
    "src/michi/presentation/qml/views/SettingsView.qml": "b2f94a108de28d36233cc95ed315e19088e332fb",
    "src/michi/presentation/qml/components/DacDeviceCard.qml": "fd9b70ce173ca675d3f78ff9a71b2e350634019c",
    "src/michi/presentation/qml/components/DacDiagnosticsDisclosure.qml": "ce360150573dafb7a9fddfa9313f28ff7dce9231",
    "src/michi/application/dac_qualification_service.py": "412a814c18021211a88d40d1adcf5d497eb5f748",
    "scripts/dac_r110_field_suite.py": "cc4e4eb319006a0fdf86202139b5010d889c3e7b",
    "tests/dac/test_v35_110_field_schema.py": "7dbc6e9f01fe4ac270e895d7383d99a43c628eda",
    "tests/dac/_fixtures.py": "00922b9213013325ac92d1fcfa51ecf4775ce6a1",
    "tests/dac/test_v34_device_identity.py": "8b31662eb4c6b25a4c75235c56ca42c5ad6b6f18",
    "scripts/verify_dac_m11_4.py": "d79e0eddb49d64c813b91d0e4dfc593fa43a846d",
    "docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md": "47395e92fafbf0a41e68f507be38a6ce222f4d4f",
}

CREATED_FILES = (
    "src/michi/application/audio_device_semantics.py",
    "src/michi/presentation/qml/components/AudioOutputDeviceGroup.qml",
    "tests/dac/test_v35_010r1_universal_audio_discovery.py",
    "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/publication_correction.json",
)


class PatchError(RuntimeError):
    pass


def git(*args: str) -> str:
    completed = subprocess.run(
        ["git", *args], cwd=ROOT, check=False, capture_output=True, text=True
    )
    if completed.returncode != 0:
        raise PatchError(
            f"git {' '.join(args)} failed ({completed.returncode}): "
            f"{completed.stderr.strip()}"
        )
    return completed.stdout.strip()


def verify_base() -> None:
    head = git("rev-parse", "HEAD")
    if head != BASE_HEAD:
        raise PatchError(
            f"BASE HEAD mismatch: expected {BASE_HEAD}, got {head}. "
            "Do not apply this corrective to a different tree; rebase/regenerate it first."
        )
    failures: list[str] = []
    for relative, expected in EXPECTED_BLOBS.items():
        path = ROOT / relative
        if not path.is_file():
            failures.append(f"missing {relative}")
            continue
        actual = git("hash-object", relative)
        if actual != expected:
            failures.append(f"{relative}: expected blob {expected}, got {actual}")
    for relative in CREATED_FILES:
        if (ROOT / relative).exists():
            failures.append(f"new-file collision: {relative}")
    if failures:
        raise PatchError("preflight failed:\n  - " + "\n  - ".join(failures))


def text(path: str) -> str:
    if path in VIRTUAL_FILES:
        return VIRTUAL_FILES[path]
    return (ROOT / path).read_text(encoding="utf-8")


def write(path: str, payload: str) -> None:
    if DRY_RUN:
        VIRTUAL_FILES[path] = payload
        return
    target = ROOT / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(payload, encoding="utf-8")


def replace_once(path: str, old: str, new: str) -> None:
    payload = text(path)
    count = payload.count(old)
    if count != 1:
        raise PatchError(f"{path}: expected one exact replacement, found {count}")
    write(path, payload.replace(old, new, 1))


def replace_all(path: str, old: str, new: str, *, expected: int) -> None:
    payload = text(path)
    count = payload.count(old)
    if count != expected:
        raise PatchError(
            f"{path}: expected {expected} occurrences for replacement, found {count}"
        )
    write(path, payload.replace(old, new))


def replace_region(path: str, start: str, end: str, replacement: str) -> None:
    payload = text(path)
    first = payload.find(start)
    if first < 0:
        raise PatchError(f"{path}: start marker not found: {start!r}")
    second = payload.find(end, first + len(start))
    if second < 0:
        raise PatchError(f"{path}: end marker not found: {end!r}")
    if payload.find(start, first + 1) >= 0:
        raise PatchError(f"{path}: start marker is not unique")
    write(path, payload[:first] + replacement + payload[second:])


def create(path: str, payload: str) -> None:
    target = ROOT / path
    if target.exists() or path in VIRTUAL_FILES:
        raise PatchError(f"refusing to overwrite new path {path}")
    write(path, payload)


def apply_domain_observation_extension() -> None:
    replace_once(
        "src/michi/domain/audio_device.py",
        """    binding: AudioDeviceBinding | None\n    descriptor_sha256: str | None = None\n""",
        """    binding: AudioDeviceBinding | None\n    descriptor_sha256: str | None = None\n    # Card-level capture capability is auxiliary classification evidence only.\n    # It NEVER admits a device to Audio Output; playback binding does.\n    capture_capable: bool = False\n""",
    )


def apply_sysfs_capture_evidence() -> None:
    path = "src/michi/infrastructure/audio_devices/sysfs_snapshot.py"
    replace_once(
        path,
        '_PCM_PLAYBACK_RE = re.compile(r"pcmC(\\d+)D(\\d+)p$")\n',
        '_PCM_PLAYBACK_RE = re.compile(r"pcmC(\\d+)D(\\d+)p$")\n'
        '_PCM_CAPTURE_RE = re.compile(r"pcmC(\\d+)D(\\d+)c$")\n',
    )
    replace_once(
        path,
        """def _playback_subdevices(\n""",
        """def _capture_pcms(sysfs_root: Path, card_index: int) -> tuple[int, ...]:\n    \"\"\"Capture PCMs are classification evidence, never output admission.\"\"\"\n    sound_dir = sysfs_root / \"class\" / \"sound\"\n    if not sound_dir.is_dir():\n        return ()\n    devices: list[int] = []\n    for entry in sorted(sound_dir.iterdir()):\n        match = _PCM_CAPTURE_RE.fullmatch(entry.name)\n        if match is None or int(match.group(1)) != card_index:\n            continue\n        devices.append(int(match.group(2)))\n    return tuple(devices)\n\n\ndef _playback_subdevices(\n""",
    )
    replace_once(
        path,
        """        physical_path = _usb_ancestor(sysfs_root, card_dir)\n        playback_pcms = _playback_pcms(sysfs_root, card_index)\n        if not playback_pcms:\n""",
        """        physical_path = _usb_ancestor(sysfs_root, card_dir)\n        playback_pcms = _playback_pcms(sysfs_root, card_index)\n        capture_capable = bool(_capture_pcms(sysfs_root, card_index))\n        if not playback_pcms:\n""",
    )
    replace_once(
        path,
        """                    bcd_device=None,\n                    binding=None,\n                )\n""",
        """                    bcd_device=None,\n                    binding=None,\n                    capture_capable=capture_capable,\n                )\n""",
    )
    replace_once(
        path,
        """                        stable_endpoint_signature=_stable_endpoint_signature(\n                            card_dir, pcm_device, pcm_subdevice\n                        ),\n                    ),\n                )\n            )\n""",
        """                        stable_endpoint_signature=_stable_endpoint_signature(\n                            card_dir, pcm_device, pcm_subdevice\n                        ),\n                    ),\n                    capture_capable=capture_capable,\n                )\n            )\n""",
    )


def apply_registry_admission() -> None:
    path = "src/michi/application/audio_device_registry.py"
    replace_once(
        path,
        """    bindings: tuple[AudioDeviceBinding, ...]\n\n\nTopologyChangedCallback""",
        """    bindings: tuple[AudioDeviceBinding, ...]\n    capture_capable: bool = False\n\n\nTopologyChangedCallback""",
    )
    replace_once(
        path,
        """    bindings: tuple[AudioDeviceBinding, ...] = ()\n\n\nclass AudioDeviceRegistry""",
        """    bindings: tuple[AudioDeviceBinding, ...] = ()\n    capture_capable: bool = False\n\n\nclass AudioDeviceRegistry""",
    )
    replace_once(
        path,
        """                    generation=record.generation,\n                    bindings=record.bindings,\n                )\n""",
        """                    generation=record.generation,\n                    bindings=record.bindings,\n                    capture_capable=record.capture_capable,\n                )\n""",
    )
    replace_once(
        path,
        """    def available_ids(self) -> tuple[str, ...]:\n        with self._lock:\n            return tuple(\n                sorted(\n                    r.stable_device_id for r in self._records.values() if r.available\n                )\n            )\n\n""",
        """    def available_ids(self) -> tuple[str, ...]:\n        with self._lock:\n            return tuple(\n                sorted(\n                    r.stable_device_id for r in self._records.values() if r.available\n                )\n            )\n\n    def is_playback_capable(self, stable_device_id: str) -> bool:\n        \"\"\"True only for a CURRENT, proven ALSA PCM playback binding.\n\n        This is the Linux admission authority for Audio Output. USB presence,\n        USB class, product names, VID/PID and classification labels are never\n        substitutes for a real playback endpoint.\n        \"\"\"\n        with self._lock:\n            record = self._records.get(stable_device_id)\n            return bool(\n                record is not None\n                and record.available\n                and any(\n                    binding.kind is BindingKind.ALSA_PCM\n                    and binding.currently_available\n                    for binding in record.bindings\n                )\n            )\n\n""",
    )
    start = "    def _apply_observations(\n"
    end = "    def _identity_for(\n"
    replacement = '''    def _apply_observations(\n        self,\n        observations: tuple[DeviceObservation, ...],\n        *,\n        reconcile: bool,\n    ) -> None:\n        \"\"\"Reconcile raw observations into the AUDIO OUTPUT domain.\n\n        Universal admission rule:\n        * USB/sysfs may observe every USB device on the host.\n        * a NEW physical identity enters AudioDeviceRegistry only when Linux\n          proves at least one CURRENT ALSA PCM playback endpoint;\n        * capture-only cards, HID, cameras, hubs and arbitrary USB devices are\n          therefore never promoted merely because they have VID/PID;\n        * an identity that was previously admitted as audio is retained when\n          its playback endpoint disappears, but becomes unavailable so hotplug\n          intent/generation semantics remain truthful.\n\n        Classification is deliberately absent from this method. A device does\n        not need to be recognised as a DAC/interface/HDMI to be admitted; real\n        playback capability is sufficient.\n        \"\"\"\n        before = self._topology_state()\n        usb = [o for o in observations if o.vendor_id and o.product_id]\n        alsa_all = [o for o in observations if o.source == \"alsa\"]\n        alsa_playback = [o for o in alsa_all if o.binding is not None]\n\n        serial_counts: dict[str, int] = {}\n        for observation in usb:\n            serial = _useful_serial(observation.serial)\n            if serial is not None:\n                serial_counts[serial] = serial_counts.get(serial, 0) + 1\n\n        batch_ids: set[str] = set()\n        seen_current_ids: set[str] = set()\n        for observation in usb:\n            stable_id = self._identity_for(observation, serial_counts, batch_ids)\n            correlated = [\n                item\n                for item in alsa_playback\n                if observation.physical_path\n                and item.physical_path == observation.physical_path\n            ]\n            capture_capable = any(\n                item.capture_capable\n                for item in alsa_all\n                if observation.physical_path\n                and item.physical_path == observation.physical_path\n            )\n\n            if not correlated:\n                previous = self._records.get(stable_id)\n                if previous is not None:\n                    previous.capture_capable = capture_capable\n                    if previous.available or previous.bindings:\n                        previous.available = False\n                        previous.bindings = ()\n                        previous.generation = self._next_generation()\n                # Critical firewall: an unknown USB identity with no playback\n                # endpoint is not an Audio Output at all.\n                continue\n\n            self._records[stable_id] = self._publish(\n                stable_id,\n                observation,\n                self._confidence_for(stable_id, observation, serial_counts),\n                alsa_playback,\n                capture_capable=capture_capable,\n            )\n            seen_current_ids.add(stable_id)\n\n        # Non-USB ALSA playback is first-class audio: motherboard codecs,\n        # PCI/PCIe cards, S/PDIF and HDMI/DP remain discoverable. Only actual\n        # playback observations reach this loop.\n        for observation in alsa_playback:\n            correlated = any(\n                binding.locator == observation.binding.locator\n                for stable_id in seen_current_ids\n                for binding in self._records[stable_id].bindings\n            )\n            if correlated:\n                continue\n            stable_id = f\"local:{observation.binding.locator}\"\n            self._records[stable_id] = self._publish(\n                stable_id,\n                observation,\n                IdentityConfidence.LOW,\n                (),\n                capture_capable=observation.capture_capable,\n            )\n            seen_current_ids.add(stable_id)\n\n        if reconcile:\n            # Every previously admitted physical audio identity absent from the\n            # current playback topology becomes disconnected; records are never\n            # deleted because selected intent must survive physical loss.\n            for stable_id, record in self._records.items():\n                if stable_id in seen_current_ids or not record.available:\n                    continue\n                record.available = False\n                record.bindings = ()\n                record.generation = self._next_generation()\n\n        self._publish_topology_changes(before)\n\n'''
    replace_region(path, start, end, replacement)
    replace_once(
        path,
        """        confidence: IdentityConfidence,\n        alsa: list[DeviceObservation],\n    ) -> _DeviceRecord:\n""",
        """        confidence: IdentityConfidence,\n        alsa: list[DeviceObservation],\n        *,\n        capture_capable: bool = False,\n    ) -> _DeviceRecord:\n""",
    )
    replace_once(
        path,
        """            generation=generation,\n            bindings=bindings,\n        )\n""",
        """            generation=generation,\n            bindings=bindings,\n            capture_capable=capture_capable,\n        )\n""",
    )


def create_semantics_module() -> None:
    create(
        "src/michi/application/audio_device_semantics.py",
        '''"""Presentation semantics for proven audio-output devices.

Admission and classification are intentionally separate:

    real ALSA playback capability -> admission authority (registry)
    observed topology/capture/name hints -> presentation classification only

No vendor/model/VID/PID allowlist or blacklist is permitted here. An unknown
playback-capable device must remain usable even when its semantic category is
uncertain.
"""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_device import AudioDeviceBinding, BindingKind


class AudioDeviceCategory(Enum):
    EXTERNAL_AUDIO = "external_audio"
    AUDIO_INTERFACE = "audio_interface"
    LOCAL_AUDIO = "local_audio"
    DISPLAY_AUDIO = "display_audio"
    OTHER_AUDIO = "other_audio"


class ClassificationConfidence(Enum):
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass(frozen=True, slots=True)
class AudioDeviceClassification:
    category: AudioDeviceCategory
    confidence: ClassificationConfidence
    reason: str


_DISPLAY_TOKENS = (
    "hdmi",
    "displayport",
    "display port",
    "dp audio",
)


def current_playback_bindings(snapshot) -> tuple[AudioDeviceBinding, ...]:
    return tuple(
        binding
        for binding in snapshot.bindings
        if binding.kind is BindingKind.ALSA_PCM and binding.currently_available
    )


def has_current_playback(snapshot) -> bool:
    return bool(snapshot.available and current_playback_bindings(snapshot))


def classify_audio_device(snapshot) -> AudioDeviceClassification:
    """Classify for UI grouping after playback admission has succeeded.

    USB + capture is a useful generic signal for an audio interface, but it is
    not required for use. USB playback without capture is intentionally called
    External Audio rather than guessed to be a DAC/headphone/receiver.

    Linux commonly exposes both HDMI and DisplayPort sink paths through an HDA
    HDMI ALSA card; unless a DRM/EDID connector correlation proves the exact
    transport, the UI groups both as Display Audio instead of guessing HDMI vs
    DP from an ALSA device number.
    """
    identity = snapshot.identity
    if identity.bus == "usb":
        if snapshot.capture_capable:
            return AudioDeviceClassification(
                AudioDeviceCategory.AUDIO_INTERFACE,
                ClassificationConfidence.HIGH,
                "USB hardware exposes current ALSA playback plus capture capability",
            )
        return AudioDeviceClassification(
            AudioDeviceCategory.EXTERNAL_AUDIO,
            ClassificationConfidence.HIGH,
            "USB hardware exposes a current ALSA playback endpoint",
        )

    searchable = " ".join(
        value
        for value in (
            identity.manufacturer,
            identity.product,
            *(binding.locator for binding in snapshot.bindings),
        )
        if value
    ).casefold()
    if any(token in searchable for token in _DISPLAY_TOKENS):
        return AudioDeviceClassification(
            AudioDeviceCategory.DISPLAY_AUDIO,
            ClassificationConfidence.MEDIUM,
            "ALSA playback identity identifies a display-audio path; exact HDMI/DP connector is not inferred",
        )
    if has_current_playback(snapshot):
        return AudioDeviceClassification(
            AudioDeviceCategory.LOCAL_AUDIO,
            ClassificationConfidence.MEDIUM,
            "non-USB hardware exposes a current ALSA playback endpoint",
        )
    return AudioDeviceClassification(
        AudioDeviceCategory.OTHER_AUDIO,
        ClassificationConfidence.LOW,
        "no stronger presentation classification is available",
    )


def category_label(category: AudioDeviceCategory) -> str:
    return {
        AudioDeviceCategory.EXTERNAL_AUDIO: "External Audio",
        AudioDeviceCategory.AUDIO_INTERFACE: "Audio Interface",
        AudioDeviceCategory.LOCAL_AUDIO: "Built-in / Local Audio",
        AudioDeviceCategory.DISPLAY_AUDIO: "Display Audio",
        AudioDeviceCategory.OTHER_AUDIO: "Other Audio",
    }[category]
''',
    )


def apply_selection_firewall() -> None:
    path = "src/michi/application/audio_output_selection_coordinator.py"
    replace_once(
        path,
        """from michi.domain.audio_engine import AudioEngineId\n""",
        """from michi.domain.audio_device import BindingKind\nfrom michi.domain.audio_engine import AudioEngineId\n""",
    )
    old = '''        snapshots = {\n            item.identity.stable_device_id: item\n            for item in self._devices.device_snapshots()\n        }\n        snapshot = snapshots.get(stable_device_id)\n        if snapshot is None:\n            raise AudioOutputSelectionError(\n                "OUTPUT_DEVICE_UNKNOWN", "The requested audio output is unknown."\n            )\n        if not snapshot.available:\n            raise AudioOutputSelectionError(\n                "DEVICE_UNAVAILABLE", "The selected DAC is disconnected."\n            )\n\n'''
    replace_all(path, old, "        self._require_playback_device(stable_device_id)\n\n", expected=1)
    old_profile = '''        snapshots = {\n            item.identity.stable_device_id: item\n            for item in self._devices.device_snapshots()\n        }\n        snapshot = snapshots.get(stable_device_id)\n        if snapshot is None or not snapshot.available:\n            raise AudioOutputSelectionError(\n                "DEVICE_UNAVAILABLE", "The selected DAC is disconnected."\n            )\n'''
    replace_once(path, old_profile, "        self._require_playback_device(stable_device_id)\n")
    replace_once(
        path,
        """        with self._profiles.batch_changes():\n            self._select_device_policy(selection.selected_device_id, policy)\n\n    def select_volume_mode""",
        """        self._require_playback_device(selection.selected_device_id)\n        with self._profiles.batch_changes():\n            self._select_device_policy(selection.selected_device_id, policy)\n\n    def select_volume_mode""",
    )
    replace_once(
        path,
        """    def _select_device_policy(\n        self, stable_device_id: str, policy: OutputPathPreference\n    ) -> None:\n        \"\"\"Bind the canonical ``(device, policy)`` pair to one profile.\"\"\"\n""",
        """    def _select_device_policy(\n        self, stable_device_id: str, policy: OutputPathPreference\n    ) -> None:\n        \"\"\"Bind the canonical ``(device, policy)`` pair to one profile.\"\"\"\n        self._require_playback_device(stable_device_id)\n""",
    )
    replace_once(
        path,
        """    def _selected_profile(\n        self, selection: AudioOutputSelection\n    ) -> AudioOutputProfile | None:\n""",
        '''    def _require_playback_device(self, stable_device_id: str):\n        snapshots = {\n            item.identity.stable_device_id: item\n            for item in self._devices.device_snapshots()\n        }\n        snapshot = snapshots.get(stable_device_id)\n        if snapshot is None:\n            raise AudioOutputSelectionError(\n                "OUTPUT_DEVICE_UNKNOWN", "The requested audio output is unknown."\n            )\n        if not snapshot.available:\n            raise AudioOutputSelectionError(\n                "DEVICE_UNAVAILABLE", "The selected audio output is disconnected."\n            )\n        if not any(\n            binding.kind is BindingKind.ALSA_PCM and binding.currently_available\n            for binding in snapshot.bindings\n        ):\n            raise AudioOutputSelectionError(\n                "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE",\n                "The selected hardware has no current audio playback endpoint.",\n            )\n        return snapshot\n\n    def _selected_profile(\n        self, selection: AudioOutputSelection\n    ) -> AudioOutputProfile | None:\n''',
    )


def apply_failure_copy() -> None:
    path = "src/michi/application/playback_failure.py"
    replace_once(
        path,
        '        "NO_ALSA_HW_BINDING",\n',
        '        "NO_ALSA_HW_BINDING",\n        "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE",\n',
    )
    replace_once(
        path,
        '''    elif normalized == "NO_ALSA_HW_BINDING":\n        title, detail = (\n            "Direct endpoint unavailable",\n            "No current hardware playback endpoint is available for this DAC.",\n        )\n''',
        '''    elif normalized == "NO_ALSA_HW_BINDING":\n        title, detail = (\n            "Direct endpoint unavailable",\n            "No current hardware playback endpoint is available for this DAC.",\n        )\n    elif normalized == "OUTPUT_DEVICE_NOT_PLAYBACK_CAPABLE":\n        title, detail = (\n            "Not an audio output",\n            "This hardware does not expose a current playback endpoint.",\n        )\n''',
    )


def apply_bridge_projection() -> None:
    path = "src/michi/presentation/audio_output_bridge.py"
    replace_once(
        path,
        """from michi.application.audio_output_selection_coordinator import (\n""",
        """from michi.application.audio_device_semantics import (\n    AudioDeviceCategory,\n    category_label,\n    classify_audio_device,\n    current_playback_bindings,\n)\nfrom michi.application.audio_output_selection_coordinator import (\n""",
    )
    replace_once(
        path,
        """def _rate_label(rate_hz: int) -> str:\n""",
        '''def _capability_summary(evidence: tuple) -> tuple[str, list[int], list[str], list[int]]:\n    supported = [item for item in evidence if item.supported is True]\n    rates = sorted({item.tuple.rate_hz for item in supported})\n    formats = sorted({item.tuple.transport_format for item in supported})\n    channels = sorted({item.tuple.channels for item in supported})\n    if not supported:\n        return "Not yet qualified", rates, formats, channels\n    rate_label = ", ".join(_rate_label(rate) for rate in rates[:5])\n    if len(rates) > 5:\n        rate_label += f" +{len(rates) - 5}"\n    format_label = ", ".join(formats[:3])\n    if len(formats) > 3:\n        format_label += f" +{len(formats) - 3}"\n    channel_label = "/".join(str(value) for value in channels) + " ch"\n    return " · ".join(value for value in (rate_label, format_label, channel_label) if value), rates, formats, channels\n\n\ndef _device_groups(shared_row: dict[str, Any], physical_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:\n    groups: list[dict[str, Any]] = [\n        {\n            "groupId": "system",\n            "label": "System Output",\n            "description": "Desktop-managed shared output",\n            "collapsedByDefault": False,\n            "rows": [shared_row],\n        }\n    ]\n    specs = (\n        ("external", "External Audio", "DACs and USB audio interfaces", False, {"external_audio", "audio_interface"}),\n        ("local", "Built-in / Local Audio", "Motherboard, PCI/PCIe and digital audio outputs", False, {"local_audio"}),\n        ("display", "Display Audio", "HDMI / DisplayPort audio outputs", True, {"display_audio"}),\n        ("other", "Other Audio", "Playback-capable hardware not otherwise classified", False, {"other_audio"}),\n    )\n    for group_id, label, description, collapsed, categories in specs:\n        rows = [row for row in physical_rows if row.get("deviceCategory") in categories]\n        if rows:\n            groups.append(\n                {\n                    "groupId": group_id,\n                    "label": label,\n                    "description": description,\n                    "collapsedByDefault": collapsed,\n                    "rows": rows,\n                }\n            )\n    return groups\n\n\ndef _rate_label(rate_hz: int) -> str:\n''',
    )
    replace_once(
        path,
        """        profiles = self._profiles_snapshot()\n        selected_profile = next(\n""",
        """        all_profiles = self._profiles_snapshot()\n        selected_profile = next(\n""",
    )
    replace_once(
        path,
        """            (item for item in profiles if item.profile_id == selected_profile_id), None\n        )\n""",
        """            (item for item in all_profiles if item.profile_id == selected_profile_id), None\n        )\n""",
    )
    replace_once(
        path,
        """        identity_presentations = _identity_presentations(snapshots)\n        profile_rows = [\n""",
        """        identity_presentations = _identity_presentations(snapshots)\n        retained_ids = set(snapshots_by_id)\n        # Do not delete persisted profiles here, but never project stale profiles\n        # for identities the AUDIO registry no longer recognises (e.g. legacy\n        # non-audio USB rows created before the admission firewall).\n        profiles = tuple(\n            item\n            for item in all_profiles\n            if item.stable_device_id is None or item.stable_device_id in retained_ids\n        )\n        profile_rows = [\n""",
    )
    replace_once(
        path,
        """        device_rows = [shared_row, *physical_rows]\n""",
        """        device_rows = [shared_row, *physical_rows]\n        device_groups = _device_groups(shared_row, physical_rows)\n""",
    )
    replace_once(
        path,
        '            "devices": device_rows,\n',
        '            "devices": device_rows,\n            "deviceGroups": device_groups,\n',
    )
    replace_once(
        path,
        """        alsa = next(\n            (\n                binding\n                for binding in snapshot.bindings\n                if snapshot.available\n                and binding.currently_available\n                and binding.kind.value == \"alsa_pcm\"\n            ),\n            None,\n        )\n""",
        """        playback_bindings = current_playback_bindings(snapshot)\n        alsa = playback_bindings[0] if playback_bindings else None\n        classification = classify_audio_device(snapshot)\n""",
    )
    replace_once(
        path,
        """        active_truth = truth if active else None\n""",
        """        capability_summary, qualified_rates, qualified_formats, qualified_channels = (\n            _capability_summary(evidence)\n        )\n        active_truth = truth if active else None\n""",
    )
    replace_once(
        path,
        '            "manufacturer": identity.manufacturer or "",\n            "product": identity.product or "",\n',
        '            "manufacturer": identity.manufacturer or "",\n            "product": identity.product or "",\n            "deviceCategory": classification.category.value,\n            "deviceCategoryLabel": category_label(classification.category),\n            "classificationConfidence": classification.confidence.value,\n            "classificationReason": classification.reason,\n            "playbackEndpointCount": len(playback_bindings),\n            "captureCapable": snapshot.capture_capable,\n',
    )
    replace_once(
        path,
        '            "capabilityEvidenceLabel": evidence_label,\n',
        '            "capabilityEvidenceLabel": evidence_label,\n            "qualifiedCapabilitySummary": capability_summary,\n            "qualifiedRates": qualified_rates,\n            "qualifiedFormats": qualified_formats,\n            "qualifiedChannels": qualified_channels,\n',
    )
    replace_once(
        path,
        '            "canSelect": snapshot.available,\n',
        '            "canSelect": bool(snapshot.available and playback_bindings),\n',
    )
    replace_once(
        path,
        '            "manufacturer": "",\n            "product": "",\n',
        '            "manufacturer": "",\n            "product": "",\n            "deviceCategory": "system",\n            "deviceCategoryLabel": "System Output",\n            "classificationConfidence": "high",\n            "classificationReason": "desktop-managed shared output",\n            "playbackEndpointCount": 0,\n            "captureCapable": False,\n',
    )
    replace_once(
        path,
        '            "capabilityEvidenceLabel": "Not applicable",\n',
        '            "capabilityEvidenceLabel": "Not applicable",\n            "qualifiedCapabilitySummary": "System managed",\n            "qualifiedRates": [],\n            "qualifiedFormats": [],\n            "qualifiedChannels": [],\n',
    )
    replace_once(
        path,
        """    devices = Property(\n        list, lambda self: self._get(\"devices\", []), notify=state_changed\n    )\n""",
        """    devices = Property(\n        list, lambda self: self._get(\"devices\", []), notify=state_changed\n    )\n    deviceGroups = Property(\n        list, lambda self: self._get(\"deviceGroups\", []), notify=state_changed\n    )\n""",
    )


def create_group_qml() -> None:
    create(
        "src/michi/presentation/qml/components/AudioOutputDeviceGroup.qml",
        '''import QtQuick\nimport QtQuick.Controls.Basic\nimport QtQuick.Layouts\nimport "../primitives"\nimport "../theme"\n\nColumnLayout {\n    id: root\n    property var group: ({})\n    property var signalPath: []\n    property var reasonCodes: []\n    property bool expanded: !(root.group.collapsedByDefault || false)\n    signal selectionRequested(string stableDeviceId)\n    spacing: MichiSpacing.xs\n\n    Button {\n        id: header\n        objectName: "audioOutputGroup_" + (root.group.groupId || "group")\n        Layout.fillWidth: true\n        visible: (root.group.label || "") !== ""\n        implicitHeight: 38\n        focusPolicy: Qt.StrongFocus\n        hoverEnabled: true\n        onClicked: root.expanded = !root.expanded\n        Keys.onReturnPressed: header.clicked()\n        Keys.onEnterPressed: header.clicked()\n        Accessible.name: (root.expanded ? qsTr("Collapse ") : qsTr("Expand "))\n            + (root.group.label || qsTr("audio outputs"))\n\n        contentItem: RowLayout {\n            spacing: MichiSpacing.sm\n            MichiText {\n                Layout.fillWidth: true\n                text: root.group.label || ""\n                role: "primary"\n                font.weight: Font.DemiBold\n            }\n            MichiText {\n                text: qsTr("%1 output(s)").arg((root.group.rows || []).length)\n                role: "secondary"\n            }\n            MichiText {\n                text: root.expanded ? "▾" : "›"\n                role: "secondary"\n            }\n        }\n        background: Rectangle {\n            radius: MichiRadius.sm\n            color: header.hovered ? MichiSemanticColors.surfaceHover : "transparent"\n            border.width: header.visualFocus ? 1 : 0\n            border.color: MichiSemanticColors.focusRing\n        }\n    }\n\n    MichiText {\n        visible: root.expanded && (root.group.description || "") !== ""\n        Layout.fillWidth: true\n        text: root.group.description || ""\n        role: "secondary"\n        wrapMode: Text.WordWrap\n    }\n\n    Repeater {\n        model: root.expanded ? (root.group.rows || []) : []\n        delegate: DacDeviceCard {\n            id: card\n            required property var modelData\n            Layout.fillWidth: true\n            device: card.modelData\n            signalPath: card.modelData.active ? root.signalPath : []\n            reasonCodes: card.modelData.active ? root.reasonCodes : []\n            onSelectionRequested: stableDeviceId => root.selectionRequested(stableDeviceId)\n        }\n    }\n}\n''',
    )


def replace_settings_qml() -> None:
    path = "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml"
    payload = text(path)
    payload = payload.replace("    property var devices: []\n", "    property var devices: []\n    property var deviceGroups: []\n", 1)
    old = '''    function pathModeIndex() {\n'''
    new = '''    function effectiveGroups() {\n        if (root.deviceGroups && root.deviceGroups.length > 0)\n            return root.deviceGroups\n        return [{\n            "groupId": "legacy",\n            "label": "",\n            "description": "",\n            "collapsedByDefault": false,\n            "rows": root.devices\n        }]\n    }\n\n    function hasHardwareOutput() {\n        for (var i = 0; i < root.devices.length; ++i) {\n            if (!root.devices[i].isShared)\n                return true\n        }\n        return false\n    }\n\n    function pathModeIndex() {\n'''
    if old not in payload:
        raise PatchError(f"{path}: pathModeIndex marker missing")
    payload = payload.replace(old, new, 1)
    start = payload.find('            ColumnLayout {\n                id: deviceCards')
    end = payload.find('            MichiText {\n                Layout.fillWidth: true\n                text: qsTr("Signal Truth', start)
    if start < 0 or end < 0:
        raise PatchError(f"{path}: device card region markers missing")
    region = '''            ColumnLayout {\n                id: deviceCards\n                objectName: "audioOutputDeviceCards"\n                Layout.fillWidth: true\n                spacing: MichiSpacing.md\n\n                Repeater {\n                    objectName: "audioOutputDeviceGroupRepeater"\n                    model: root.effectiveGroups()\n                    delegate: AudioOutputDeviceGroup {\n                        id: outputGroup\n                        required property var modelData\n                        Layout.fillWidth: true\n                        group: outputGroup.modelData\n                        signalPath: root.signalPath\n                        reasonCodes: root.signalTruthReasonCodes\n                        onSelectionRequested: stableDeviceId => {\n                            if (stableDeviceId === "")\n                                root.sharedSelectionRequested()\n                            else\n                                root.deviceSelectionRequested(stableDeviceId)\n                        }\n                    }\n                }\n            }\n\n            ColumnLayout {\n                visible: !root.hasHardwareOutput()\n                Layout.fillWidth: true\n                spacing: MichiSpacing.xs\n                MichiText {\n                    text: qsTr("No hardware audio outputs detected")\n                    role: "primary"\n                }\n                MichiText {\n                    Layout.fillWidth: true\n                    text: qsTr("System Output remains available. Connect any playback-capable DAC, audio interface or sound device to add it here.")\n                    role: "secondary"\n                    wrapMode: Text.WordWrap\n                }\n            }\n\n'''
    payload = payload[:start] + region + payload[end:]
    write(path, payload)


def replace_popup_qml() -> None:
    path = "src/michi/presentation/qml/player/AudioOutputPopup.qml"
    create_payload = '''pragma ComponentBehavior: Bound\n\nimport QtQuick\nimport QtQuick.Controls.Basic\nimport QtQuick.Layouts\nimport "../controls"\nimport "../primitives"\nimport "../theme"\n\nPopup {\n    id: root\n    objectName: "AudioOutputPopup"\n    property var devices: []\n    property var deviceGroups: []\n    property string signalTruthLabel: qsTr("Not verified")\n    property string failureTitle: ""\n    property var focusReturnTarget: null\n    property bool displayAudioExpanded: false\n\n    signal deviceSelectionRequested(string stableDeviceId)\n    signal sharedSelectionRequested()\n    signal settingsRequested()\n\n    padding: MichiSpacing.lg\n    modal: false\n    focus: true\n    closePolicy: Popup.CloseOnEscape | Popup.CloseOnPressOutside\n    width: 380\n    enter: Transition {\n        enabled: !MichiAccessibility.reducedMotion\n        NumberAnimation { property: "opacity"; from: 0; to: 1; duration: MichiMotion.panel }\n    }\n    exit: Transition {\n        enabled: !MichiAccessibility.reducedMotion\n        NumberAnimation { property: "opacity"; from: 1; to: 0; duration: MichiMotion.standard }\n    }\n    background: MichiGlassSurface {\n        elevation: "elevated"\n        contentPadding: 0\n        tileSeed: 11\n    }\n\n    function groups() {\n        if (root.deviceGroups && root.deviceGroups.length > 0)\n            return root.deviceGroups\n        return [{"groupId": "legacy", "label": "", "collapsedByDefault": false, "rows": root.devices}]\n    }\n\n    function visibleRows() {\n        var rows = []\n        var source = root.groups()\n        for (var g = 0; g < source.length; ++g) {\n            var group = source[g]\n            var groupRows = group.rows || []\n            if (group.groupId === "system") {\n                for (var s = 0; s < groupRows.length; ++s)\n                    rows.push(groupRows[s])\n                continue\n            }\n            if (group.groupId === "display") {\n                rows.push({\n                    "isGroupHeader": true,\n                    "stableDeviceId": "__display_audio__",\n                    "displayName": group.label || qsTr("Display Audio"),\n                    "statusLabel": qsTr("%1 output(s) · %2").arg(groupRows.length).arg(root.displayAudioExpanded ? qsTr("Collapse") : qsTr("Expand")),\n                    "transportLabel": qsTr("HDMI / DisplayPort"),\n                    "available": true,\n                    "active": false,\n                    "selected": false,\n                    "canSelect": true,\n                    "signalTruthLabel": ""\n                })\n                if (!root.displayAudioExpanded)\n                    continue\n            } else if ((group.label || "") !== "") {\n                rows.push({\n                    "isGroupHeader": true,\n                    "stableDeviceId": "__header_" + group.groupId,\n                    "displayName": group.label,\n                    "statusLabel": group.description || "",\n                    "transportLabel": "",\n                    "available": true,\n                    "active": false,\n                    "selected": false,\n                    "canSelect": false,\n                    "signalTruthLabel": ""\n                })\n            }\n            for (var i = 0; i < groupRows.length; ++i)\n                rows.push(groupRows[i])\n        }\n        return rows\n    }\n\n    onOpened: {\n        for (var i = 0; i < outputRows.count; i++) {\n            var item = outputRows.itemAt(i)\n            if (item && item.enabled) {\n                item.forceActiveFocus()\n                break\n            }\n        }\n    }\n    onClosed: {\n        if (root.focusReturnTarget)\n            root.focusReturnTarget.forceActiveFocus()\n    }\n\n    function navigate(fromIndex, delta) {\n        var i = fromIndex + delta\n        while (i >= 0 && i < outputRows.count) {\n            var item = outputRows.itemAt(i)\n            if (item && item.enabled)\n                return item\n            i += delta\n        }\n        return null\n    }\n\n    contentItem: ColumnLayout {\n        spacing: MichiSpacing.sm\n        MichiText {\n            text: qsTr("Audio Output")\n            role: "heading"\n            Layout.fillWidth: true\n        }\n\n        Repeater {\n            id: outputRows\n            objectName: "audioOutputPopupRepeater"\n            model: root.visibleRows()\n            delegate: Button {\n                id: row\n                required property var modelData\n                required property int index\n                objectName: "outputPopupRow_" + (modelData.stableDeviceId || "shared")\n                Layout.fillWidth: true\n                Layout.preferredHeight: modelData.isGroupHeader ? 42 : 54\n                focusPolicy: Qt.StrongFocus\n                hoverEnabled: true\n                enabled: modelData.canSelect\n                onClicked: {\n                    if (row.modelData.isGroupHeader) {\n                        if (row.modelData.stableDeviceId === "__display_audio__")\n                            root.displayAudioExpanded = !root.displayAudioExpanded\n                    } else if (row.modelData.isShared) {\n                        root.sharedSelectionRequested()\n                    } else {\n                        root.deviceSelectionRequested(row.modelData.stableDeviceId)\n                    }\n                }\n                Keys.onReturnPressed: row.clicked()\n                Keys.onEnterPressed: row.clicked()\n                KeyNavigation.up: root.navigate(index, -1)\n                KeyNavigation.down: root.navigate(index, 1)\n                Accessible.name: row.modelData.displayName + " — " + row.modelData.statusLabel\n                Accessible.description: row.modelData.transportLabel || ""\n\n                contentItem: RowLayout {\n                    spacing: MichiSpacing.sm\n                    Rectangle {\n                        visible: !row.modelData.isGroupHeader\n                        Layout.preferredWidth: 10\n                        Layout.preferredHeight: 10\n                        radius: 5\n                        color: row.modelData.active ? MichiPalette.auroraCyan : "transparent"\n                        border.width: row.modelData.active ? 0 : 1\n                        border.color: row.modelData.available ? MichiPalette.textMuted : MichiPalette.warning\n                    }\n                    ColumnLayout {\n                        Layout.fillWidth: true\n                        spacing: 0\n                        MichiText {\n                            Layout.fillWidth: true\n                            text: row.modelData.displayName\n                            role: row.modelData.isGroupHeader ? "secondary" : "primary"\n                            font.weight: row.modelData.isGroupHeader ? Font.DemiBold : Font.Normal\n                            elide: Text.ElideRight\n                        }\n                        MichiText {\n                            Layout.fillWidth: true\n                            text: row.modelData.statusLabel + ((row.modelData.transportLabel || "") !== "" ? " · " + row.modelData.transportLabel : "")\n                            role: "technical"\n                            technical: true\n                            elide: Text.ElideRight\n                        }\n                    }\n                    MichiText {\n                        visible: !row.modelData.isGroupHeader && row.modelData.active\n                        text: row.modelData.signalTruthLabel\n                        role: "technical"\n                        technical: true\n                    }\n                    MichiText {\n                        visible: row.modelData.stableDeviceId === "__display_audio__"\n                        text: root.displayAudioExpanded ? "▾" : "›"\n                        role: "secondary"\n                    }\n                }\n                background: Rectangle {\n                    radius: MichiRadius.sm\n                    color: row.pressed ? MichiSemanticColors.surfacePressed\n                        : row.hovered ? MichiSemanticColors.surfaceHover : "transparent"\n                    border.width: row.visualFocus || row.modelData.selected ? 1 : 0\n                    border.color: row.visualFocus ? MichiSemanticColors.focusRing : MichiSemanticColors.borderStrong\n                }\n            }\n        }\n\n        MichiText {\n            visible: root.failureTitle !== ""\n            Layout.fillWidth: true\n            text: root.failureTitle\n            role: "secondary"\n            wrapMode: Text.WordWrap\n        }\n\n        MichiButton {\n            objectName: "openAudioOutputSettingsButton"\n            Layout.fillWidth: true\n            text: qsTr("Audio Output Settings")\n            variant: "secondary"\n            onClicked: root.settingsRequested()\n        }\n    }\n}\n'''
    write(path, create_payload)


def apply_qml_wiring() -> None:
    replace_once(
        "src/michi/presentation/qml/player/NowPlayingBar.qml",
        "    property var outputDevices: []\n",
        "    property var outputDevices: []\n    property var outputDeviceGroups: []\n",
    )
    replace_once(
        "src/michi/presentation/qml/player/NowPlayingBar.qml",
        "                devices: root.outputDevices\n",
        "                devices: root.outputDevices\n                deviceGroups: root.outputDeviceGroups\n",
    )
    replace_once(
        "src/michi/presentation/qml/shell/AppShell.qml",
        "        outputDevices: audioOutput.devices\n",
        "        outputDevices: audioOutput.devices\n        outputDeviceGroups: audioOutput.deviceGroups\n",
    )
    replace_once(
        "src/michi/presentation/qml/views/SettingsView.qml",
        "                devices: audioOutput.devices\n",
        "                devices: audioOutput.devices\n                deviceGroups: audioOutput.deviceGroups\n",
    )


def replace_device_card_qml() -> None:
    path = "src/michi/presentation/qml/components/DacDeviceCard.qml"
    payload = text(path)
    replace = '''                    MichiText {\n                        Layout.fillWidth: true\n                        text: root.device.displayName || qsTr("Audio Output")\n                        role: "heading"\n                        elide: Text.ElideRight\n                    }\n                    MichiText {\n                        text: root.device.connectionLabel || qsTr("Unavailable")\n                        role: "secondary"\n                    }\n'''
    new = '''                    ColumnLayout {\n                        Layout.fillWidth: true\n                        spacing: 0\n                        MichiText {\n                            Layout.fillWidth: true\n                            text: root.device.displayName || qsTr("Audio Output")\n                            role: "heading"\n                            elide: Text.ElideRight\n                        }\n                        MichiText {\n                            Layout.fillWidth: true\n                            text: (root.device.deviceCategoryLabel || qsTr("Audio Output"))\n                                + ((root.device.qualifiedCapabilitySummary || "") !== ""\n                                    ? " · " + root.device.qualifiedCapabilitySummary : "")\n                            role: "secondary"\n                            elide: Text.ElideRight\n                        }\n                    }\n                    MichiText {\n                        text: root.device.connectionLabel || qsTr("Unavailable")\n                        role: "secondary"\n                    }\n'''
    if payload.count(replace) != 1:
        raise PatchError(f"{path}: heading region mismatch")
    payload = payload.replace(replace, new, 1)
    payload = payload.replace(
        '''                    MichiStatusChip {\n                        text: root.device.signalTruthLabel || qsTr("Not verified")\n                        tone: root.device.signalTruthLabel === "Output mismatch"\n                            ? "error" : "neutral"\n                    }\n''',
        '''                    MichiStatusChip {\n                        visible: root.device.active\n                        text: root.device.signalTruthLabel || qsTr("Not verified")\n                        tone: root.device.signalTruthLabel === "Output mismatch"\n                            ? "error" : "neutral"\n                    }\n''',
        1,
    )
    write(path, payload)


def apply_diagnostics_qml() -> None:
    path = "src/michi/presentation/qml/components/DacDiagnosticsDisclosure.qml"
    replace_once(
        path,
        """        MichiDivider { Layout.fillWidth: true }\n        MichiText {\n""",
        '''        MichiDivider { Layout.fillWidth: true }\n        MichiText {\n            Layout.fillWidth: true\n            text: qsTr("Identity: %1 · %2")\n                .arg(root.device.manufacturer || qsTr("Unknown manufacturer"))\n                .arg(root.device.product || qsTr("Unknown model"))\n            role: "technical"\n            technical: true\n            wrapMode: Text.WordWrap\n        }\n        MichiText {\n            Layout.fillWidth: true\n            text: qsTr("Class: %1 · confidence %2")\n                .arg(root.device.deviceCategoryLabel || qsTr("Audio"))\n                .arg(root.device.classificationConfidence || "—")\n            role: "technical"\n            technical: true\n            wrapMode: Text.WordWrap\n        }\n        MichiText {\n            Layout.fillWidth: true\n            text: qsTr("Playback endpoints: %1 · capture capability: %2")\n                .arg(root.device.playbackEndpointCount || 0)\n                .arg(root.device.captureCapable ? qsTr("yes") : qsTr("no / not observed"))\n            role: "technical"\n            technical: true\n        }\n        MichiText {\n            Layout.fillWidth: true\n            text: qsTr("Qualified playback capabilities: %1")\n                .arg(root.device.qualifiedCapabilitySummary || qsTr("Not yet qualified"))\n            role: "technical"\n            technical: true\n            wrapMode: Text.WordWrap\n        }\n        MichiText {\n''',
    )


def apply_qualification_context_api() -> None:
    path = "src/michi/application/dac_qualification_service.py"
    replace_once(
        path,
        """    def current_environment_fingerprint(self, stable_device_id: str) -> str:\n        if self._environment_fingerprint is not None:\n            return self._environment_fingerprint()\n        context = (\n            self._environment_context(stable_device_id)\n            if self._environment_context is not None\n            else default_environment_context(stable_device_id)\n        )\n        return default_environment_fingerprint(context)\n\n""",
        '''    def current_environment_context(\n        self, stable_device_id: str\n    ) -> QualificationEnvironmentContext:\n        """Return the exact context used for environment-scoped qualification.\n\n        Evidence tooling must never call ``default_environment_fingerprint()``\n        without this device-bound context and then label the result physical.\n        """\n        if self._environment_context is not None:\n            return self._environment_context(stable_device_id)\n        return default_environment_context(stable_device_id)\n\n    def current_environment_fingerprint(self, stable_device_id: str) -> str:\n        if self._environment_fingerprint is not None:\n            return self._environment_fingerprint()\n        return default_environment_fingerprint(\n            self.current_environment_context(stable_device_id)\n        )\n\n''',
    )


def apply_r110_harness_context() -> None:
    path = "scripts/dac_r110_field_suite.py"
    replace_once(path, "import argparse\n", "import argparse\nfrom dataclasses import asdict\n")
    replace_once(
        path,
        '''    try:\n        from michi.application.dac_qualification_service import (\n            default_environment_fingerprint,\n        )\n\n        _env_fingerprint = default_environment_fingerprint()\n    except Exception:  # noqa: BLE001 — provenance boundary, never mask the run\n        _env_fingerprint = ""\n\n''',
        "",
    )
    replace_once(
        path,
        '        "environment_fingerprint": _env_fingerprint,\n',
        '        "environment_fingerprint": None,\n        "environment_context": None,\n',
    )
    replace_once(
        path,
        """        _validate_device(container, device_id=args.device_id, locator=args.locator)\n        container._aob.select_device(args.device_id)\n""",
        '''        _validate_device(container, device_id=args.device_id, locator=args.locator)\n        qualification = container._aob._qualification\n        if qualification is None:\n            raise SystemExit("canonical DAC qualification authority unavailable")\n        environment_context = qualification.current_environment_context(args.device_id)\n        if not environment_context.complete_for_current_evidence:\n            raise SystemExit(\n                "device-bound qualification environment is incomplete; "\n                "refusing to publish an unbound environment fingerprint"\n            )\n        report["environment_context"] = asdict(environment_context)\n        report["environment_fingerprint"] = qualification.current_environment_fingerprint(\n            args.device_id\n        )\n        container._aob.select_device(args.device_id)\n''',
    )


def apply_field_schema_test() -> None:
    path = "tests/dac/test_v35_110_field_schema.py"
    replace_once(
        path,
        '''def test_fs110_05b_environment_fingerprint_uses_the_canonical_authority() -> None:\n    source = _harness_source()\n    assert "from michi.application.dac_qualification_service import (" in source\n    assert "default_environment_fingerprint()" in source\n    assert '"environment_fingerprint": _env_fingerprint,' in source\n\n''',
        '''def test_fs110_05b_environment_fingerprint_is_device_bound() -> None:\n    source = _harness_source()\n    assert "default_environment_fingerprint()" not in source\n    assert "current_environment_context(args.device_id)" in source\n    assert "current_environment_fingerprint(" in source\n    assert "complete_for_current_evidence" in source\n    assert '"environment_context": None,' in source\n    assert '"environment_fingerprint": None,' in source\n\n''',
    )


def apply_test_fixture_capture() -> None:
    path = "tests/dac/_fixtures.py"
    replace_once(
        path,
        """    playback_pcms: tuple[int, ...] = (0,)\n    platform_path: str = \"platform/michi-sound\"\n""",
        """    playback_pcms: tuple[int, ...] = (0,)\n    capture_pcms: tuple[int, ...] = ()\n    platform_path: str = \"platform/michi-sound\"\n""",
    )
    replace_once(
        path,
        """        card_link = class_sound / f\"card{card.card_index}\"\n""",
        '''        for pcm in card.capture_pcms:\n            pcm_name = f"pcmC{card.card_index}D{pcm}c"\n            (card_dir / pcm_name).mkdir(exist_ok=True)\n            pcm_link = class_sound / pcm_name\n            if not pcm_link.exists():\n                relative_card = card_dir.relative_to(root)\n                pcm_link.symlink_to(f"../../{relative_card}/{pcm_name}")\n        card_link = class_sound / f"card{card.card_index}"\n''',
    )


def update_identity_tests() -> None:
    path = "tests/dac/test_v34_device_identity.py"
    replace_once(
        path,
        '''    stable_id = "usb:2622:0105:DX5ABC123"\n    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is None\n''',
        '''    stable_id = "usb:2622:0105:DX5ABC123"\n    assert registry.snapshot() == (), "capture/non-playback USB is not an Audio Output"\n    assert registry.device_snapshots() == (), "unknown non-playback USB is not retained"\n    assert registry.binding_for(stable_id, BindingKind.ALSA_PCM) is None\n''',
    )
    replace_once(
        path,
        '''        usb_devices=(\n            UsbDevice("2-1", "2622", "0105"),\n            UsbDevice("2-2", "2622", "0105"),\n        ),\n    )\n''',
        '''        usb_devices=(\n            UsbDevice("2-1", "2622", "0105"),\n            UsbDevice("2-2", "2622", "0105"),\n        ),\n        cards=(\n            AlsaCard(1, "DAC1", "2-1"),\n            AlsaCard(2, "DAC2", "2-2"),\n        ),\n    )\n''',
    )
    replace_once(
        path,
        '''        usb_devices=(\n            UsbDevice("2-1", "2622", "0105", serial="SAME123"),\n            UsbDevice("2-2", "2622", "0105", serial="SAME123"),\n        ),\n    )\n''',
        '''        usb_devices=(\n            UsbDevice("2-1", "2622", "0105", serial="SAME123"),\n            UsbDevice("2-2", "2622", "0105", serial="SAME123"),\n        ),\n        cards=(\n            AlsaCard(1, "DAC1", "2-1"),\n            AlsaCard(2, "DAC2", "2-2"),\n        ),\n    )\n''',
    )
    replace_once(
        path,
        '''        usb_devices=(UsbDevice("2-1", "2622", "0105", serial="00000000"),),\n    )\n''',
        '''        usb_devices=(UsbDevice("2-1", "2622", "0105", serial="00000000"),),\n        cards=(AlsaCard(1, "DAC", "2-1"),),\n    )\n''',
    )
    replace_once(
        path,
        '''    assert [i.stable_device_id for i in registry.snapshot()] == [stable_id]\n    assert registry.bindings_for(stable_id, BindingKind.ALSA_PCM) == ()\n    assert registry.generation_for(stable_id) > generation_before\n''',
        '''    assert registry.snapshot() == ()\n    retained = {item.identity.stable_device_id: item for item in registry.device_snapshots()}\n    assert retained[stable_id].available is False\n    assert retained[stable_id].bindings == ()\n    assert registry.bindings_for(stable_id, BindingKind.ALSA_PCM) == ()\n    assert registry.generation_for(stable_id) > generation_before\n''',
    )
    replace_once(
        path,
        '''    stable_id = registry.snapshot()[0].stable_device_id\n    generation_before = registry.generation_for(stable_id)\n    assert registry.bindings_for(stable_id, BindingKind.ALSA_PCM) == ()\n\n    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))\n    _ingest(registry, sysfs_root)\n\n    assert registry.generation_for(stable_id) > generation_before\n''',
        '''    stable_id = "usb:2622:0105:DX5ABC123"\n    assert registry.snapshot() == ()\n    assert registry.device_snapshots() == ()\n\n    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))\n    _ingest(registry, sysfs_root)\n\n    generation_after = registry.generation_for(stable_id)\n    assert generation_after is not None\n''',
    )
    replace_once(
        path,
        '''    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card(()),))\n    registry = AudioDeviceRegistry()\n    _ingest(registry, sysfs_root)\n    stable_id = registry.snapshot()[0].stable_device_id\n    generation_before = registry.generation_for(stable_id)\n    assert registry.bindings_for(stable_id) == ()\n\n    remove_usb_device(sysfs_root, "2-1")\n    _ingest(registry, sysfs_root)\n\n    assert registry.snapshot() == ()\n    assert registry.generation_for(stable_id) == generation_before + 1, (\n        "available True->False es un cambio topológico aunque bindings==()"\n    )\n\n    # segundo rescan con el device todavía ausente: NO incrementa de nuevo\n    _ingest(registry, sysfs_root)\n    assert registry.generation_for(stable_id) == generation_before + 1\n''',
        '''    build_linux_sysfs(sysfs_root, usb_devices=(DX5,), cards=(_single_card((0,)),))\n    registry = AudioDeviceRegistry()\n    _ingest(registry, sysfs_root)\n    stable_id = registry.snapshot()[0].stable_device_id\n    generation_before = registry.generation_for(stable_id)\n\n    # Playback disappears while the physical USB identity remains. A known\n    # audio device is retained as disconnected exactly once.\n    remove_playback_pcm(sysfs_root, 1, 0)\n    _ingest(registry, sysfs_root)\n\n    assert registry.snapshot() == ()\n    retained = {item.identity.stable_device_id: item for item in registry.device_snapshots()}\n    assert retained[stable_id].available is False\n    assert registry.generation_for(stable_id) == generation_before + 1\n\n    _ingest(registry, sysfs_root)\n    assert registry.generation_for(stable_id) == generation_before + 1\n''',
    )


def create_universal_tests() -> None:
    create(
        "tests/dac/test_v35_010r1_universal_audio_discovery.py",
        '''"""DAC-V35-010R1 — universal playback admission + semantic projection.

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


def test_unknown_usb_with_real_playback_is_admitted_without_whitelist(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    unknown = UsbDevice("9-4", "dead", "beef", serial="UNSEEN-DAC-1")
    build_linux_sysfs(root, usb_devices=(unknown,), cards=(AlsaCard(3, "Mystery", "9-4"),))
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshots = registry.device_snapshots()
    assert len(snapshots) == 1
    assert snapshots[0].identity.vendor_id == "dead"
    assert snapshots[0].identity.product_id == "beef"
    assert has_current_playback(snapshots[0])
    assert classify_audio_device(snapshots[0]).category is AudioDeviceCategory.EXTERNAL_AUDIO


def test_arbitrary_usb_without_playback_never_enters_audio_output(tmp_path: Path) -> None:
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


def test_composite_playback_capture_usb_is_admitted_as_interface(tmp_path: Path) -> None:
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
    assert snapshot.capture_capable is True
    assert classify_audio_device(snapshot).category is AudioDeviceCategory.AUDIO_INTERFACE


def test_non_usb_motherboard_playback_remains_first_class(tmp_path: Path) -> None:
    root = make_roots(tmp_path)
    build_linux_sysfs(
        root,
        cards=(AlsaCard(0, "Generic", None, playback_pcms=(0,), platform_path="pci/hda"),),
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
        cards=(AlsaCard(0, "HDMI", None, playback_pcms=(3, 7), platform_path="pci/gpu"),),
    )
    registry = AudioDeviceRegistry()
    _ingest(registry, root)
    snapshots = registry.device_snapshots()
    assert len(snapshots) == 2
    assert all(classify_audio_device(item).category is AudioDeviceCategory.DISPLAY_AUDIO for item in snapshots)


def test_known_audio_identity_losing_playback_is_retained_disconnected(tmp_path: Path) -> None:
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
    retained = {item.identity.stable_device_id: item for item in registry.device_snapshots()}
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
    popup = (repo / "src/michi/presentation/qml/player/AudioOutputPopup.qml").read_text(encoding="utf-8")
    settings = (repo / "src/michi/presentation/qml/views/AudioOutputSettingsSection.qml").read_text(encoding="utf-8")
    bridge = (repo / "src/michi/presentation/audio_output_bridge.py").read_text(encoding="utf-8")
    assert "property bool displayAudioExpanded: false" in popup
    assert "__display_audio__" in popup
    assert "AudioOutputDeviceGroup" in settings
    assert '("display", "Display Audio"' in bridge
    assert '"HDMI / DisplayPort audio outputs"' in bridge
''',
    )


def apply_verifier_manifest() -> None:
    path = "scripts/verify_dac_m11_4.py"
    replace_once(
        path,
        '    "tests/dac/test_v35_100r12_productive_qualification.py",\n',
        '    "tests/dac/test_v35_100r12_productive_qualification.py",\n    "tests/dac/test_v35_010r1_universal_audio_discovery.py",\n',
    )
    replace_once(
        path,
        '        "michi/application/audio_device_registry.py",\n',
        '        "michi/application/audio_device_registry.py",\n        "michi/application/audio_device_semantics.py",\n        "michi/presentation/qml/components/AudioOutputDeviceGroup.qml",\n',
    )
    replace_once(
        path,
        '    "michi.application.audio_device_registry",\n',
        '    "michi.application.audio_device_registry",\n    "michi.application.audio_device_semantics",\n',
    )


def apply_r110_publication_corrective() -> None:
    ledger = "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/canonical_experiment_ledger.json"
    operator = "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/operator_observation.json"
    lp = json.loads(text(ledger))
    lp["environment"]["device_bound"] = False
    lp["environment"]["status"] = "HISTORICAL_UNBOUND_CONTEXT"
    lp["environment"]["note"] = (
        "The recorded qenv hash was generated from default_environment_context() "
        "with environment:unbound/topology:unbound. It is retained as historical "
        "provenance but MUST NOT be cited as a device-bound environment fingerprint."
    )
    lp["operator_observation"]["audibility"]["scope"] = (
        "expected behavior PASS 12/12: audible on 9 playback rows "
        "(1 Shared + 8 Direct), truthful silence/refusal on 3 Strict 16-bit rows"
    )
    lp["experiments"]["R28"]["evidence"] = (
        "All 12 rows classified through the domain snapshot: 8 Direct rows "
        "DIRECT_CONTAINER_ADAPTED, 3 truthful EXACT_TUPLE_UNSUPPORTED, "
        "1 Shared row correctly not verified"
    )
    lp["experiments"]["R33"]["evidence"] = (
        "physical operator unplug/reconnect: no crash, loss handled, rediscovery "
        "succeeded; automated DAC-V35-080R1.1 gates prove reconnect alone restores "
        "no runtime authority, never autoplays, requires explicit Play and creates "
        "a fresh generation/SignalTruthIdentity"
    )
    lp["experiments"]["R33"]["scope_note"] = (
        "PASS is composite evidence: physical reconnect + existing productive "
        "automated no-autoresume/explicit-Play safety gates. No physical autoplay "
        "was fabricated or inferred."
    )
    write(ledger, json.dumps(lp, indent=2) + "\n")

    op = json.loads(text(operator))
    op["expected_behavior"] = {"answer": "PASS", "scope": "12/12 rows"}
    op["audibility"]["scope"] = "9 playback rows (1 Shared + 8 Direct)"
    op["audibility"]["truthful_refusals"] = (
        "3 Strict 16-bit rows produced no audio because the exact tuple was refused, as expected"
    )
    write(operator, json.dumps(op, indent=2) + "\n")

    create(
        "evidence/dac-v35-110/2026-09-25-smsl-152a85dd-operator-run/publication_correction.json",
        json.dumps(
            {
                "schema_version": 1,
                "kind": "R110 publication integrity correction",
                "base_publication_head": BASE_HEAD,
                "raw_physical_matrices_rewritten": False,
                "corrections": {
                    "direct_positive_rows": {
                        "previous_claim": 9,
                        "correct_value": 8,
                        "derivation": "12 total = 1 Shared + 3 Strict refusals + 8 Direct successes",
                    },
                    "audibility": {
                        "expected_behavior_rows": 12,
                        "audible_playback_rows": 9,
                        "truthful_refusal_rows": 3,
                    },
                    "environment_fingerprint": {
                        "historical_hash_is_device_bound": False,
                        "reason": "captured from default unbound environment context",
                        "corrective": "field harness now requires complete current_environment_context(device_id) before publishing qenv",
                    },
                    "R33": {
                        "physical_component": "unplug/reconnect/rediscovery PASS",
                        "resume_safety_component": "automated DAC-V35-080R1.1 no-autoresume + explicit-Play/fresh-generation gates",
                    },
                },
            },
            indent=2,
        )
        + "\n",
    )

    docs = "docs/M11_4_AUDIOPHILE_OUTPUT_DAC.md"
    replace_once(
        docs,
        "operator audibility PASS on 12/12 rows and physical\n",
        "operator expected-behavior PASS on 12/12 rows (audible on 9 playback rows; "
        "3 Strict 16-bit refusals correctly silent) and physical\n",
    )
    old = (
        "The verdict is device- and environment-scoped\n"
        "(`qenv:v2:sha256:77ee027839ed623943a36912c258ce15550fc4dc746048c0321242fadf124701`):\n"
    )
    new = (
        "The bounded playback verdict is device-scoped. The historical R110 qenv hash\n"
        "was captured from an unbound default environment context and is retained only\n"
        "as provenance; it is **not** a device-bound environment claim. The corrected\n"
        "field harness now requires a complete device-bound qualification context before\n"
        "publishing an environment-scoped fingerprint:\n"
    )
    replace_once(docs, old, new)


def apply_all() -> None:
    apply_domain_observation_extension()
    apply_sysfs_capture_evidence()
    apply_registry_admission()
    create_semantics_module()
    apply_selection_firewall()
    apply_failure_copy()
    apply_bridge_projection()
    create_group_qml()
    replace_settings_qml()
    replace_popup_qml()
    apply_qml_wiring()
    replace_device_card_qml()
    apply_diagnostics_qml()
    apply_qualification_context_api()
    apply_r110_harness_context()
    apply_field_schema_test()
    apply_test_fixture_capture()
    update_identity_tests()
    create_universal_tests()
    apply_verifier_manifest()
    apply_r110_publication_corrective()


def main() -> int:
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--check", action="store_true")
    mode.add_argument("--apply", action="store_true")
    parser.add_argument("--keep-bootstrap", action="store_true")
    args = parser.parse_args()

    global DRY_RUN
    try:
        verify_base()
        if args.check:
            DRY_RUN = True
            apply_all()
            print("PRECHECK PASS")
            print(f"BASE_HEAD={BASE_HEAD}")
            print(f"verified_blobs={len(EXPECTED_BLOBS)}")
            print(f"validated_transformations={len(VIRTUAL_FILES)} files")
            print(f"new_files={len(CREATED_FILES)}")
            return 0
        apply_all()
        # Cheap syntax checks. Full repository gates belong to the caller/CI.
        for relative in (
            "src/michi/domain/audio_device.py",
            "src/michi/infrastructure/audio_devices/sysfs_snapshot.py",
            "src/michi/application/audio_device_registry.py",
            "src/michi/application/audio_device_semantics.py",
            "src/michi/application/audio_output_selection_coordinator.py",
            "src/michi/application/playback_failure.py",
            "src/michi/presentation/audio_output_bridge.py",
            "src/michi/application/dac_qualification_service.py",
            "scripts/dac_r110_field_suite.py",
            "tests/dac/test_v35_010r1_universal_audio_discovery.py",
        ):
            completed = subprocess.run(
                [sys.executable, "-m", "py_compile", str(ROOT / relative)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            if completed.returncode != 0:
                raise PatchError(f"py_compile failed for {relative}: {completed.stderr}")
        if not args.keep_bootstrap:
            SELF.unlink()
        print("APPLY PASS")
        print("Run the contract gates before committing. Core R110 playback logic was not reopened.")
        return 0
    except PatchError as exc:
        print(f"PATCH ERROR: {exc}", file=sys.stderr)
        print("No fuzzy fallback is authorized. Restore the base tree and regenerate if needed.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
