"""AP2-F02 — device knowledge as descriptive enrichment with provenance.

Contract anchors: R11-F02 (device knowledge without admission authority),
R11-G02 (authority map), spec §126 (evidence vocabulary), §188 (acceptance:
corrupt MAHKB must not block playback, unknown devices stay usable, every
displayed enrichment has provenance).
"""

from __future__ import annotations

import ast
import dataclasses
import sys
from pathlib import Path

import pytest

from michi.application.audio_device_knowledge_service import (
    AudioDeviceKnowledgeService,
)
from michi.application.audio_device_registry import AudioDeviceSnapshot
from michi.application.audio_output_ports import VolumeAuthority
from michi.domain.audio_device import (
    AudioDeviceBinding,
    AudioDeviceIdentity,
    BindingKind,
    IdentityConfidence,
)
from michi.domain.audio_device_knowledge import (
    DeviceKnowledge,
    EvidenceConfidence,
    EvidenceOrigin,
    EvidenceResolution,
    EvidenceSource,
)
from michi.presentation.audio_output_bridge import AudioOutputBridge

DOMAIN_MODULE = Path(sys.modules["michi.domain.audio_device_knowledge"].__file__)
SERVICE_MODULE = Path(
    sys.modules["michi.application.audio_device_knowledge_service"].__file__
)

STABLE_ID = "usb:152a:85dd:3-3.3.2"


def _imported_modules(source_path: Path) -> list[str]:
    tree = ast.parse(source_path.read_text(encoding="utf-8"))
    modules: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom):
            modules.append("." * node.level + (node.module or ""))
    return modules


def _source(
    *,
    origin: EvidenceOrigin = EvidenceOrigin.MICHI_KB,
    confidence: EvidenceConfidence = EvidenceConfidence.STRONG,
    ref: str = "mahkb:entries/0",
    version: str | None = "2026.10",
) -> EvidenceSource:
    return EvidenceSource(
        origin=origin, confidence=confidence, source_ref=ref, source_version=version
    )


def _document_entry(
    *,
    vid: str | None = "152a",
    pid: str | None = "85dd",
    stable_device_id: str | None = None,
    manufacturer: str | None = "SMSL",
    product: str | None = "SMSL USB AUDIO",
    capabilities: object = None,
    provenance: object = None,
) -> dict:
    match: dict = {}
    if vid is not None:
        match["vid"] = vid
    if pid is not None:
        match["pid"] = pid
    if stable_device_id is not None:
        match["stable_device_id"] = stable_device_id
    entry: dict = {
        "match": match,
        "identity": {
            "commercial_manufacturer": manufacturer,
            "commercial_model": product,
        },
        "declared_capabilities": (
            {"DSD256": True, "768kHz": True} if capabilities is None else capabilities
        ),
        "provenance": (
            [
                {
                    "origin": "michi_kb",
                    "confidence": "strong",
                    "source_ref": "mahkb:entries/0",
                }
            ]
            if provenance is None
            else provenance
        ),
    }
    return entry


def _snapshot(
    *, stable_id: str = STABLE_ID, available: bool = True
) -> AudioDeviceSnapshot:
    identity = AudioDeviceIdentity(
        stable_device_id=stable_id,
        vendor_id="152a",
        product_id="85dd",
        serial=None,
        manufacturer="SMSL",
        product="SMSL USB AUDIO",
        physical_path="3-3.3.2",
        bus="usb",
        bcd_device="0x0100",
        confidence=IdentityConfidence.HIGH,
    )
    binding = AudioDeviceBinding(
        kind=BindingKind.ALSA_PCM,
        locator="hw:CARD=AUDIO,DEV=0",
        generation=1,
        currently_available=True,
    )
    return AudioDeviceSnapshot(
        identity=identity,
        available=available,
        generation=1,
        bindings=(binding,),
    )


class _Volume:
    authority = VolumeAuthority.FIXED
    volume_adjustable = False
    volume_label = "Fixed / Unity"


class _Playback:
    def subscribe_changed(self, _callback) -> None: ...

    def unsubscribe_changed(self, _callback) -> None: ...


