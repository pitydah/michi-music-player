"""Node identity and presence read models projected from validated contracts.

Pure projections from receiver-v1-lite payloads (already schema-validated by
``infrastructure.michi_link.contracts``) into domain read models. No registry,
no state machine and no network here — those arrive with the E3 node registry.

Phase: E2 (identity projection).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any


def _require_str(document: Mapping[str, Any], key: str) -> str:
    value = document.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"missing required string field: {key}")
    return value


@dataclass(frozen=True)
class NodeIdentity:
    """Public Ed25519 identity document (michi-identity.schema.json)."""

    michi_id: str
    public_key: str
    device_name: str = ""
    identity_scheme: str = "ed25519-blake3-v1"

    @classmethod
    def from_document(cls, document: Mapping[str, Any]) -> NodeIdentity:
        return cls(
            michi_id=_require_str(document, "michi_id"),
            public_key=_require_str(document, "public_key"),
            device_name=str(document.get("device_name", "")),
            identity_scheme=str(document.get("identity_scheme", "ed25519-blake3-v1")),
        )


@dataclass(frozen=True)
class NodePresence:
    """Functional announce fields (discovery-announce.schema.json)."""

    device_id: str
    name: str
    service: str
    roles: tuple[str, ...]
    api_version: str
    host: str
    port: int
    features: Mapping[str, bool]
    michi_id: str | None = None
    public_key: str | None = None

    @classmethod
    def from_announce(cls, announce: Mapping[str, Any]) -> NodePresence:
        raw_roles = announce.get("roles")
        if not isinstance(raw_roles, list) or not raw_roles:
            raise ValueError("announce is missing its roles")
        raw_features = announce.get("features")
        if not isinstance(raw_features, dict) or not raw_features:
            raise ValueError("announce is missing its features")
        if not all(isinstance(role, str) and role.strip() for role in raw_roles):
            raise ValueError("announce roles must be non-empty strings")
        if not all(
            isinstance(key, str) and isinstance(value, bool)
            for key, value in raw_features.items()
        ):
            raise ValueError("announce features must be boolean flags")
        port = announce.get("port")
        if (
            isinstance(port, bool)
            or not isinstance(port, int)
            or not (1 <= port <= 65535)
        ):
            raise ValueError("announce port must be an integer between 1 and 65535")
        return cls(
            device_id=_require_str(announce, "device_id"),
            name=_require_str(announce, "name"),
            service=_require_str(announce, "service"),
            roles=tuple(str(role) for role in raw_roles),
            api_version=_require_str(announce, "api_version"),
            host=_require_str(announce, "host"),
            port=port,
            features=MappingProxyType(dict(raw_features)),
            michi_id=str(announce.get("michi_id"))
            if announce.get("michi_id")
            else None,
            public_key=(
                str(announce.get("public_key")) if announce.get("public_key") else None
            ),
        )
