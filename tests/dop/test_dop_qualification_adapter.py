"""AP2-F09 — probe evidence -> planner qualification adapter."""

from __future__ import annotations

import pytest

from michi.domain.dop import (
    DopCarrierLayout,
    DopCarrierSupport,
    memory_contract_for,
)
from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
    DopCarrierProbeRequest,
)
from michi.infrastructure.audio_devices.dop_qualification import (
    DopQualificationError,
    qualification_from_probe,
)


def _evidence(
    *,
    support=DopCarrierSupport.QUALIFIED,
    layout=DopCarrierLayout.S32_LE_LSB24,
    env="env:1",
    rate=176_400,
    fmt=None,
    gen=3,
    locator="hw:3,0",
):
    contract = memory_contract_for(layout)
    request = DopCarrierProbeRequest(layout, fmt or contract.alsa_format, rate, 2)
    return DopCarrierProbeEvidence(
        stable_device_id="usb:152a:85dd",
        binding_locator=locator,
        binding_generation=gen,
        request=request,
        negotiated_rate_hz=rate,
        negotiated_format=fmt or contract.alsa_format,
        negotiated_channels=2,
        support=support,
        disposition="test",
        errno_code=None,
        environment_fingerprint=env,
        evidence_ref="alsa-dop:test",
    )


def test_qualified_evidence_becomes_exact_qualification() -> None:
    q = qualification_from_probe(_evidence(), environment_fingerprint="env:1")
    assert q.support is DopCarrierSupport.QUALIFIED
    assert q.binding_locator == "hw:3,0"
    assert q.binding_generation == 3
    assert q.carrier_layout_id == DopCarrierLayout.S32_LE_LSB24.value
    assert q.alsa_format == "S32_LE"
    assert q.provenance


@pytest.mark.parametrize(
    "support,code",
    [
        (DopCarrierSupport.UNKNOWN, "DOP_CARRIER_NOT_QUALIFIED"),
        (DopCarrierSupport.INCONCLUSIVE, "DOP_CARRIER_NOT_QUALIFIED"),
        (DopCarrierSupport.UNSUPPORTED, "DOP_CARRIER_NOT_QUALIFIED"),
    ],
)
def test_non_qualified_evidence_is_rejected(support, code) -> None:
    with pytest.raises(DopQualificationError) as info:
        qualification_from_probe(
            _evidence(support=support), environment_fingerprint="env:1"
        )
    assert info.value.code == code


def test_stale_environment_is_rejected() -> None:
    with pytest.raises(DopQualificationError) as info:
        qualification_from_probe(
            _evidence(env="env:old"), environment_fingerprint="env:1"
        )
    assert info.value.code == "DOP_ENVIRONMENT_STALE"


def test_readback_mismatch_is_rejected() -> None:
    evidence = _evidence()
    mismatched = DopCarrierProbeEvidence(
        stable_device_id=evidence.stable_device_id,
        binding_locator=evidence.binding_locator,
        binding_generation=evidence.binding_generation,
        request=evidence.request,
        negotiated_rate_hz=352_800,
        negotiated_format=evidence.negotiated_format,
        negotiated_channels=2,
        support=DopCarrierSupport.QUALIFIED,
        disposition="mismatch",
        errno_code=None,
        environment_fingerprint="env:1",
        evidence_ref="ref",
    )
    with pytest.raises(DopQualificationError) as info:
        qualification_from_probe(mismatched, environment_fingerprint="env:1")
    assert info.value.code == "DOP_CARRIER_READBACK_MISMATCH"
