"""AP2-F09 — canonical DoP resolution through the productive resolver."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from michi.application.dsd_output_planner import NativeDsdPlanner
from michi.application.dsd_source_characterizer import DsdSourceStatus
from michi.application.output_session_service import ProductiveOutputRequestResolver
from michi.domain.audio_output import OutputPathPreference, VolumePolicy
from michi.domain.dop import DopInterpretationState, DopPolicyDecision
from tests.audio_phase2.test_productive_output_resolver import (
    _Characterizer,
    _Devices,
    _dsd_qualification,
    _DsdCharacterizer,
    _Engines,
    _Metadata,
    _profile,
    _Profiles,
    _Qualification,
)
from tests.dop.test_dop_planner import _carrier, _interp


def _dop_carrier(_device, _binding, _source):
    return (
        replace(
            _carrier(),
            stable_device_id="dev:dac",
            binding_generation=7,
            binding_locator="hw:2,0",
            environment_fingerprint="env:1",
        ),
    )


def _dop_interp(_device, _source):
    return (
        replace(
            _interp(DopInterpretationState.USER_CONFIRMED),
            stable_device_id="dev:dac",
            device_revision="rev:1",
        ),
    )


def _resolver(policy, *, qualification=_dop_carrier):
    return ProductiveOutputRequestResolver(
        profiles=_Profiles(
            __import__("dataclasses").replace(
                _profile(OutputPathPreference.HARDWARE_DIRECT),
                volume_policy=VolumePolicy.HARDWARE,
            )
        ),
        devices=_Devices(),
        qualification=_Qualification(),
        engines=_Engines(),
        source_metadata=_Metadata(),
        source_characterizer=_Characterizer(),
        dsd_source_characterizer=_DsdCharacterizer(DsdSourceStatus.DSD_PROVEN),
        dsd_planner=NativeDsdPlanner(),
        dsd_qualification=_dsd_qualification,
        dop_policy_provider=lambda _source: policy,
        dop_qualification=qualification,
        dop_interpretation=_dop_interp,
        dop_host_generation=lambda: 1,
        dop_environment_fingerprint=lambda: "env:1",
        dop_device_revision=lambda _device: "rev:1",
    )


def test_explicit_dop_resolves_canonical_plan() -> None:
    policy = DopPolicyDecision(
        explicit_requested=True,
        auto_allowed=False,
        minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
    )
    request = _resolver(policy)(Path("/media/track.dsf"))
    assert request.dop_plan is not None
    plan = request.dop_plan
    assert plan.stable_device_id == "dev:dac"
    assert plan.binding_locator == "hw:2,0"
    assert plan.binding_generation == 7
    assert plan.carrier_rate.frames_per_second == 176_400
    assert plan.source.bit_rate_hz == 2_822_400
    assert plan.processing_policy == "DOP_ONLY"


def test_auto_without_device_observation_is_refused() -> None:
    policy = DopPolicyDecision(
        explicit_requested=False,
        auto_allowed=True,
        minimum_interpretation_state=DopInterpretationState.DEVICE_OBSERVED,
    )
    with pytest.raises(Exception) as info:
        _resolver(policy)(Path("/media/track.dsf"))
    assert "DOP_DEVICE_INTERPRETATION_UNKNOWN" in str(info.value)


def test_missing_qualification_authority_is_typed() -> None:
    policy = DopPolicyDecision(explicit_requested=True, auto_allowed=False)
    with pytest.raises(Exception) as info:
        _resolver(policy, qualification=None)(Path("/media/track.dsf"))
    assert "DOP_AUTHORITIES_UNAVAILABLE" in str(info.value)


def test_without_policy_native_dsd_is_preserved() -> None:
    resolver = ProductiveOutputRequestResolver(
        profiles=_Profiles(
            __import__("dataclasses").replace(
                _profile(OutputPathPreference.HARDWARE_DIRECT),
                volume_policy=VolumePolicy.HARDWARE,
            )
        ),
        devices=_Devices(),
        qualification=_Qualification(),
        engines=_Engines(),
        source_metadata=_Metadata(),
        source_characterizer=_Characterizer(),
        dsd_source_characterizer=_DsdCharacterizer(DsdSourceStatus.DSD_PROVEN),
        dsd_planner=NativeDsdPlanner(),
        dsd_qualification=_dsd_qualification,
    )
    request = resolver(Path("/media/track.dsf"))
    assert request.native_dsd_plan is not None
    assert request.dop_plan is None
