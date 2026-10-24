"""AP2-F09 — DoP planner V3 double-gate tests."""

from __future__ import annotations

import pytest

from michi.application.dop_planner import (
    DopExecutionPlanV2,
    DopPlannerError,
    DopPlannerV3,
)
from michi.domain.dop import (
    DopCarrierLayout,
    DopCarrierQualification,
    DopCarrierSupport,
    DopDeviceInterpretationEvidence,
    DopInterpretationState,
    DopPolicyDecision,
)
from michi.domain.dsd_signal import (
    DsdBitOrder,
    DsdOrganization,
    DsdPacking,
    DsdSignalFormat,
)

DEVICE = "usb:152a:85dd"
LOCATOR = "hw:3,0"
EVIDENCE = ("alsa-dop:carrier",)
INTERP_EVIDENCE = ("dop:user-confirmed",)


def _source(rate: int = 2_822_400, channels: int = 2) -> DsdSignalFormat:
    layout = ("FL", "FR") if channels == 2 else tuple(f"C{i}" for i in range(channels))
    return DsdSignalFormat(
        bit_rate_hz=rate,
        channels=channels,
        packing=DsdPacking.DSD_U8,
        bit_order=DsdBitOrder.MSBF,
        organization=DsdOrganization.PLANAR,
        layout=layout,
    )


def _carrier(
    *,
    rate: int = 176_400,
    layout: DopCarrierLayout = DopCarrierLayout.PACKED_24_LE,
    support: DopCarrierSupport = DopCarrierSupport.QUALIFIED,
    binding: int | None = 3,
) -> DopCarrierQualification:
    return DopCarrierQualification(
        stable_device_id=DEVICE,
        carrier_layout_id=layout.value,
        carrier_rate_hz=rate,
        alsa_format="S24_3LE" if layout is DopCarrierLayout.PACKED_24_LE else "S32_LE",
        channels=2,
        support=support,
        environment_fingerprint="env:1",
        evidence_refs=EVIDENCE,
        binding_generation=binding,
        binding_locator=LOCATOR,
        significant_transport_bits=24,
        provenance="alsa-dop-probe",
    )


def _interp(
    state: DopInterpretationState,
    *,
    evidence: tuple[str, ...] = INTERP_EVIDENCE,
    multiplier: int = 64,
) -> DopDeviceInterpretationEvidence:
    return DopDeviceInterpretationEvidence(
        stable_device_id=DEVICE,
        source_dsd_multiplier=multiplier,
        state=state,
        source="test",
        device_revision="rev:1",
        evidence_refs=evidence,
    )


def _plan(**overrides):
    values = {
        "stable_device_id": DEVICE,
        "binding_locator": LOCATOR,
        "binding_generation": 3,
        "environment_fingerprint": "env:1",
        "source": _source(),
        "carrier_qualifications": (_carrier(),),
        "interpretation": (_interp(DopInterpretationState.USER_CONFIRMED),),
        "policy": DopPolicyDecision(
            explicit_requested=True,
            auto_allowed=False,
            minimum_interpretation_state=DopInterpretationState.USER_CONFIRMED,
        ),
    }
    values.update(overrides)
    return DopPlannerV3().plan(**values)


def test_explicit_user_confirmed_plan_is_exact() -> None:
    plan = _plan()
    assert isinstance(plan, DopExecutionPlanV2)
    assert plan.carrier_rate.frames_per_second == 176_400
    assert plan.memory_contract.layout is DopCarrierLayout.PACKED_24_LE
    assert plan.interpretation_state is DopInterpretationState.USER_CONFIRMED
    assert plan.packer_revision.startswith("dop-python-reference")
    assert plan.plan_id.startswith("dop:")


def test_auto_requires_device_observed() -> None:
    plan = _plan(
        interpretation=(_interp(DopInterpretationState.DEVICE_OBSERVED),),
        policy=DopPolicyDecision(
            explicit_requested=False,
            auto_allowed=True,
            minimum_interpretation_state=DopInterpretationState.DEVICE_OBSERVED,
        ),
    )
    assert plan.interpretation_state is DopInterpretationState.DEVICE_OBSERVED


def test_auto_rejects_user_confirmed_only() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(
            policy=DopPolicyDecision(
                explicit_requested=False,
                auto_allowed=True,
                minimum_interpretation_state=DopInterpretationState.DEVICE_OBSERVED,
            )
        )
    assert info.value.code == "DOP_DEVICE_INTERPRETATION_UNKNOWN"


def test_explicit_rejects_unknown() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(interpretation=(_interp(DopInterpretationState.UNKNOWN),))
    assert info.value.code == "DOP_DEVICE_INTERPRETATION_UNKNOWN"


def test_contradicted_interpretation_is_negative() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(interpretation=(_interp(DopInterpretationState.CONTRADICTED),))
    assert info.value.code == "DOP_DEVICE_INTERPRETATION_CONTRADICTED"


def test_carrier_support_states() -> None:
    for support, code in (
        (DopCarrierSupport.UNKNOWN, "DOP_CARRIER_UNKNOWN"),
        (DopCarrierSupport.INCONCLUSIVE, "DOP_CARRIER_UNKNOWN"),
        (DopCarrierSupport.UNSUPPORTED, "DOP_CARRIER_UNSUPPORTED"),
    ):
        with pytest.raises(DopPlannerError) as info:
            _plan(carrier_qualifications=(_carrier(support=support),))
        assert info.value.code == code


def test_rate_mismatch_is_unqualified() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_carrier(rate=352_800),))
    assert info.value.code == "DOP_CARRIER_LAYOUT_UNQUALIFIED"


