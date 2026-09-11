"""DAC-V35-020 — capability evidence domain types (spec §12 + §401).

Regla crítica de errores:

    BUSY != UNSUPPORTED
    REMOVED != UNSUPPORTED
    TIMEOUT != UNSUPPORTED

Solo un rechazo exacto suficientemente específico puede producir
evidencia negativa de capability.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class EvidenceStrength(Enum):
    DECLARED = "declared"
    DISCOVERED = "discovered"
    PROBED = "probed"
    OPENED = "opened"
    NEGOTIATED = "negotiated"
    RUNTIME_VERIFIED = "runtime_verified"


@dataclass(frozen=True, slots=True)
class PcmTuple:
    rate_hz: int
    transport_format: str
    channels: int
    significant_bits: int | None


@dataclass(frozen=True, slots=True)
class CapabilityEvidence:
    stable_device_id: str
    tuple: PcmTuple

    supported: bool | None
    strength: EvidenceStrength

    source: str
    observed_at_ns: int

    environment_fingerprint: str
    evidence_refs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ExactProbeResult:
    """Resultado tipado del adapter de probe exacto (§401).

    Nunca JSON/dicts crudos: el worker habla JSON versionado, pero la
    aplicación consume este tipo.
    """

    requested: PcmTuple
    negotiated: PcmTuple | None
    disposition: str
    alsa_error_code: int | None
    detail: str | None
    evidence_ref: str
