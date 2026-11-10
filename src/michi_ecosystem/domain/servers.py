"""Micro Server read models projected from the real ``/api/v1`` payloads.

Shapes are grounded on michi-micro-server ``crates/michi-api/src/routes/v1/``
(server.rs, receivers.rs, diagnostics.rs) and mapped against the vendored
Michi Link ``server-info`` schema where applicable (master plan §154).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
from types import MappingProxyType
from typing import Any


class ServerConformance(StrEnum):
    """How a live server payload relates to the vendored contract."""

    CONFORMANT = "conformant"
    NONCONFORMANT_KNOWN = "nonconformant_known"
    NONCONFORMANT = "nonconformant"
    UNVALIDATED = "unvalidated"


# Fields the real michi-micro-server exposes beyond the vendored server-info
# schema (MICRO-REQ-001 in UPSTREAM_REQUIREMENTS.md). Never silently accepted:
# projection surfaces NONCONFORMANT_KNOWN for them.
SERVER_INFO_KNOWN_EXTENSIONS = frozenset({"deployment_platform", "commit"})


def _require_text(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing required string field: {key}")
    return value


def _int(payload: Mapping[str, Any], key: str, default: int = 0) -> int:
    value = payload.get(key)
    if isinstance(value, (int, float)):
        return int(value)
    return default


def _bool(payload: Mapping[str, Any], key: str, default: bool = False) -> bool:
    value = payload.get(key)
    return bool(value) if isinstance(value, bool) else default


@dataclass(frozen=True)
class ServerInfo:
    """``GET /api/v1/server/info`` (V1ServerInfo in server.rs)."""

    service: str
    name: str
    server_id: str
    version: str
    api_version: str
    roles: tuple[str, ...]
    features: Mapping[str, bool]
    auth_required: bool
    auth_strategy: str
    token_refresh: bool
    deployment_platform: str = ""
    commit: str | None = None
    michi_home_id: str = ""

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ServerInfo:
        roles = payload.get("roles")
        features = payload.get("features")
        auth = payload.get("auth")
        commit = payload.get("commit")
        return cls(
            service=_require_text(payload, "service"),
            name=_require_text(payload, "name"),
            server_id=_require_text(payload, "server_id"),
            version=_require_text(payload, "version"),
            api_version=_require_text(payload, "api_version"),
            roles=tuple(str(role) for role in (roles or ())),
            features=MappingProxyType(
                {str(key): bool(value) for key, value in (features or {}).items()}
            ),
            auth_required=_bool(auth or {}, "required"),
            auth_strategy=str((auth or {}).get("strategy", "")),
            token_refresh=_bool(auth or {}, "token_refresh"),
            deployment_platform=str(payload.get("deployment_platform", "")),
            commit=str(commit) if isinstance(commit, str) and commit else None,
            # Michi Link alpha.6: stream receivers announce their Home identity.
            # This is a claim from the server payload, never Home authority.
            michi_home_id=str(payload.get("michi_home_id", "")),
        )

    def capabilities(self) -> tuple[str, ...]:
        """Enabled feature flags, sorted."""
        return tuple(sorted(name for name, enabled in self.features.items() if enabled))

    def feature_enabled(self, name: str) -> bool:
        return bool(self.features.get(name, False))


@dataclass(frozen=True)
class ServerInfoResult:
    """Server info plus its conformance verdict against the vendored contract."""

    info: ServerInfo
    conformance: ServerConformance


@dataclass(frozen=True)
class ServerHealth:
    """``GET /api/v1/status`` (status_handler in server.rs)."""

    status: str
    database_connected: bool
    uptime_seconds: int
    version: str
    port: int

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ServerHealth:
        return cls(
            status=str(payload.get("status", "")),
            database_connected=str(payload.get("database", "")) == "connected",
            uptime_seconds=_int(payload, "uptime_seconds"),
            version=str(payload.get("version", "")),
            port=_int(payload, "port"),
        )


@dataclass(frozen=True)
class DiagnosticsSummary:
    """Compact projection of ``GET /api/v1/diagnostics`` (DiagnosticsReport)."""

    healthy: bool
    degraded: bool
    db_connected: bool
    total_tracks: int
    uptime_seconds: int
    warnings: tuple[str, ...]

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> DiagnosticsSummary:
        db = payload.get("db") or {}
        system = payload.get("system") or {}
        warnings = payload.get("warnings") or ()
        return cls(
            healthy=_bool(payload, "healthy"),
            degraded=_bool(payload, "degraded"),
            db_connected=_bool(db, "connected"),
            total_tracks=_int(db, "total_tracks"),
            uptime_seconds=_int(system, "uptime_seconds"),
            warnings=tuple(str(item) for item in warnings),
        )


@dataclass(frozen=True)
class ReceiverSummary:
    """One entry of ``GET /api/v1/receivers`` (receivers_handler)."""

    receiver_id: str
    michi_id: str
    name: str
    device_type: str
    host: str
    paired: bool
    online: bool
    verified: bool
    reachable: bool
    session_active: bool
    last_seen: int | None

    @classmethod
    def from_payload(cls, payload: Mapping[str, Any]) -> ReceiverSummary:
        last_seen = payload.get("last_seen")
        return cls(
            receiver_id=_require_text(payload, "receiver_id"),
            michi_id=str(payload.get("michi_id", "")),
            name=str(payload.get("name", "")),
            device_type=str(payload.get("device_type", "")),
            host=str(payload.get("base_url", payload.get("host", ""))),
            paired=_bool(payload, "paired"),
            online=_bool(payload, "online"),
            verified=_bool(payload, "verified"),
            reachable=_bool(payload, "reachable"),
            session_active=_bool(payload, "session_active"),
            last_seen=int(last_seen) if isinstance(last_seen, (int, float)) else None,
        )

    @property
    def pairing_pending(self) -> bool:
        """Not paired yet, or discovered but still unverified."""
        return not self.paired or (self.online and not self.verified)
