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


def intrinsic_pcm_significant_bits(transport_format: str | None) -> int | None:
    """Return precision proved by an intrinsically unambiguous PCM format.

    Container formats such as S32 and S24-in-32 deliberately remain unknown.
    This function classifies format semantics only; it never infers sample
    content, device capability, or active-runtime ownership.
    """
    normalized = (transport_format or "").strip().replace("-", "_").upper()
    if normalized in {"S8", "U8"}:
        return 8
    compact = normalized.replace("_", "")
    if compact in {"S16LE", "S16BE", "U16LE", "U16BE"}:
        return 16
    if normalized in {"S24_3LE", "S24_3BE", "U24_3LE", "U24_3BE"}:
        return 24
    if normalized in {"S24LE", "S24BE", "U24LE", "U24BE"}:
        return 24
    return None


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


@dataclass(frozen=True, slots=True)
class DecodedSourceSignal:
    """Señal de fuente decodificada (§16). Stable first target: PCM estéreo."""

    encoding: str
    rate_hz: int
    significant_bits: int | None
    channels: int
    channel_positions: tuple[str, ...] | None


@dataclass(frozen=True, slots=True)
class SourceFileFacts:
    """Container/metadata facts; never evidence of decoded runtime caps."""

    container: str | None
    codec: str | None
    nominal_pcm: PcmTuple | None
