"""Firmware compatibility evaluation (C4) — explicit statuses, no fake checks.

Fields whose upstream contract is unfinished are NEVER silently ignored:
they surface as ``NOT_ENFORCED_UPSTREAM_OPEN`` and are registered as exact
upstream requirements (STREAM-REQ-008). ``INCOMPATIBLE`` is fail-closed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from michi_ecosystem.domain.flashing import FirmwareManifest


class CompatibilityStatus(StrEnum):
    SUPPORTED = "supported"
    NOT_ENFORCED_UPSTREAM_OPEN = "not_enforced_upstream_open"
    INCOMPATIBLE = "incompatible"


@dataclass(frozen=True)
class CompatibilityFinding:
    field: str
    status: CompatibilityStatus
    detail: str = ""


@dataclass(frozen=True)
class FirmwareCompatibilityReport:
    findings: tuple[CompatibilityFinding, ...]

    @property
    def blocking(self) -> tuple[CompatibilityFinding, ...]:
        return tuple(
            finding
            for finding in self.findings
            if finding.status is CompatibilityStatus.INCOMPATIBLE
        )

    @property
    def supported(self) -> bool:
        return not self.blocking


def _parse_version(text: str) -> tuple[int, ...] | None:
    parts = text.strip().split(".")
    if not parts or not all(part.isdigit() for part in parts):
        return None
    return tuple(int(part) for part in parts)


def evaluate_compatibility(
    manifest: FirmwareManifest,
    *,
    ecosystem_version: str,
    supported_protocols: frozenset[str] = frozenset(),
) -> FirmwareCompatibilityReport:
    """Evaluate the unfinished upstream compatibility fields explicitly."""
    findings: list[CompatibilityFinding] = []

    minimum = manifest.minimum_ecosystem_version.strip()
    if not minimum:
        findings.append(
            CompatibilityFinding(
                "minimum_ecosystem_version",
                CompatibilityStatus.NOT_ENFORCED_UPSTREAM_OPEN,
                "el manifest no declara un mínimo de ecosistema (STREAM-REQ-008)",
            )
        )
    else:
        required = _parse_version(minimum)
        current = _parse_version(ecosystem_version)
        if required is None:
            findings.append(
                CompatibilityFinding(
                    "minimum_ecosystem_version",
                    CompatibilityStatus.INCOMPATIBLE,
                    f"mínimo declarado no parseable: {minimum!r}",
                )
            )
        elif current is None or current < required:
            findings.append(
                CompatibilityFinding(
                    "minimum_ecosystem_version",
                    CompatibilityStatus.INCOMPATIBLE,
                    f"requiere >= {minimum}, ecosistema {ecosystem_version}",
                )
            )
        else:
            findings.append(
                CompatibilityFinding(
                    "minimum_ecosystem_version",
                    CompatibilityStatus.SUPPORTED,
                    f"{ecosystem_version} >= {minimum}",
                )
            )

    protocols = tuple(manifest.protocol_compatibility)
    if not protocols:
        findings.append(
            CompatibilityFinding(
                "protocol_compatibility",
                CompatibilityStatus.NOT_ENFORCED_UPSTREAM_OPEN,
                "el manifest no declara protocolos (STREAM-REQ-008)",
            )
        )
    elif not supported_protocols:
        findings.append(
            CompatibilityFinding(
                "protocol_compatibility",
                CompatibilityStatus.NOT_ENFORCED_UPSTREAM_OPEN,
                "el host aún no define su set de protocolos (STREAM-REQ-008)",
            )
        )
    elif supported_protocols.intersection(protocols):
        findings.append(
            CompatibilityFinding(
                "protocol_compatibility",
                CompatibilityStatus.SUPPORTED,
                f"intersección con {sorted(supported_protocols)}",
            )
        )
    else:
        findings.append(
            CompatibilityFinding(
                "protocol_compatibility",
                CompatibilityStatus.INCOMPATIBLE,
                f"declara {sorted(protocols)}, host soporta "
                f"{sorted(supported_protocols)}",
            )
        )

    findings.append(
        CompatibilityFinding(
            "partition_table_digest",
            CompatibilityStatus.NOT_ENFORCED_UPSTREAM_OPEN,
            "sin contrato de tabla de particiones publicado (STREAM-REQ-008)",
        )
    )
    return FirmwareCompatibilityReport(tuple(findings))
