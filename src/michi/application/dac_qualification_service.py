"""DAC-V35-020 — DacQualificationService (spec §401).

Decide si un ExactProbeResult puede producir capability evidence:

    exact open + exact readback       -> supported=True,  OPENED
    rechazo exacto format/rate        -> supported=False, PROBED
    BUSY / REMOVED / TIMEOUT          -> supported=None
    permission/runtime/protocol error -> supported=None
    requested != negotiated           -> supported=None (negotiation_failed)

Nunca brute-force de matrices al startup (§14).
"""

from __future__ import annotations

import os
import platform
import sys
import time
from collections.abc import Callable

from michi.domain.audio_evidence import (
    CapabilityEvidence,
    EvidenceStrength,
    ExactProbeResult,
    PcmTuple,
)

SOURCE = "michi-alsa-probe"

_NEGATIVE_DISPOSITIONS = {"unsupported_format"}
# BUSY/REMOVED/TIMEOUT y fallos de entorno NUNCA son negativos (§12).


def _exact_match(requested: PcmTuple, negotiated: PcmTuple | None) -> bool:
    """El readback prueba el tuple exacto (rate/format/channels).

    significant_bits es diagnóstico del readback (sbits), no parte del
    pedido; compararlo contra None del requested sería falso negativo.
    """
    if negotiated is None:
        return False
    return (
        negotiated.rate_hz == requested.rate_hz
        and negotiated.transport_format == requested.transport_format
        and negotiated.channels == requested.channels
    )


def default_environment_fingerprint() -> str:
    return (
        f"{platform.system()}-{platform.release()}-{os.uname().machine}"
        f"-py{sys.version_info.major}.{sys.version_info.minor}"
    )


class DacQualificationService:
    def __init__(
        self,
        adapter: object,
        *,
        environment_fingerprint: Callable[[], str] = default_environment_fingerprint,
        clock: Callable[[], int] = time.monotonic_ns,
    ) -> None:
        self._adapter = adapter
        self._environment_fingerprint = environment_fingerprint
        self._clock = clock

    def qualify_exact(
        self,
        *,
        stable_device_id: str,
        locator: str,
        rate_hz: int,
        transport_format: str,
        channels: int,
    ) -> CapabilityEvidence:
        result: ExactProbeResult = self._adapter.probe_exact(
            locator=locator,
            rate_hz=rate_hz,
            transport_format=transport_format,
            channels=channels,
        )
        return self.evidence_from(result, stable_device_id=stable_device_id)

    def evidence_from(
        self, result: ExactProbeResult, *, stable_device_id: str
    ) -> CapabilityEvidence:
        requested = result.requested
        exact = _exact_match(requested, result.negotiated)
        if result.disposition == "OPENED" and exact:
            return self._evidence(
                stable_device_id,
                requested,
                supported=True,
                strength=EvidenceStrength.OPENED,
                evidence_ref=result.evidence_ref,
            )
        if result.disposition in _NEGATIVE_DISPOSITIONS:
            # Solo un rechazo exacto documentado produce evidencia negativa.
            return self._evidence(
                stable_device_id,
                requested,
                supported=False,
                strength=EvidenceStrength.PROBED,
                evidence_ref=result.evidence_ref,
            )
        # BUSY/REMOVED/TIMEOUT/permission/runtime/protocol: sin claim.
        return self._evidence(
            stable_device_id,
            requested,
            supported=None,
            strength=EvidenceStrength.PROBED,
            evidence_ref=result.evidence_ref,
        )

    def _evidence(
        self,
        stable_device_id: str,
        pcm_tuple: PcmTuple,
        *,
        supported: bool | None,
        strength: EvidenceStrength,
        evidence_ref: str,
    ) -> CapabilityEvidence:
        return CapabilityEvidence(
            stable_device_id=stable_device_id,
            tuple=pcm_tuple,
            supported=supported,
            strength=strength,
            source=SOURCE,
            observed_at_ns=self._clock(),
            environment_fingerprint=self._environment_fingerprint(),
            evidence_refs=(evidence_ref,),
        )
