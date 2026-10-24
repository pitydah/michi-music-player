"""AP2-F09 — probe evidence -> executable DoP carrier qualification.

Only an exact QUALIFIED ALSA observation becomes an executable planner
qualification. UNKNOWN/INCONCLUSIVE/UNSUPPORTED remain non-authorizing, and
DAC interpretation is never inferred from this carrier evidence.
"""

from __future__ import annotations

from michi.domain.dop import (
    DopCarrierLayout,
    DopCarrierQualification,
    DopCarrierSupport,
    memory_contract_for,
)
from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
)


class DopQualificationError(ValueError):
    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


def qualification_from_probe(
    evidence: DopCarrierProbeEvidence,
    *,
    environment_fingerprint: str,
    provenance: str,
) -> DopCarrierQualification:
    if not isinstance(evidence, DopCarrierProbeEvidence):
        raise DopQualificationError(
            "DOP_CARRIER_EVIDENCE_INVALID", "expected probe evidence"
        )
    if not environment_fingerprint.strip():
        raise DopQualificationError(
            "DOP_ENVIRONMENT_STALE", "current environment fingerprint required"
        )
    if provenance not in ("ALSA_LAB_DIRECT", "ALSA_SUPERVISED"):
        raise DopQualificationError(
            "DOP_CARRIER_PROVENANCE_INVALID",
            "provenance must be ALSA_LAB_DIRECT or ALSA_SUPERVISED",
        )
    if evidence.environment_fingerprint != environment_fingerprint:
        raise DopQualificationError(
            "DOP_ENVIRONMENT_STALE", "carrier evidence is from another environment"
        )
    if evidence.support is not DopCarrierSupport.QUALIFIED:
        raise DopQualificationError("DOP_CARRIER_NOT_QUALIFIED", evidence.support.value)
    request = evidence.request
    try:
        contract = memory_contract_for(request.layout)
    except Exception as exc:
        raise DopQualificationError("DOP_CARRIER_LAYOUT_INVALID", str(exc)) from exc
    if request.alsa_format != contract.alsa_format:
        raise DopQualificationError("DOP_CARRIER_FORMAT_MISMATCH", request.alsa_format)
    if (
        evidence.negotiated_rate_hz != request.rate_hz
        or evidence.negotiated_format != request.alsa_format
        or evidence.negotiated_channels != request.channels
    ):
        raise DopQualificationError(
            "DOP_CARRIER_READBACK_MISMATCH", evidence.disposition
        )
    if not evidence.binding_locator.strip() or evidence.binding_generation < 0:
        raise DopQualificationError(
            "DOP_CARRIER_QUALIFICATION_INCOMPLETE", "binding required"
        )
    layout = request.layout
    if not isinstance(layout, DopCarrierLayout):
        raise DopQualificationError("DOP_CARRIER_LAYOUT_INVALID", "layout")
    return DopCarrierQualification(
        stable_device_id=evidence.stable_device_id,
        carrier_layout_id=layout.value,
        carrier_rate_hz=evidence.negotiated_rate_hz,
        alsa_format=evidence.negotiated_format,
        channels=evidence.negotiated_channels,
        support=DopCarrierSupport.QUALIFIED,
        environment_fingerprint=evidence.environment_fingerprint,
        evidence_refs=(evidence.evidence_ref,),
        binding_generation=evidence.binding_generation,
        binding_locator=evidence.binding_locator,
        significant_transport_bits=24,
        provenance=provenance,
    )
