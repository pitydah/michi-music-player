"""Health service (E8): compose upstream signals into one canonical summary.

Composes the Micro Server port (reachability, database, diagnostics, contract
conformance, receivers) and the discovery service (rejected announces) into
stable issue codes with repair actions. Raw exceptions are mapped to human
copy; nothing here talks to the network directly, so callers keep I/O off the
GUI thread (master plan §51, §114.9).

Issue codes:
- HEALTH-MICRO-OFFLINE      error   → Micro Server page
- HEALTH-MICRO-DB           error   → diagnostics
- HEALTH-MICRO-DEGRADED     warning → diagnostics
- HEALTH-MICRO-CONFORMANCE  warning → diagnostics (MICRO-REQ-001)
- HEALTH-RECEIVER-PENDING   warning → streams/discovery
- HEALTH-DISCOVERY-REJECTED warning → diagnostics
"""

from __future__ import annotations

from michi_ecosystem.domain.health import (
    HealthIssue,
    HealthState,
    HealthSummary,
    IssueSeverity,
)
from michi_ecosystem.domain.servers import ServerConformance
from michi_ecosystem.ports.micro_server import MicroServerPort, MicroServerRequestError


class HealthService:
    def __init__(self, micro: MicroServerPort, *, discovery=None) -> None:
        self._micro = micro
        self._discovery = discovery

    def summary(self) -> HealthSummary:
        issues: list[HealthIssue] = []

        micro_online = True
        try:
            health = self._micro.health()
        except MicroServerRequestError:
            micro_online = False
            health = None
            issues.append(
                HealthIssue(
                    code="HEALTH-MICRO-OFFLINE",
                    severity=IssueSeverity.ERROR,
                    title="Micro Server no responde",
                    detail=(
                        "Los dispositivos del ecosistema no están disponibles "
                        "hasta que vuelva la conexión."
                    ),
                    repair_route="ecosystem/micro-server",
                    repair_label="Revisar Micro Server",
                )
            )

        if micro_online and health is not None:
            if not health.database_connected:
                issues.append(
                    HealthIssue(
                        code="HEALTH-MICRO-DB",
                        severity=IssueSeverity.ERROR,
                        title="La biblioteca no está disponible",
                        detail="El Micro Server no puede acceder a su base de datos.",
                        repair_route="ecosystem/diagnostics",
                        repair_label="Ver diagnóstico",
                    )
                )

            try:
                diagnostics = self._micro.diagnostics()
            except MicroServerRequestError:
                diagnostics = None
            if diagnostics is not None and (
                diagnostics.degraded or diagnostics.warnings
            ):
                detail = (
                    "; ".join(diagnostics.warnings[:2])
                    or "El Micro Server reporta estado degradado."
                )
                issues.append(
                    HealthIssue(
                        code="HEALTH-MICRO-DEGRADED",
                        severity=IssueSeverity.WARNING,
                        title="El Micro Server reporta problemas menores",
                        detail=detail,
                        repair_route="ecosystem/diagnostics",
                        repair_label="Ver diagnóstico",
                    )
                )

            try:
                info = self._micro.server_info()
            except MicroServerRequestError:
                info = None
            if info is not None and info.conformance in (
                ServerConformance.NONCONFORMANT_KNOWN,
                ServerConformance.NONCONFORMANT,
            ):
                known = info.conformance is ServerConformance.NONCONFORMANT_KNOWN
                issues.append(
                    HealthIssue(
                        code="HEALTH-MICRO-CONFORMANCE",
                        severity=IssueSeverity.WARNING,
                        title="El Micro Server difiere del contrato certificado",
                        detail=(
                            "Divergencia conocida registrada (MICRO-REQ-001)."
                            if known
                            else "El contrato difiere de lo certificado."
                        ),
                        repair_route="ecosystem/diagnostics",
                        repair_label="Ver diagnóstico",
                    )
                )

            try:
                receivers = self._micro.receivers()
            except MicroServerRequestError:
                receivers = ()
            pending = tuple(r for r in receivers if r.pairing_pending)
            if pending:
                issues.append(
                    HealthIssue(
                        code="HEALTH-RECEIVER-PENDING",
                        severity=IssueSeverity.WARNING,
                        title=f"{len(pending)} dispositivo(s) esperan vinculación",
                        detail=pending[0].name or pending[0].receiver_id,
                        repair_route="ecosystem/streams",
                        repair_label="Revisar dispositivos",
                    )
                )

        if self._discovery is not None:
            rejected = sum(self._discovery.rejected_counts().values())
            if rejected > 0:
                issues.append(
                    HealthIssue(
                        code="HEALTH-DISCOVERY-REJECTED",
                        severity=IssueSeverity.WARNING,
                        title="Se rechazaron anuncios de discovery",
                        detail=(
                            f"{rejected} anuncio(s) inválidos o repetidos fueron "
                            "descartados."
                        ),
                        repair_route="ecosystem/diagnostics",
                        repair_label="Ver diagnóstico",
                    )
                )

        return HealthSummary(state=_state(micro_online, issues), issues=tuple(issues))


def _state(micro_online: bool, issues: list[HealthIssue]) -> HealthState:
    if not micro_online:
        return HealthState.OFFLINE
    if any(issue.severity is IssueSeverity.ERROR for issue in issues):
        return HealthState.ACTION_REQUIRED
    if issues:
        return HealthState.DEGRADED
    return HealthState.HEALTHY
