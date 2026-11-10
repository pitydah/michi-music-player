"""Projection of real Micro Server payloads, with contract conformance (E3).

The ``server-info`` conformance verdict is explicit: a payload that only
diverges by the known extension fields (MICRO-REQ-001) is reported as
NONCONFORMANT_KNOWN, never silently accepted (master plan §155.1).
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from michi_ecosystem.domain.servers import (
    SERVER_INFO_KNOWN_EXTENSIONS,
    DiagnosticsSummary,
    ReceiverSummary,
    ServerConformance,
    ServerHealth,
    ServerInfo,
    ServerInfoResult,
)
from michi_ecosystem.infrastructure.michi_link.contracts import (
    ContractBundle,
    ContractViolation,
)


def project_server_info(
    payload: Mapping[str, Any], contracts: ContractBundle | None
) -> ServerInfoResult:
    conformance = ServerConformance.UNVALIDATED
    if contracts is not None:
        conformance = _server_info_conformance(payload, contracts)
    return ServerInfoResult(ServerInfo.from_payload(payload), conformance)


def _server_info_conformance(
    payload: Mapping[str, Any], contracts: ContractBundle
) -> ServerConformance:
    try:
        contracts.validate("server-info", payload)
    except ContractViolation:
        trimmed = {
            key: value
            for key, value in payload.items()
            if key not in SERVER_INFO_KNOWN_EXTENSIONS
        }
        try:
            contracts.validate("server-info", trimmed)
        except ContractViolation:
            return ServerConformance.NONCONFORMANT
        return ServerConformance.NONCONFORMANT_KNOWN
    return ServerConformance.CONFORMANT


def project_health(payload: Mapping[str, Any]) -> ServerHealth:
    return ServerHealth.from_payload(payload)


def project_diagnostics(payload: Mapping[str, Any]) -> DiagnosticsSummary:
    return DiagnosticsSummary.from_payload(payload)


def project_receivers(payload: Mapping[str, Any]) -> tuple[ReceiverSummary, ...]:
    raw = payload.get("receivers")
    if not isinstance(raw, list):
        return ()
    return tuple(
        ReceiverSummary.from_payload(item) for item in raw if isinstance(item, Mapping)
    )
