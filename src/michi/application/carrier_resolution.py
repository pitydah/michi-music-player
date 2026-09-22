"""DAC-V35-100R1.3 — bounded candidate carrier resolution.

The historical helper collapsed two different facts into one decision:

    source significant bits  ->  transport carrier format

That is wrong. Significant bits belong to the SIGNAL; the transport format is
the CARRIER. A DAC may reject the narrowest lossless carrier while still
transporting the very same signal losslessly through a wider container.

This module is pure policy. It never probes hardware, never claims capability
and never invents support: it only produces a small, deterministic, ordered set
of policy-authorized candidates. Physical qualification remains the authority.

Rules:

- ``significant_bits is None`` (unknown) NEVER produces a candidate, and never
  produces an adaptation.
- The exact candidate preserves today's canonical mapping (S16_LE for <= 16
  significant bits, S32_LE for <= 24).
- ``CONTAINER_WIDTH`` candidates exist only for sources whose significant bits
  fit strictly inside the wider carrier; the signal width is preserved, so the
  carrier adds no precision and removes none.
- The candidate set is bounded (``MAX_CANDIDATES``); no dynamic enumeration.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from michi.domain.audio_evidence import DecodedSourceSignal, PcmTuple


class CarrierAdaptationKind(Enum):
    """How a candidate relates to the decoded source signal."""

    EXACT = "exact"
    CONTAINER_WIDTH = "container_width"


@dataclass(frozen=True, slots=True)
class CarrierCandidate:
    tuple: PcmTuple
    adaptation_kind: CarrierAdaptationKind
    priority: int

    @property
    def is_exact(self) -> bool:
        return self.adaptation_kind is CarrierAdaptationKind.EXACT


class CandidateCarrierResolver:
    """Deterministic, policy-bounded carrier candidate resolution."""

    MAX_CANDIDATES = 3

    #: Widest lossless integer container the Stable Direct policy authorizes.
    WIDE_CONTAINER_FORMAT = "S32_LE"
    NARROW_CONTAINER_FORMAT = "S16_LE"

    def candidates(
        self,
        source: DecodedSourceSignal,
        *,
        allow_adaptation: bool,
    ) -> tuple[CarrierCandidate, ...]:
        """Ordered candidates for one decoded source signal.

        ``allow_adaptation`` is the caller's POLICY decision (compatible Direct
        allows bounded container-width adaptation; strict Direct does not).
        """
        bits = source.significant_bits
        if bits is None or source.rate_hz <= 0 or source.channels <= 0:
            return ()
        exact_format = self._exact_format(bits)
        if exact_format is None:
            return ()
        resolved: list[CarrierCandidate] = [
            CarrierCandidate(
                tuple=PcmTuple(
                    rate_hz=source.rate_hz,
                    transport_format=exact_format,
                    channels=source.channels,
                    significant_bits=bits,
                ),
                adaptation_kind=CarrierAdaptationKind.EXACT,
                priority=0,
            )
        ]
        if allow_adaptation and bits <= 16:
            resolved.append(
                CarrierCandidate(
                    tuple=PcmTuple(
                        rate_hz=source.rate_hz,
                        transport_format=self.WIDE_CONTAINER_FORMAT,
                        channels=source.channels,
                        significant_bits=bits,
                    ),
                    adaptation_kind=CarrierAdaptationKind.CONTAINER_WIDTH,
                    priority=1,
                )
            )
        return tuple(resolved[: self.MAX_CANDIDATES])

    @staticmethod
    def _exact_format(significant_bits: int) -> str | None:
        """Canonical narrowest lossless carrier for a proven signal width."""
        if significant_bits <= 16:
            return CandidateCarrierResolver.NARROW_CONTAINER_FORMAT
        if significant_bits <= 24:
            return CandidateCarrierResolver.WIDE_CONTAINER_FORMAT
        # Wider than the authorized lossless integer container: no candidate.
        return None
