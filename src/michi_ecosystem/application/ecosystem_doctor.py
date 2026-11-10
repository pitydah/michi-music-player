"""E11.6: bounded evidence-based incident read-model; never auto-repairs."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from michi_ecosystem.domain.device_registry import (
    DeviceDescriptor,
    DeviceType,
    HomeMembershipState,
)


@dataclass(frozen=True)
class DoctorIssue:
    code: str
    severity: str
    title: str
    detail: str
    route: str
    action: str
    # Where the evidence came from (snapshot section). Stable, non-secret.
    source: str = ""

    def projection(self) -> dict[str, str]:
        return {
            "code": self.code,
            "severity": self.severity,
            "title": self.title,
            "detail": self.detail,
            "route": self.route,
            "action": self.action,
            "source": self.source,
        }


class EcosystemDoctor:
    """Compute current incidents from a snapshot, never accumulated history.

    `micro: None` is *unknown*, not evidence of failure. In particular old
    discovery rejection counters are not active incident evidence.
    """

    def inspect(
        self, snapshot: Mapping[str, Any], devices: Iterable[DeviceDescriptor]
    ) -> tuple[DoctorIssue, ...]:
        issues: list[DoctorIssue] = []
        servers = snapshot.get("servers")
        micro = servers.get("micro") if isinstance(servers, dict) else None
        health = snapshot.get("health")
        micro_offline_from_health = isinstance(health, dict) and any(
            isinstance(item, dict) and item.get("code") == "HEALTH-MICRO-OFFLINE"
            for item in health.get("issues", ())
        )
        if (
            isinstance(micro, dict)
            and micro
            and str(micro.get("presence", "")) == "offline"
        ) or micro_offline_from_health:
            issues.append(
                DoctorIssue(
                    "DOCTOR-MICRO-OFFLINE",
                    "warning",
                    "Michi Micro Server no responde",
                    "Otros servicios locales pueden seguir disponibles.",
                    "ecosystem/micro-server",
                    "Revisar servidor",
                    source="servers.micro",
                )
            )
        home = snapshot.get("home")
        if isinstance(home, dict) and home.get("state") == "locked":
            issues.append(
                DoctorIssue(
                    "DOCTOR-HOME-LOCKED",
                    "warning",
                    "Michi Home bloqueado",
                    "Las operaciones administrativas requieren desbloquear Home.",
                    "ecosystem/home",
                    "Abrir Michi Home",
                    source="home",
                )
            )
        link = snapshot.get("link")
        if isinstance(link, dict) and link.get("state") == "degraded":
            issues.append(
                DoctorIssue(
                    "DOCTOR-LINK-DEGRADED",
                    "warning",
                    "Michi Link necesita atención",
                    "Revisa el estado de descubrimiento y los contratos.",
                    "ecosystem/michi-link",
                    "Revisar Michi Link",
                    source="servers.link",
                )
            )
        discovery = snapshot.get("discovery")
        if isinstance(discovery, dict) and discovery.get("state") == "failed":
            issues.append(
                DoctorIssue(
                    "DOCTOR-DISCOVERY-FAILED",
                    "warning",
                    "Discovery no completó la búsqueda",
                    "Revisa interfaces, multicast y mDNS.",
                    "ecosystem/discovery",
                    "Revisar red",
                    source="discovery",
                )
            )
        for device in devices:
            if (
                device.home_membership is HomeMembershipState.ACTIVE
                and not device.online
            ):
                category = (
                    "Stream"
                    if device.type is DeviceType.MUSIC_STREAM
                    else "Dispositivo"
                )
                issues.append(
                    DoctorIssue(
                        "DOCTOR-DEVICE-OFFLINE:" + device.canonical_id,
                        "warning",
                        f"{category} sin conexión",
                        "Comprobar energía, red y anuncios recientes.",
                        "ecosystem/devices",
                        "Abrir dispositivos",
                        source="device_registry",
                    )
                )
        # Only live health incidents from the host are used. The cumulative
        # rejected_counts metric describes history, not a current breakdown.
        if isinstance(health, dict):
            for issue in health.get("issues", ()):
                if not isinstance(issue, dict):
                    continue
                code = str(issue.get("code", ""))
                if not code or code in {
                    "HEALTH-DISCOVERY-REJECTED",
                    "HEALTH-MICRO-OFFLINE",
                }:
                    continue
                if not code.startswith("HEALTH-"):
                    continue
                sev = (
                    "error"
                    if issue.get("severity") in ("error", "critical")
                    else "warning"
                )
                issues.append(
                    DoctorIssue(
                        code,
                        sev,
                        str(issue.get("title", "Revisión pendiente"))[:120],
                        "Consulta el componente para obtener información actualizada.",
                        "ecosystem/diagnostics",
                        "Ver detalles",
                        source="health",
                    )
                )
        return tuple(sorted(issues, key=lambda x: (x.severity != "error", x.code)))

    def projection(
        self, snapshot: Mapping[str, Any], devices: Iterable[DeviceDescriptor]
    ) -> dict[str, Any]:
        devices = tuple(devices)
        issues = self.inspect(snapshot, devices)
        # An overall provider alarm cannot be silently reduced just because
        # its detailed issue list contains only warnings. Micro-only offline is
        # deliberately scoped: it does not mean Michi Home is offline.
        upstream = snapshot.get("health")
        upstream_state = (
            str(upstream.get("state", "unknown"))
            if isinstance(upstream, dict)
            else "unknown"
        )
        codes = {issue.code for issue in issues}
        micro_only = upstream_state == "offline" and codes == {"DOCTOR-MICRO-OFFLINE"}
        has_error = any(issue.severity == "error" for issue in issues)
        if (
            upstream_state in {"offline", "action_required"}
            and not has_error
            and not micro_only
        ):
            # The legacy HealthService uses OFFLINE for Micro Server reachability;
            # with no more precise evidence, report at least degraded. When there
            # are other issues, or ACTION_REQUIRED, do not lower a serious alarm.
            severity = (
                "warning" if upstream_state == "offline" and not issues else "error"
            )
            issues = (
                *issues,
                DoctorIssue(
                    "DOCTOR-HEALTH-UNSPECIFIED",
                    severity,
                    "El proveedor informa un problema de salud",
                    "El proveedor requiere atención, pero no entregó "
                    "evidencia suficiente para explicar la causa.",
                    "ecosystem/diagnostics",
                    "Revisar diagnóstico",
                    source="health",
                ),
            )
        elif upstream_state == "degraded" and not issues:
            issues = (
                DoctorIssue(
                    "DOCTOR-HEALTH-UNSPECIFIED",
                    "warning",
                    "Estado degradado sin detalles",
                    "El proveedor indica una anomalía sin diagnóstico verificable.",
                    "ecosystem/diagnostics",
                    "Revisar diagnóstico",
                    source="health",
                ),
            )
        # Preserve deterministic display order even when adding a synthetic issue.
        issues = tuple(sorted(issues, key=lambda x: (x.severity != "error", x.code)))
        if any(issue.severity == "error" for issue in issues):
            state = "action_required"
        elif issues:
            state = "degraded"
        else:
            servers = snapshot.get("servers")
            micro = servers.get("micro") if isinstance(servers, dict) else None
            home = snapshot.get("home")
            link = snapshot.get("link")
            # A dictionary with an unknown status is NOT positive evidence.
            affirmative = (
                upstream_state == "healthy"
                or (isinstance(micro, dict) and micro.get("presence") == "online")
                or (
                    isinstance(home, dict)
                    and home.get("state") in {"active", "ready", "unlocked"}
                )
                or (isinstance(link, dict) and link.get("state") == "operational")
                or any(
                    device.online and device.trusted_home_member for device in devices
                )
            )
            state = "healthy" if affirmative else "unknown"
        return {
            "state": state,
            "issues": [issue.projection() for issue in issues],
            "issueCount": len(issues),
        }