def test_layout_preference_selects_s32_lsb24() -> None:
    plan = _plan(
        carrier_qualifications=(
            _carrier(layout=DopCarrierLayout.PACKED_24_LE),
            _carrier(layout=DopCarrierLayout.S32_LE_LSB24),
        ),
        layout_preference=(DopCarrierLayout.S32_LE_LSB24,),
    )
    assert plan.memory_contract.layout is DopCarrierLayout.S32_LE_LSB24
    assert plan.memory_contract.alsa_format == "S32_LE"


def test_msb24_is_not_in_default_production_preference() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_carrier(layout=DopCarrierLayout.S32_LE_MSB24),))
    assert info.value.code == "DOP_CARRIER_LAYOUT_UNKNOWN"


def test_binding_generation_mismatch() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(binding_generation=4)
    assert info.value.code == "DOP_BINDING_STALE"


def test_dsp_volume_engine_and_binding_refusals() -> None:
    cases = (
        ({"processing_active": True}, "DOP_DSP_UNSUPPORTED"),
        ({"volume_authority": "software"}, "DOP_VOLUME_AUTHORITY_UNSUPPORTED"),
        ({"active_engine_id": "mpd"}, "DOP_ENGINE_UNSUPPORTED"),
        ({"binding_current": False}, "DOP_BINDING_STALE"),
    )
    for overrides, code in cases:
        with pytest.raises(DopPlannerError) as info:
            _plan(**overrides)
        assert info.value.code == code


def test_policy_must_enable_dop() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(
            policy=DopPolicyDecision(
                explicit_requested=False,
                auto_allowed=False,
                minimum_interpretation_state=DopInterpretationState.DECLARED,
            )
        )
    assert info.value.code == "DOP_NOT_ENABLED"


def test_multichannel_is_refused() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(source=_source(channels=3), carrier_qualifications=())
    assert info.value.code == "DOP_MULTICHANNEL_UNSUPPORTED"


def test_plan_identity_is_deterministic_and_binding_bound() -> None:
    first = _plan()
    same = _plan()
    other = _plan(
        binding_generation=3,
        carrier_qualifications=(_special_carrier(binding_locator="hw:3,1"),),
        binding_locator="hw:3,1",
    )
    assert first.plan_id == same.plan_id
    assert first.plan_id != other.plan_id


@pytest.mark.parametrize("rate,carrier", [(5_644_800, 352_800), (11_289_600, 705_600)])
def test_higher_rate_mapping(rate, carrier) -> None:
    plan = _plan(
        source=_source(rate=rate),
        carrier_qualifications=(_carrier(rate=carrier),),
        interpretation=(
            _interp(DopInterpretationState.USER_CONFIRMED, multiplier=rate // 44_100),
        ),
    )
    assert plan.carrier_rate.frames_per_second == carrier


def _special_carrier(**overrides):
    values = dict(
        stable_device_id=DEVICE,
        carrier_layout_id=DopCarrierLayout.PACKED_24_LE.value,
        carrier_rate_hz=176_400,
        alsa_format="S24_3LE",
        channels=2,
        support=DopCarrierSupport.QUALIFIED,
        environment_fingerprint="env:1",
        evidence_refs=EVIDENCE,
        binding_generation=3,
        binding_locator=LOCATOR,
        significant_transport_bits=24,
        provenance="alsa-dop-probe",
    )
    values.update(overrides)
    return DopCarrierQualification(**values)


def test_carrier_without_binding_is_incomplete() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_special_carrier(binding_generation=None),))
    assert info.value.code == "DOP_CARRIER_QUALIFICATION_INCOMPLETE"


def test_other_endpoint_of_same_dac_is_rejected() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_special_carrier(binding_locator="hw:3,1"),))
    assert info.value.code == "DOP_ENDPOINT_MISMATCH"


def test_old_binding_is_stale() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_special_carrier(binding_generation=2),))
    assert info.value.code == "DOP_BINDING_STALE"


def test_environment_mismatch_is_stale() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(
            carrier_qualifications=(
                _special_carrier(environment_fingerprint="env:old"),
            )
        )
    assert info.value.code == "DOP_ENVIRONMENT_STALE"


def test_format_mismatch_is_rejected() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(carrier_qualifications=(_special_carrier(alsa_format="S32_LE"),))
    assert info.value.code == "DOP_CARRIER_FORMAT_MISMATCH"


def test_interpretation_multiplier_scope_is_enforced() -> None:
    with pytest.raises(DopPlannerError) as info:
        _plan(
            source=_source(rate=5_644_800),
            carrier_qualifications=(_carrier(rate=352_800),),
            interpretation=(
                _interp(DopInterpretationState.USER_CONFIRMED, multiplier=64),
            ),
        )
    assert info.value.code == "DOP_DEVICE_INTERPRETATION_UNKNOWN"


def test_explicit_supported_multipliers_allow_multirate() -> None:
    evidence = DopDeviceInterpretationEvidence(
        stable_device_id=DEVICE,
        source_dsd_multiplier=None,
        state=DopInterpretationState.USER_CONFIRMED,
        source="declared-multirate",
        device_revision="rev:1",
        evidence_refs=INTERP_EVIDENCE,
        supported_multipliers=(64, 128),
    )
    plan = _plan(
        source=_source(rate=5_644_800),
        carrier_qualifications=(_carrier(rate=352_800),),
        interpretation=(evidence,),
    )
    assert plan.carrier_rate.frames_per_second == 352_800
