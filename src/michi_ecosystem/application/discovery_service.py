"""Discovery application service (E4): verification, merge, trust and expiry.

Consumes raw announces from a discovery source, runs the canonical E2
verification pipeline, keeps one record per device, tracks replay/liveness and
exposes plan-aligned dashboard states. Cadence is caller-driven (``poll``), so
the service stays off the GUI thread by construction (master plan §19).
"""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field

from michi_ecosystem.domain.discovery import DiscoveredNode, MdnsHint
from michi_ecosystem.domain.nodes import NodePresence
from michi_ecosystem.domain.trust import TrustLevel
from michi_ecosystem.infrastructure.michi_link.transport import (
    OFFLINE_TIMEOUT_MS,
    DatagramError,
    parse_datagram,
)
from michi_ecosystem.infrastructure.michi_link.verification import (
    nonce_key,
    verify_announce,
)
from michi_ecosystem.ports.discovery import DiscoverySourcePort, RawAnnounce


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


@dataclass(frozen=True)
class HintCorrelation:
    """An unambiguous mDNS hint <-> signed-node match. Grants zero trust."""

    hint: MdnsHint
    node: DiscoveredNode


@dataclass
class DiscoveryService:
    """Node registry with canonical verification and fail-closed trust."""

    source: DiscoverySourcePort | None = None
    offline_timeout_ms: int = OFFLINE_TIMEOUT_MS
    clock: Callable[[], int] = _now_ms
    on_snapshot: Callable[[tuple[DiscoveredNode, ...]], None] | None = None
    _nodes: dict[str, DiscoveredNode] = field(default_factory=dict)
    _seen_nonces: set[tuple[str, str]] = field(default_factory=set)
    _nonce_expiry: dict[tuple[str, str], int] = field(default_factory=dict)
    _last_nonce_cleanup_ms: int | None = None
    # Bounded by design; exhaustion rejects NEW signed announces rather than
    # evicting still-valid replay evidence and making replays possible.
    max_replay_nonces: int = 32768
    max_discovered_nodes: int = 2048
    max_mdns_hints: int = 2048
    _hint_seen_ms: dict[str, int] = field(default_factory=dict)
    _rejected: dict[str, int] = field(default_factory=dict)
    _hints: dict[str, MdnsHint] = field(default_factory=dict)
    _started: bool = False

    def start(self) -> None:
        if self.source is not None:
            self.source.start()
        self._started = True

    def close(self) -> None:
        if self.source is not None:
            self.source.close()
        self._started = False

    def poll(self, *, now_ms: int | None = None) -> int:
        """Drain the source; returns the number of announce datagrams seen."""
        if self.source is None:
            return 0
        raw_announces = self.source.poll()
        for raw in raw_announces:
            self.ingest(raw, now_ms=now_ms)
        poll_hints = getattr(self.source, "poll_hints", None)
        if callable(poll_hints):
            for hint in poll_hints():
                self.observe_hint(hint)
        self._expire_hints(self.clock())
        self._emit_snapshot(now_ms=now_ms)
        return len(raw_announces)

    def ingest(
        self, raw: RawAnnounce, *, now_ms: int | None = None
    ) -> DiscoveredNode | None:
        """Verify and merge one raw announce; None when rejected."""
        timestamp = now_ms if now_ms is not None else self.clock()
        self._expire_replay_nonces(timestamp)
        try:
            payload = parse_datagram(raw.payload)
        except DatagramError:
            self._reject("malformed")
            return None

        result = verify_announce(
            payload,
            now_ms=timestamp,
            seen_nonces=self._seen_nonces,
            source_host=raw.source_host,
        )
        if result.level is TrustLevel.INVALID:
            self._reject(result.reason)
            return None
        # Store nonce only after the signed payload also passes domain and
        # identity-collision checks; a rejected frame must not consume quota.
        if (
            result.level is TrustLevel.VERIFIED
            and len(self._seen_nonces) >= self.max_replay_nonces
        ):
            self._reject("replay_cache_full")
            return None

        try:
            presence = NodePresence.from_announce(payload)
        except ValueError:
            self._reject("malformed")
            return None

        existing = self._nodes.get(presence.device_id)
        if (
            existing is not None
            and existing.identity_verified
            and result.level is not TrustLevel.VERIFIED
        ):
            # An unsigned frame with a reused device_id must NOT renew the
            # cryptographically verified node's liveness. Otherwise a third
            # party can keep an offline receiver apparently online forever.
            self._reject("unverified_identity_collision")
            return None
        if (
            existing is not None
            and existing.identity_verified
            and result.level is TrustLevel.VERIFIED
            and presence.michi_id != existing.presence.michi_id
        ):
            self._reject("verified_identity_collision")
            return None
        # Two device_ids claiming the same verified identity make discovery
        # ambiguous; never let the registry silently prefer the last frame.
        if (
            result.level is TrustLevel.VERIFIED
            and presence.michi_id
            and any(
                other_id != presence.device_id
                and node.identity_verified
                and node.presence.michi_id == presence.michi_id
                and timestamp - node.last_seen_ms <= self.offline_timeout_ms
                for other_id, node in self._nodes.items()
            )
        ):
            self._reject("verified_identity_alias")
            return None
        if (
            presence.device_id not in self._nodes
            and len(self._nodes) >= self.max_discovered_nodes
        ):
            # Expired entries can be dropped at capacity; never evict online
            # verified nodes to make room for attacker-created IDs.
            expired = [
                key
                for key, node in self._nodes.items()
                if timestamp - node.last_seen_ms > self.offline_timeout_ms
            ]
            for key in expired:
                del self._nodes[key]
            if (
                len(self._nodes) >= self.max_discovered_nodes
                and result.level is TrustLevel.VERIFIED
            ):
                # Unsigned devices may flood a LAN, but cannot indefinitely
                # starve a genuinely signed announcement. Preserve verified
                # online nodes; only an unverified entry may be displaced.
                unverified = sorted(
                    (
                        (key, node.last_seen_ms)
                        for key, node in self._nodes.items()
                        if not node.identity_verified
                    ),
                    key=lambda pair: (pair[1], pair[0]),
                )
                if unverified:
                    self._nodes.pop(unverified[0][0], None)
            if len(self._nodes) >= self.max_discovered_nodes:
                self._reject("discovery_capacity_exceeded")
                return None
        merged = DiscoveredNode(
            presence=presence,
            verification=result,
            last_seen_ms=timestamp,
            source_host=raw.source_host,
        )
        self._nodes[presence.device_id] = merged
        if result.level is TrustLevel.VERIFIED:
            key = nonce_key(payload)
            self._seen_nonces.add(key)
            self._nonce_expiry[key] = timestamp
        return merged

    def observe_hint(self, hint: MdnsHint, *, now_ms: int | None = None) -> None:
        """Bound untrusted mDNS hints by age and count; never grant trust."""
        timestamp = now_ms if now_ms is not None else self.clock()
        self._expire_hints(timestamp)
        if (
            hint.device_id not in self._hints
            and len(self._hints) >= self.max_mdns_hints
        ):
            # Hints are unsigned, disposable hints only. Prefer bounded
            # freshness over an ever-growing cache of attacker-supplied IDs.
            oldest = min(self._hint_seen_ms, key=self._hint_seen_ms.get)
            self._hints.pop(oldest, None)
            self._hint_seen_ms.pop(oldest, None)
        self._hints[hint.device_id] = hint
        self._hint_seen_ms[hint.device_id] = timestamp

    def _expire_hints(self, now_ms: int) -> None:
        stale = [
            key
            for key, seen in self._hint_seen_ms.items()
            if now_ms - seen > self.offline_timeout_ms
        ]
        for key in stale:
            self._hint_seen_ms.pop(key, None)
            self._hints.pop(key, None)

    def snapshot(
        self, *, now_ms: int | None = None, include_offline: bool = False
    ) -> tuple[DiscoveredNode, ...]:
        timestamp = now_ms if now_ms is not None else self.clock()
        nodes = [
            node
            for node in self._nodes.values()
            if include_offline
            or timestamp - node.last_seen_ms <= self.offline_timeout_ms
        ]
        return tuple(sorted(nodes, key=lambda node: node.presence.name))

    def verified_identity_nodes(self, **kwargs: object) -> tuple[DiscoveredNode, ...]:
        """Nodes with cryptographically verified identity (NOT paired trust)."""
        return tuple(node for node in self.snapshot(**kwargs) if node.identity_verified)

    def unverified_identity_nodes(self, **kwargs: object) -> tuple[DiscoveredNode, ...]:
        """Discovered nodes without verified identity — pairing/recovery surface."""
        return tuple(
            node for node in self.snapshot(**kwargs) if not node.identity_verified
        )

    def hints(self) -> tuple[MdnsHint, ...]:
        self._expire_hints(self.clock())
        return tuple(sorted(self._hints.values(), key=lambda hint: hint.device_id))

    def correlated_hints(self) -> tuple[HintCorrelation, ...]:
        """Correlate hints with signed nodes ONLY when unambiguous (C6).

        A hint whose ``michi_id`` contradicts the signed node's ``michi_id``
        is a collision: it is excluded (fail closed) and never enriches
        anything. Hints never grant, upgrade or downgrade trust.
        """
        self._expire_hints(self.clock())
        correlations: list[HintCorrelation] = []
        for device_id in sorted(self._hints):
            hint = self._hints[device_id]
            node = self._nodes.get(device_id)
            if node is None or _hint_conflicts(hint, node):
                continue
            correlations.append(HintCorrelation(hint=hint, node=node))
        return tuple(correlations)

    def ambiguous_hint_ids(self) -> tuple[str, ...]:
        """Hints excluded from correlation due to identity collisions."""
        self._expire_hints(self.clock())
        return tuple(
            device_id
            for device_id in sorted(self._hints)
            if (node := self._nodes.get(device_id)) is not None
            and _hint_conflicts(self._hints[device_id], node)
        )

    def rejected_counts(self) -> Mapping[str, int]:
        return dict(self._rejected)

    def ui_state(self, *, now_ms: int | None = None) -> str:
        """Dashboard discovery state (master plan §115.2)."""
        nodes = self.snapshot(now_ms=now_ms)
        if not nodes:
            if self._rejected:
                return "failed"
            return "searching" if self._started else "idle"
        if self._rejected:
            return "needs_attention"
        return "found_one" if len(nodes) == 1 else "found_multiple"

    def _expire_replay_nonces(self, now_ms: int) -> None:
        from michi_ecosystem.infrastructure.michi_link.verification import (
            TIMESTAMP_WINDOW_MS,
        )

        # A nonce older than the signature timestamp acceptance window cannot
        # be replayed successfully even without a cache entry.
        if (
            self._last_nonce_cleanup_ms is not None
            and 0 <= now_ms - self._last_nonce_cleanup_ms < 1000
            and len(self._nonce_expiry) < self.max_replay_nonces
        ):
            return
        self._last_nonce_cleanup_ms = now_ms
        cutoff = now_ms - 2 * TIMESTAMP_WINDOW_MS
        for key, seen_at in tuple(self._nonce_expiry.items()):
            if seen_at < cutoff:
                self._nonce_expiry.pop(key, None)
                self._seen_nonces.discard(key)

    def _emit_snapshot(self, *, now_ms: int | None = None) -> None:
        """Publish one atomic liveness-filtered snapshot to the canonical registry."""
        if self.on_snapshot is not None:
            self.on_snapshot(self.snapshot(now_ms=now_ms))

    def _reject(self, reason: str) -> None:
        self._rejected[reason] = self._rejected.get(reason, 0) + 1


def _hint_conflicts(hint: MdnsHint, node: DiscoveredNode) -> bool:
    """Identity collision: both sides claim a michi_id and they differ."""
    node_michi = node.presence.michi_id or ""
    return bool(hint.michi_id) and bool(node_michi) and hint.michi_id != node_michi