def _row(
    bridge: AudioOutputBridge,
    snapshot: AudioDeviceSnapshot,
) -> dict:
    return bridge._device_row(
        snapshot,
        profiles=(),
        selected_device_id=None,
        selected_profile_id=None,
        active_device_id=None,
        reconnecting=False,
        truth=None,
        truth_label="Not verified",
        last_failure_code=None,
        identity_presentation=("SMSL USB AUDIO", ""),
    )


# --------------------------------------------------------------------------- #
# domain vocabulary
# --------------------------------------------------------------------------- #


def test_evidence_vocabulary_matches_spec_126() -> None:
    assert [(member.name, member.value) for member in EvidenceOrigin] == [
        ("SYSFS", "sysfs"),
        ("USB_DESCRIPTOR", "usb_descriptor"),
        ("ALSA", "alsa"),
        ("UDEV_HWDB", "udev_hwdb"),
        ("USB_IDS", "usb_ids"),
        ("KERNEL_KNOWLEDGE", "kernel_knowledge"),
        ("MICHI_KB", "michi_kb"),
        ("PHYSICAL_QUALIFICATION", "physical_qualification"),
        ("RUNTIME", "runtime"),
        ("MANUFACTURER_DECLARED", "manufacturer_declared"),
    ]
    assert [member.value for member in EvidenceConfidence] == [
        "authoritative",
        "strong",
        "corroborated",
        "weak",
        "unknown",
    ]
    assert [member.value for member in EvidenceResolution] == [
        "resolved",
        "unknown",
        "conflicted",
        "stale",
        "not_applicable",
    ]


def test_evidence_source_requires_a_concrete_ref() -> None:
    with pytest.raises(ValueError):
        EvidenceSource(
            origin=EvidenceOrigin.MICHI_KB,
            confidence=EvidenceConfidence.STRONG,
            source_ref="   ",
        )


def test_evidence_source_is_immutable() -> None:
    source = _source()
    with pytest.raises(dataclasses.FrozenInstanceError):
        source.source_ref = "other"  # type: ignore[misc]


def test_device_knowledge_is_immutable() -> None:
    knowledge = DeviceKnowledge.unknown(STABLE_ID)
    with pytest.raises(dataclasses.FrozenInstanceError):
        knowledge.stable_device_id = "other"  # type: ignore[misc]


def test_resolved_knowledge_requires_provenance() -> None:
    with pytest.raises(ValueError):
        DeviceKnowledge(
            stable_device_id=STABLE_ID,
            manufacturer_label="SMSL",
            product_label="SMSL USB AUDIO",
            capability_hints=("DSD256",),
            sources=(),
            resolution=EvidenceResolution.RESOLVED,
        )


