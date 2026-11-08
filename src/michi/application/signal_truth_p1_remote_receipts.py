"""AP2-F11 A48: FUTURE-only remote self-report, bounded replay projection.

This is a contract/fixture for Michi Micro/Big/Stream. It is NOT a network
listener, auth verifier, endpoint controller, or trusted DAC physical oracle.
F12+ remains locked. The transport's authenticated status must be supplied by
an external trusted owner and still only permits REMOTE_REPORTED.
"""

from __future__ import annotations

from dataclasses import dataclass

_FAMILIES = frozenset(
    {"direct_pcm", "managed_pcm", "shared_pcm", "dsd_to_pcm", "native_dsd", "dop"}
)
_PROVIDERS = frozenset({"michi_micro_server", "michi_big_server", "michi_stream"})


@dataclass(frozen=True, slots=True)
class RemoteReport:
    schema_version: int
    endpoint_id: str
    producer: str
    route_epoch: int
    sequence: int
    issued_ms: int
    ttl_ms: int
    family: str
    state: str

    def __post_init__(self) -> None:
        if self.schema_version != 1 or self.producer not in _PROVIDERS:
            raise ValueError("unknown remote receipt schema or producer")
        if (
            not isinstance(self.endpoint_id, str)
            or not 1 <= len(self.endpoint_id) <= 128
        ):
            raise ValueError("endpoint is not an opaque identifier")
        if any(ord(c) < 33 or ord(c) > 126 for c in self.endpoint_id):
            raise ValueError("endpoint contains unsafe characters")
        if any(
            type(n) is not int or n <= 0
            for n in (self.route_epoch, self.sequence, self.issued_ms)
        ):
            raise ValueError("invalid epoch sequence or receipt clock")
        if type(self.ttl_ms) is not int or not 1 <= self.ttl_ms <= 30_000:
            raise ValueError("bounded TTL required")
        if self.family not in _FAMILIES or self.state not in {
            "READY",
            "RUNNING",
            "RELEASED",
            "UNAVAILABLE",
        }:
            raise ValueError("invalid family/state")


@dataclass(frozen=True, slots=True)
class RemoteProjection:
    status: str
    boundary: str
    family: str
    reason: str


class RemoteReceiptWindow:
    """Memory-bounded replay/TTL state, single owner thread only.

    Authentication is NEVER inferred from a receipt field, a device name,
    endpoint ID, mDNS/Whisker discovery or a matching sequence.
    """

    def __init__(self, max_endpoints: int = 64) -> None:
        if type(max_endpoints) is not int or not 1 <= max_endpoints <= 256:
            raise ValueError("invalid endpoint budget")
        self._max = max_endpoints
        self._latest: dict[str, tuple[int, int]] = {}

    def consider(
        self, receipt: RemoteReport, *, now_ms: int, owner_authenticated: bool = False
    ) -> RemoteProjection:
        if type(now_ms) is not int or now_ms <= 0:
            raise ValueError("trusted time required")

        def refusal(reason: str) -> RemoteProjection:
            return RemoteProjection("UNOBSERVED", "NONE", "unknown", reason)

        if owner_authenticated is not True:
            return refusal("ST_P1_REMOTE_AUTHENTICATION_MISSING")
        if receipt.issued_ms > now_ms + 1000:
            return refusal("ST_P1_REMOTE_FUTURE_CLOCK")
        if now_ms > receipt.issued_ms + receipt.ttl_ms:
            return refusal("ST_P1_REMOTE_EXPIRED")
        prior = self._latest.get(receipt.endpoint_id)
        if prior is not None and (receipt.route_epoch, receipt.sequence) <= prior:
            return refusal("ST_P1_REMOTE_REPLAY_OR_STALE")
        if prior is not None and receipt.route_epoch < prior[0]:
            return refusal("ST_P1_REMOTE_REPLAY_OR_STALE")
        if prior is None and len(self._latest) >= self._max:
            return refusal("ST_P1_REMOTE_ENDPOINT_BUDGET")
        self._latest[receipt.endpoint_id] = (receipt.route_epoch, receipt.sequence)
        if receipt.state in {"RELEASED", "UNAVAILABLE"}:
            return RemoteProjection(
                "REMOTE_TERMINATED",
                "REMOTE_REPORTED",
                receipt.family,
                "ST_P1_REMOTE_TERMINAL",
            )
        return RemoteProjection(
            "REMOTE_REPORTED",
            "REMOTE_REPORTED",
            receipt.family,
            "ST_P1_REMOTE_SELF_REPORT_ONLY",
        )
