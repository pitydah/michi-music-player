"""AP2-F06 WU-A — the productive resolver must classify MANAGED as a
specific-DAC family, never as Shared. Regression for the P0 misclassification.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from michi.application.output_session_service import (
    OutputSessionError,
    ProductiveOutputRequestResolver,
)
from michi.domain.audio_device import AudioDeviceBinding, BindingKind
from michi.domain.audio_engine import AudioEngineId
from michi.domain.audio_evidence import (
    CapabilityEvidence,
    DecodedSourceSignal,
    EvidenceStrength,
    PcmTuple,
)
from michi.domain.audio_output import (
    AudioOutputProfile,
    AudioOutputSelection,
    FallbackKind,
    OutputPathPreference,
    RatePolicy,
    VolumePolicy,
)

PATH = Path("/media/song.flac")


def _profile(path: OutputPathPreference, profile_id: str = "profile:1"):
    return AudioOutputProfile(
        profile_id=profile_id,
        stable_device_id="dev:dac",
        path=path,
        rate_policy=RatePolicy.SOURCE_NATIVE,
        volume_policy=VolumePolicy.SOFTWARE,
        allow_resample=False,
        allow_remix=False,
        allow_processing=path is OutputPathPreference.MANAGED,
        fallback=FallbackKind.STOP,
    )


class _Profiles:
    def __init__(self, profile: AudioOutputProfile | None):
        self.profile = profile

    def load_selection(self):
        return AudioOutputSelection(
            self.profile.profile_id if self.profile else None,
            "dev:dac" if self.profile else None,
            1,
        )

    def load_profiles(self):
        return (self.profile,) if self.profile else ()

    def snapshot_output_intent(self):
        return ("intent", 1)


class _Devices:
    def __init__(self, bindings=None):
        self._bindings = (
            bindings
            if bindings is not None
            else [
                AudioDeviceBinding(
                    kind=BindingKind.ALSA_PCM,
                    locator="hw:2,0",
                    generation=7,
                    currently_available=True,
                )
            ]
        )

    def bindings_for(self, _device, _kind):
        return list(self._bindings)

    def generation_for(self, _device):
        return 7

    def available_ids(self):
        return {"dev:dac"}


class _Qualification:
    def cached_evidence_current(self, device):
        return (
            CapabilityEvidence(
                stable_device_id=device,
                tuple=PcmTuple(44100, "S16LE", 2, 16),
                supported=True,
                strength=EvidenceStrength.OPENED,
                source="test",
                observed_at_ns=1,
                environment_fingerprint="fp",
                evidence_refs=("ref",),
            ),
        )


class _Engines:
    def __init__(self, engine=AudioEngineId.GSTREAMER):
        self.state = type("State", (), {"active_engine_id": engine})()


class _Metadata:
    def extract(self, _path):
        return type(
            "Metadata",
            (),
            {
                "container": "flac",
                "codec": "flac",
                "sample_rate_hz": 44100,
                "channels": 2,
                "bit_depth": 16,
            },
        )()


class _Characterizer:
    def characterize(self, _path):
        return DecodedSourceSignal(
            encoding="PCM",
            rate_hz=44100,
            significant_bits=16,
            channels=2,
            channel_positions=("FL", "FR"),
        )


def _resolver(profile, *, engine=AudioEngineId.GSTREAMER, bindings=None):
    return ProductiveOutputRequestResolver(
        profiles=_Profiles(profile),
        devices=_Devices(bindings),
        qualification=_Qualification(),
        engines=_Engines(engine),
        source_metadata=_Metadata(),
        source_characterizer=_Characterizer(),
    )


def test_managed_profile_is_never_reclassified_as_shared() -> None:
    resolver = _resolver(_profile(OutputPathPreference.MANAGED))
    request = resolver(PATH)
    assert request.facts is not None, "MANAGED was misclassified as Shared"
    facts = request.facts
    assert facts.profile.path is OutputPathPreference.MANAGED
    assert facts.selected_device_id == "dev:dac"
    assert facts.binding is not None and facts.binding.locator == "hw:2,0"
    assert facts.expected_binding_generation == 7
    assert facts.device_available is True
    assert facts.decoded_source.rate_hz == 44100
    assert facts.evidence and facts.evidence[0].supported is True
    assert request.selected_profile_id == "profile:1"


def test_shared_profile_stays_an_explicit_shared_request() -> None:
    resolver = _resolver(_profile(OutputPathPreference.DESKTOP))
    request = resolver(PATH)
    assert request.facts is None
    assert request.selected_device_id == "dev:dac"


def test_direct_profile_regression() -> None:
    for path in (
        OutputPathPreference.HARDWARE_DIRECT,
        OutputPathPreference.HARDWARE_DIRECT_COMPATIBLE,
    ):
        request = _resolver(_profile(path))(PATH)
        assert request.facts is not None
        assert request.facts.profile.path is path


def test_managed_requires_the_gstreamer_engine() -> None:
    resolver = _resolver(
        _profile(OutputPathPreference.MANAGED), engine=AudioEngineId.MPD
    )
    with pytest.raises(OutputSessionError) as info:
        resolver(PATH)
    assert info.value.code == "ENGINE_UNSUPPORTED_FOR_MANAGED"


def test_managed_pending_device_identity_is_visible() -> None:
    resolver = _resolver(_profile(OutputPathPreference.MANAGED))
    assert resolver.pending_device_id(PATH) == "dev:dac"
    shared = _resolver(_profile(OutputPathPreference.DESKTOP))
    assert shared.pending_device_id(PATH) is None


def test_ambiguous_alsa_endpoints_are_still_rejected_for_managed() -> None:
    bindings = [
        AudioDeviceBinding(BindingKind.ALSA_PCM, "hw:2,0", 7, True),
        AudioDeviceBinding(BindingKind.ALSA_PCM, "hw:2,1", 7, True),
    ]
    resolver = _resolver(_profile(OutputPathPreference.MANAGED), bindings=bindings)
    with pytest.raises(OutputSessionError) as info:
        resolver(PATH)
    assert info.value.code == "MULTIPLE_ALSA_PLAYBACK_ENDPOINTS"
