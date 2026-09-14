"""DAC-V35-050R1 qualification environment fingerprint gates (FP-01..11)."""

from __future__ import annotations

import dataclasses

import pytest

from michi.application.audio_output_planner import OutputPlanner, PlannerRefusal
from michi.application.dac_qualification_service import (
    DacQualificationService,
    QualificationEnvironmentContext,
    binding_topology_fingerprint,
    default_environment_fingerprint,
)
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_evidence import CapabilityEvidence, EvidenceStrength, PcmTuple
from tests.dac.test_v34_output_planner import _facts


def _context(**changes) -> QualificationEnvironmentContext:
    base = QualificationEnvironmentContext(
        stable_device_id="usb:2622:0105:serial",
        usb_vendor_id="2622",
        usb_product_id="0105",
        usb_bcd_device="0100",
        usb_descriptor_sha256="a" * 64,
        kernel_release="6.12.1",
        snd_usb_audio_identity="snd-usb-audio@6.12.1",
        alsa_library_version="1.2.14",
        gstreamer_version="1.26.3",
        binding_topology_fingerprint="topology:stable-endpoint-0",
        qualification_profile_version="dac-v35-profile-1",
    )
    return dataclasses.replace(base, **changes)


def _fingerprint(**changes) -> str:
    return default_environment_fingerprint(_context(**changes))


def test_fp_01_fingerprint_is_versioned_sha256_and_deterministic() -> None:
    first = _fingerprint()
    assert first.startswith("qenv:v2:sha256:")
    assert first == _fingerprint()
    assert len(first.removeprefix("qenv:v2:sha256:")) == 64


def test_fp_02_physical_device_identity_changes_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(stable_device_id="usb:other")


def test_fp_03_usb_vid_or_pid_changes_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(usb_product_id="0106")


def test_fp_04_bcd_device_changes_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(usb_bcd_device="0200")


def test_fp_05_usb_descriptor_hash_changes_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(usb_descriptor_sha256="b" * 64)


def test_fp_06_kernel_or_driver_change_invalidates_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(kernel_release="6.13.0")
    assert _fingerprint() != _fingerprint(snd_usb_audio_identity="snd-usb-audio@2")


def test_fp_07_alsa_library_change_invalidates_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(alsa_library_version="1.2.15")


def test_fp_08_gstreamer_change_invalidates_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(gstreamer_version="1.28.0")


def test_fp_09_binding_topology_change_invalidates_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(
        binding_topology_fingerprint="topology:stable-endpoint-1"
    )


def test_fp_10_qualification_profile_change_invalidates_fingerprint() -> None:
    assert _fingerprint() != _fingerprint(
        qualification_profile_version="dac-v35-profile-2"
    )


class _Cache:
    def __init__(self, evidence) -> None:
        self.evidence = evidence

    def load_qualification_cache(self, stable_device_id):
        return self.evidence

    def replace_qualification_cache(self, stable_device_id, evidence):
        self.evidence = evidence


def test_fp_11_legacy_and_stale_sbits_evidence_are_never_current() -> None:
    stale = CapabilityEvidence(
        stable_device_id="usb:2622:0105:serial",
        tuple=PcmTuple(96_000, "S32_LE", 2, 24),
        supported=True,
        strength=EvidenceStrength.OPENED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint="Linux-6.12-x86_64-py3.11",
        evidence_refs=("probe:legacy-sbits24",),
    )
    service = DacQualificationService(
        object(),
        cache=_Cache((stale,)),
        environment_context=lambda stable_id: _context(stable_device_id=stable_id),
    )

    assert service.cached_evidence("usb:2622:0105:serial") == (stale,)
    current = service.cached_evidence_current("usb:2622:0105:serial")
    assert current == ()
    decision = OutputPlanner().plan(_facts(evidence=current))
    assert isinstance(decision, PlannerRefusal)
    assert decision.code == "EXACT_TUPLE_UNKNOWN"


def test_card_renumber_is_innocuous_with_stable_endpoint_signature() -> None:
    def binding(card: int, locator: str) -> AudioDeviceBinding:
        return AudioDeviceBinding(
            kind=BindingKind.ALSA_PCM,
            locator=locator,
            generation=card,
            currently_available=True,
            card_index=card,
            pcm_device=0,
            stable_endpoint_signature="usb-interface:1.0:pcm:0:sub:0",
        )

    assert binding_topology_fingerprint((binding(1, "hw:1,0"),)) == (
        binding_topology_fingerprint((binding(7, "hw:7,0"),))
    )


def test_card_renumber_invalidates_without_stable_endpoint_signature() -> None:
    first = AudioDeviceBinding(
        BindingKind.ALSA_PCM, "hw:1,0", 1, True, card_index=1, pcm_device=0
    )
    second = AudioDeviceBinding(
        BindingKind.ALSA_PCM, "hw:7,0", 2, True, card_index=7, pcm_device=0
    )
    assert binding_topology_fingerprint((first,)) != binding_topology_fingerprint(
        (second,)
    )


def test_incomplete_required_context_never_promotes_matching_cache() -> None:
    incomplete = _context(usb_descriptor_sha256=None)
    evidence = CapabilityEvidence(
        stable_device_id=incomplete.stable_device_id,
        tuple=PcmTuple(96_000, "S32_LE", 2, 24),
        supported=True,
        strength=EvidenceStrength.OPENED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint=default_environment_fingerprint(incomplete),
        evidence_refs=("probe:incomplete",),
    )
    service = DacQualificationService(
        object(),
        cache=_Cache((evidence,)),
        environment_context=lambda _stable_id: incomplete,
    )
    assert service.cached_evidence_current(incomplete.stable_device_id) == ()


def test_default_incomplete_context_never_promotes_matching_cache() -> None:
    stable_device_id = "usb:2622:0105:serial"
    fingerprint = DacQualificationService(object()).current_environment_fingerprint(
        stable_device_id
    )
    evidence = CapabilityEvidence(
        stable_device_id=stable_device_id,
        tuple=PcmTuple(96_000, "S32_LE", 2, 24),
        supported=True,
        strength=EvidenceStrength.OPENED,
        source="michi-alsa-probe",
        observed_at_ns=1,
        environment_fingerprint=fingerprint,
        evidence_refs=("probe:default-incomplete",),
    )
    service = DacQualificationService(object(), cache=_Cache((evidence,)))

    assert service.cached_evidence_current(stable_device_id) == ()


def test_fingerprint_override_and_context_cannot_diverge() -> None:
    with pytest.raises(ValueError, match="mutually exclusive"):
        DacQualificationService(
            object(),
            environment_fingerprint=lambda: "override",
            environment_context=lambda _stable_id: _context(),
        )
