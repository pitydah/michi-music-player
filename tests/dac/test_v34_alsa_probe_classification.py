"""DAC-V35-020 — clasificación de errores y mapeo a evidencia (§12/§401).

Regla crítica: BUSY != UNSUPPORTED, REMOVED != UNSUPPORTED,
TIMEOUT != UNSUPPORTED. Solo un rechazo exacto produce evidencia
negativa.
"""

from __future__ import annotations

from michi.application.dac_qualification_service import DacQualificationService
from michi.domain.audio_evidence import (
    EvidenceStrength,
    ExactProbeResult,
    PcmTuple,
)
from michi.infrastructure.audio_devices.alsa_ctypes import AlsaProbeError
from michi.infrastructure.audio_devices.alsa_probe_cli import classify_error

TUPLE = PcmTuple(96000, "S32_LE", 2, None)


class _NeverCalledAdapter:
    def probe_exact(self, **kwargs):  # pragma: no cover - no debe llamarse
        raise AssertionError("el adapter no debe invocarse en este test")


def _result(disposition: str, negotiated: PcmTuple | None = None) -> ExactProbeResult:
    return ExactProbeResult(
        requested=TUPLE,
        negotiated=negotiated,
        disposition=disposition,
        alsa_error_code=None,
        detail=None,
        evidence_ref="probe:test",
    )


def _service() -> DacQualificationService:
    return DacQualificationService(
        _NeverCalledAdapter(),
        environment_fingerprint=lambda: "test-fingerprint",
        clock=lambda: 123,
    )


def test_ebusy_classifies_as_device_busy() -> None:
    assert classify_error(AlsaProbeError("hw_params", 16, "busy")) == "device_busy"


def test_enoent_and_enodev_classify_as_removed() -> None:
    assert classify_error(AlsaProbeError("open", 2, "gone")) == "device_removed"
    assert classify_error(AlsaProbeError("open", 19, "gone")) == "device_removed"


def test_permission_errors() -> None:
    assert classify_error(AlsaProbeError("open", 1, "denied")) == "permission_denied"
    assert classify_error(AlsaProbeError("open", 13, "denied")) == "permission_denied"


def test_einval_on_exact_setters_is_unsupported_format() -> None:
    assert (
        classify_error(AlsaProbeError("set_format", 22, "fmt")) == "unsupported_format"
    )
    assert (
        classify_error(AlsaProbeError("set_rate", 22, "rate")) == "unsupported_format"
    )
    assert (
        classify_error(AlsaProbeError("set_channels", 22, "ch")) == "unsupported_format"
    )


def test_einval_on_hw_params_is_negotiation_failed() -> None:
    assert (
        classify_error(AlsaProbeError("hw_params", 22, "comb")) == "negotiation_failed"
    )


def test_busy_removed_timeout_produce_no_negative_claim() -> None:
    service = _service()
    for disposition in ("device_busy", "device_removed", "timeout"):
        evidence = service.evidence_from(_result(disposition), stable_device_id="dac")
        assert evidence.supported is None, f"{disposition} != UNSUPPORTED"
        assert evidence.strength is EvidenceStrength.PROBED


def test_environment_failures_produce_no_negative_claim() -> None:
    service = _service()
    for disposition in (
        "permission_denied",
        "protocol_error",
        "internal_error",
        "alsa_runtime_missing",
        "unknown",
    ):
        evidence = service.evidence_from(_result(disposition), stable_device_id="dac")
        assert evidence.supported is None, f"{disposition} != UNSUPPORTED"


def test_exact_open_and_readback_is_supported_opened() -> None:
    service = _service()
    negotiated = PcmTuple(96000, "S32_LE", 2, 24)
    evidence = service.evidence_from(
        _result("OPENED", negotiated=negotiated), stable_device_id="dac"
    )
    assert evidence.supported is True
    assert evidence.strength is EvidenceStrength.OPENED
    assert evidence.tuple == PcmTuple(96000, "S32_LE", 2, 24), (
        "C05: el tuple del evidence lleva el sbits negociado"
    )
    assert evidence.evidence_refs == ("probe:test",)
    assert evidence.environment_fingerprint == "test-fingerprint"
    assert evidence.observed_at_ns == 123


def test_open_with_mismatched_readback_produces_no_positive_claim() -> None:
    service = _service()
    negotiated = PcmTuple(48000, "S16_LE", 2, 16)
    evidence = service.evidence_from(
        _result("OPENED", negotiated=negotiated), stable_device_id="dac"
    )
    assert evidence.supported is None, "readback distinto no prueba soporte"


def test_explicit_exact_rejection_is_negative_probed() -> None:
    service = _service()
    evidence = service.evidence_from(
        _result("unsupported_format"), stable_device_id="dac"
    )
    assert evidence.supported is False
    assert evidence.strength is EvidenceStrength.PROBED


def test_negotiation_failed_is_no_claim_not_false() -> None:
    service = _service()
    evidence = service.evidence_from(
        _result("negotiation_failed"), stable_device_id="dac"
    )
    assert evidence.supported is None, (
        "solo ALSA puede probar mismatch exacto; conservador por defecto"
    )


# ── DAC-C04/C05: readback, sbits negociado, retry exacto ─────────────


def test_readback_failure_is_never_unsupported() -> None:
    """C04: un fallo de readback es negotiation/protocol, nunca soporte."""
    for step in (
        "readback_access",
        "readback_channels",
        "readback_format",
        "readback_rate",
        "readback_sbits",
    ):
        category = classify_error(AlsaProbeError(step, 5, "EIO"))
        assert category == "negotiation_failed", f"{step} -> {category}"
        assert category != "unsupported_format"


def test_readback_einval_is_not_exact_rejection() -> None:
    """C04: EINVAL en readback NO es un rechazo exacto de formato."""
    assert (
        classify_error(AlsaProbeError("readback_format", 22, "einval"))
        == "negotiation_failed"
    )


def test_eio_runtime_ambiguity_stays_no_claim() -> None:
    """C05: EIO/entorno ambiguo permanece supported=None."""
    service = _service()
    for disposition in ("internal_error", "unknown", "alsa_runtime_missing"):
        evidence = service.evidence_from(_result(disposition), stable_device_id="dac")
        assert evidence.supported is None


def test_service_preserves_negotiated_sbits_in_evidence() -> None:
    """C05: el sbits negociado (readback) se preserva en CapabilityEvidence."""
    service = _service()
    negotiated = PcmTuple(96000, "S32_LE", 2, 24)
    evidence = service.evidence_from(
        _result("OPENED", negotiated=negotiated), stable_device_id="dac"
    )
    assert evidence.tuple.significant_bits == 24, (
        "el evidence debe llevar el sbits negociado, no el pedido (None)"
    )


def test_service_preserves_none_when_readback_lacks_sbits() -> None:
    service = _service()
    negotiated = PcmTuple(96000, "S32_LE", 2, None)
    evidence = service.evidence_from(
        _result("OPENED", negotiated=negotiated), stable_device_id="dac"
    )
    assert evidence.tuple.significant_bits is None