def test_unknown_factory_is_fail_closed() -> None:
    knowledge = DeviceKnowledge.unknown(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.UNKNOWN
    assert knowledge.manufacturer_label is None
    assert knowledge.product_label is None
    assert knowledge.capability_hints == ()
    assert knowledge.sources == ()
    assert knowledge.provenance_labels == ()


def test_provenance_labels_are_deterministic_and_ordered() -> None:
    knowledge = DeviceKnowledge(
        stable_device_id=STABLE_ID,
        manufacturer_label="SMSL",
        product_label="SMSL USB AUDIO",
        capability_hints=("DSD256",),
        sources=(
            _source(ref="mahkb:entries/7", version="2026.10"),
            _source(
                origin=EvidenceOrigin.MANUFACTURER_DECLARED,
                confidence=EvidenceConfidence.WEAK,
                ref="vendor:spec-2025",
                version=None,
            ),
        ),
        resolution=EvidenceResolution.RESOLVED,
    )
    assert knowledge.provenance_labels == (
        "michi_kb:mahkb:entries/7@2026.10",
        "manufacturer_declared:vendor:spec-2025",
    )


def test_domain_module_imports_stay_pure() -> None:
    imports = _imported_modules(DOMAIN_MODULE)
    assert imports
    forbidden = (
        "PySide6",
        "gi",
        "Gst",
        "sqlite3",
        "ctypes",
        "michi.presentation",
        "michi.infrastructure",
        "michi.bootstrap",
        "michi.application",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in forbidden
        ), name
        top = name.split(".")[0]
        assert top in sys.stdlib_module_names or top == "michi", name
        if top == "michi":
            assert name == "michi.domain" or name.startswith("michi.domain."), name


# --------------------------------------------------------------------------- #
# knowledge service
# --------------------------------------------------------------------------- #


def test_empty_service_returns_unknown_knowledge() -> None:
    service = AudioDeviceKnowledgeService.empty()
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.UNKNOWN
    assert knowledge.manufacturer_label is None
    assert knowledge.sources == ()
    assert service.entry_count == 0


def test_document_row_resolves_by_vid_pid() -> None:
    service = AudioDeviceKnowledgeService({"entries": [_document_entry()]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.RESOLVED
    assert knowledge.manufacturer_label == "SMSL"
    assert knowledge.product_label == "SMSL USB AUDIO"
    assert knowledge.capability_hints == ("DSD256", "768kHz")
    assert knowledge.provenance_labels == ("michi_kb:mahkb:entries/0",)


def test_document_row_resolves_by_stable_device_id() -> None:
    entry = _document_entry(vid=None, pid=None, stable_device_id=STABLE_ID)
    service = AudioDeviceKnowledgeService({"entries": [entry]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.RESOLVED
    assert knowledge.manufacturer_label == "SMSL"


def test_partial_match_keys_never_invent_a_match() -> None:
    entry = _document_entry(vid="152a", pid=None)
    service = AudioDeviceKnowledgeService({"entries": [entry]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.UNKNOWN


def test_unmatched_device_stays_unknown() -> None:
    service = AudioDeviceKnowledgeService({"entries": [_document_entry()]})
    knowledge = service.knowledge_for("usb:1234:5678:1-1")
    assert knowledge.resolution is EvidenceResolution.UNKNOWN
    assert knowledge.sources == ()


def test_conflicting_rows_are_conflicted_without_invented_certainty() -> None:
    first = _document_entry(manufacturer="SMSL", product="SMSL USB AUDIO")
    second = _document_entry(
        manufacturer="Topping",
        product="D90SE",
        provenance=[
            {
                "origin": "usb_ids",
                "confidence": "corroborated",
                "source_ref": "usb.ids:0x152a",
            }
        ],
    )
    service = AudioDeviceKnowledgeService({"entries": [first, second]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.CONFLICTED
    assert knowledge.manufacturer_label is None
    assert knowledge.product_label is None
    assert knowledge.capability_hints == ()
    assert knowledge.provenance_labels == (
        "michi_kb:mahkb:entries/0",
        "usb_ids:usb.ids:0x152a",
    )


def test_agreeing_rows_merge_hints_in_order_without_duplicates() -> None:
    first = _document_entry(capabilities={"DSD256": True, "768kHz": True})
    second = _document_entry(capabilities={"768kHz": True, "384kHz": True})
    service = AudioDeviceKnowledgeService({"entries": [first, second]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.RESOLVED
    assert knowledge.capability_hints == ("DSD256", "768kHz", "384kHz")


def test_corrupt_document_text_never_raises() -> None:
    service = AudioDeviceKnowledgeService("{not json at all")
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.resolution is EvidenceResolution.UNKNOWN
    assert service.entry_count == 0


def test_malformed_entries_are_skipped_and_good_entries_survive() -> None:
    document = {
        "entries": [
            "not-a-mapping",
            {"match": "not-a-mapping"},
            {"match": {"vid": "152a", "pid": "85dd"}},  # no provenance
            {
                "match": {"vid": "152a", "pid": "85dd"},
                "provenance": [{"origin": "not-an-origin", "source_ref": "x"}],
            },
            _document_entry(),
        ]
    }
    service = AudioDeviceKnowledgeService(document)
    assert service.entry_count == 1
    assert service.knowledge_for(STABLE_ID).resolution is EvidenceResolution.RESOLVED


def test_entry_without_provenance_is_never_displayed() -> None:
    entry = _document_entry(provenance=[])
    service = AudioDeviceKnowledgeService({"entries": [entry]})
    assert service.entry_count == 0
    assert service.knowledge_for(STABLE_ID).resolution is EvidenceResolution.UNKNOWN


def test_document_version_reaches_provenance_labels() -> None:
    entry = _document_entry(
        provenance=[
            {"origin": "michi_kb", "confidence": "strong", "source_ref": "row/1"}
        ]
    )
    service = AudioDeviceKnowledgeService({"version": "2026.10", "entries": [entry]})
    knowledge = service.knowledge_for(STABLE_ID)
    assert knowledge.provenance_labels == ("michi_kb:row/1@2026.10",)


def test_knowledge_is_a_pure_function_of_the_document() -> None:
    document = {"entries": [_document_entry()]}
    first = AudioDeviceKnowledgeService(document).knowledge_for(STABLE_ID)
    second = AudioDeviceKnowledgeService(document).knowledge_for(STABLE_ID)
    assert first == second


def test_service_never_imports_admission_or_qualification_authorities() -> None:
    imports = _imported_modules(SERVICE_MODULE)
    forbidden = (
        "michi.application.audio_device_registry",
        "michi.application.dac_qualification_service",
        "michi.infrastructure",
        "michi.presentation",
        "michi.bootstrap",
        "PySide6",
        "sqlite3",
        "subprocess",
        "socket",
        "urllib",
        "http",
    )
    for name in imports:
        assert not any(
            name == prefix or name.startswith(prefix + ".") for prefix in forbidden
        ), name


# --------------------------------------------------------------------------- #
# presentation projection (MODIFY: audio_output_bridge.py)
# --------------------------------------------------------------------------- #


def test_bridge_row_exposes_knowledge_with_provenance() -> None:
    service = AudioDeviceKnowledgeService({"entries": [_document_entry()]})
    bridge = AudioOutputBridge(_Volume(), _Playback(), device_knowledge=service)
    row = _row(bridge, _snapshot())
    assert row["knowledgeResolution"] == "resolved"
    assert row["knowledgeManufacturer"] == "SMSL"
    assert row["knowledgeProduct"] == "SMSL USB AUDIO"
    assert row["knowledgeCapabilityHints"] == ["DSD256", "768kHz"]
    assert row["knowledgeProvenance"] == ["michi_kb:mahkb:entries/0"]


def test_unknown_device_remains_selectable_with_unknown_knowledge() -> None:
    bridge = AudioOutputBridge(
        _Volume(), _Playback(), device_knowledge=AudioDeviceKnowledgeService.empty()
    )
    row = _row(bridge, _snapshot())
    assert row["canSelect"] is True
    assert row["knowledgeResolution"] == "unknown"
    assert row["knowledgeManufacturer"] == ""
    assert row["knowledgeCapabilityHints"] == []
    assert row["knowledgeProvenance"] == []


def test_bridge_without_service_keeps_previous_projection_identical() -> None:
    plain = AudioOutputBridge(_Volume(), _Playback())
    enriched = AudioOutputBridge(
        _Volume(),
        _Playback(),
        device_knowledge=AudioDeviceKnowledgeService({"entries": [_document_entry()]}),
    )
    snapshot = _snapshot()
    row_plain = _row(plain, snapshot)
    row_enriched = _row(enriched, snapshot)
    knowledge_keys = {key for key in row_enriched if key.startswith("knowledge")}
    assert knowledge_keys
    stripped_plain = {
        key: value for key, value in row_plain.items() if key not in knowledge_keys
    }
    stripped_enriched = {
        key: value for key, value in row_enriched.items() if key not in knowledge_keys
    }
    assert stripped_plain == stripped_enriched
    assert row_plain["canSelect"] is True
    assert row_plain["knowledgeResolution"] == "unknown"
    assert row_enriched["knowledgeResolution"] == "resolved"


def test_bridge_knowledge_failure_is_fail_soft() -> None:
    class _BrokenService:
        def knowledge_for(self, _stable_device_id: str) -> DeviceKnowledge:
            raise RuntimeError("corrupt kb")

    bridge = AudioOutputBridge(
        _Volume(), _Playback(), device_knowledge=_BrokenService()
    )
    row = _row(bridge, _snapshot())
    assert row["knowledgeResolution"] == "unknown"
    assert row["canSelect"] is True
