"""Flash preflight checks PF-001..PF-009 (master plan §139).

Blocking findings disable the Create button; destructive workflows require
explicit confirmation; one lease per port. Blocking findings fail closed.
"""

from __future__ import annotations

import threading
from dataclasses import dataclass
from pathlib import Path

from michi_ecosystem.domain.flashing import (
    CreationMode,
    FlashPlanDraft,
    PhysicalDeviceIdentity,
    ProvisioningRequest,
)
from michi_ecosystem.infrastructure.flashing.manifest_verifier import (
    ManifestError,
    verify_artifact,
    verify_layout,
    verify_manifest_for_board,
)
from michi_ecosystem.infrastructure.flashing.provisioning_blob import (
    SCHEMA_VERSION,
    SUPPORTED_FACTORY_FORMAT,
    ProvisioningError,
    parse_provisioning_blob,
)
from michi_ecosystem.ports.installation_detector import (
    InstallationEvidence,
    InstallationReport,
)
from michi_ecosystem.ports.serial_devices import SerialCandidate

REQUIRED_CHIP = "esp32s3"


@dataclass(frozen=True)
class PreflightFinding:
    code: str
    severity: str  # "blocking" | "warning"
    message: str


@dataclass(frozen=True)
class PreflightReport:
    findings: tuple[PreflightFinding, ...] = ()

    @property
    def blocking(self) -> tuple[PreflightFinding, ...]:
        return tuple(
            finding for finding in self.findings if finding.severity == "blocking"
        )

    @property
    def ok(self) -> bool:
        return not self.blocking


class PortLeaseRegistry:
    """Thread-safe, operation-scoped port lease (master plan §140.2).

    One exclusive owner per port — no reentrancy: a second acquisition (even
    from the same service) fails until the owner releases. Owners are unique
    operation ids, never service-instance ids.
    """

    def __init__(self) -> None:
        self._holders: dict[str, str] = {}
        self._lock = threading.Lock()

    def acquire(self, port: str, operation_id: str) -> bool:
        with self._lock:
            if port in self._holders:
                return False
            self._holders[port] = operation_id
            return True

    def release(self, port: str, operation_id: str) -> None:
        with self._lock:
            if self._holders.get(port) == operation_id:
                del self._holders[port]

    def holder(self, port: str) -> str | None:
        with self._lock:
            return self._holders.get(port)


def run_preflight(
    plan: FlashPlanDraft,
    *,
    candidate: SerialCandidate | None,
    chip: str | None,
    artifacts_dir: Path,
    leases: PortLeaseRegistry,
    provisioning: ProvisioningRequest | None = None,
    disk_free_bytes: int | None = None,
    installation: InstallationReport | None = None,
    physical_identity: PhysicalDeviceIdentity | None = None,
) -> PreflightReport:
    findings: list[PreflightFinding] = []

    # PF-001 — port presence and permissions.
    if candidate is None:
        findings.append(
            PreflightFinding(
                "PF-001", "blocking", "No hay una placa conectada en ese puerto."
            )
        )
    elif candidate.access_denied:
        findings.append(
            PreflightFinding(
                "PF-001",
                "blocking",
                "Michi detectó la placa, pero no tiene permiso para usar el "
                "puerto USB.",
            )
        )

    # PF-002 — chip probe (must be an ESP32-S3).
    if candidate is not None and not candidate.access_denied:
        if chip is None:
            findings.append(
                PreflightFinding(
                    "PF-002",
                    "blocking",
                    "No se pudo identificar el chip. Revisa el cable y reintenta.",
                )
            )
        elif chip != REQUIRED_CHIP:
            findings.append(
                PreflightFinding(
                    "PF-002",
                    "blocking",
                    f"El chip detectado ({chip}) no es un ESP32-S3.",
                )
            )

    # PF-003 — board profile compatibility.
    try:
        verify_manifest_for_board(plan.manifest, plan.board)
    except ManifestError as exc:
        findings.append(
            PreflightFinding(
                "PF-003", "blocking", f"El firmware no corresponde a la placa: {exc}"
            )
        )

    # PF-004 — manifest layout coherence (never guessed offsets).
    try:
        verify_layout(plan.manifest)
    except ManifestError as exc:
        findings.append(
            PreflightFinding(
                "PF-004", "blocking", f"El manifiesto de firmware es incoherente: {exc}"
            )
        )

    # PF-005 — artifacts present and hashed.
    for segment in plan.manifest.segments:
        try:
            verify_artifact(plan.manifest, segment, artifacts_dir)
        except ManifestError as exc:
            findings.append(PreflightFinding("PF-005", "blocking", str(exc)))
            break

    # PF-006 — provisioning coherence and factory partition support.
    if plan.provisioning_blob is not None:
        descriptor = plan.manifest.factory_partition
        if descriptor is None:
            findings.append(
                PreflightFinding(
                    "PF-006",
                    "blocking",
                    "Este firmware todavía no acepta la precarga de Wi-Fi "
                    "(falta la partición factory; ver E6 / STREAM-REQ-002).",
                )
            )
        else:
            if descriptor.format != SUPPORTED_FACTORY_FORMAT:
                findings.append(
                    PreflightFinding(
                        "PF-006",
                        "blocking",
                        f"Formato de partición factory no soportado: "
                        f"{descriptor.format!r}.",
                    )
                )
            if descriptor.schema_version != SCHEMA_VERSION:
                findings.append(
                    PreflightFinding(
                        "PF-006",
                        "blocking",
                        f"Schema de partición factory no soportado: "
                        f"{descriptor.schema_version}.",
                    )
                )
            if len(plan.provisioning_blob) > descriptor.capacity:
                findings.append(
                    PreflightFinding(
                        "PF-006",
                        "blocking",
                        "FACTORY_BLOB_TOO_LARGE: el provisioning excede la "
                        "capacidad de la partición factory.",
                    )
                )
        if provisioning is None:
            findings.append(
                PreflightFinding("PF-006", "blocking", "Faltan los datos de Wi-Fi.")
            )
        else:
            try:
                stored = parse_provisioning_blob(plan.provisioning_blob)
                current = (
                    provisioning.ssid,
                    provisioning.password,
                    provisioning.region,
                    provisioning.device_name,
                )
                planned = (
                    stored.ssid,
                    stored.password,
                    stored.region,
                    stored.device_name,
                )
                if current != planned:
                    findings.append(
                        PreflightFinding(
                            "PF-006",
                            "warning",
                            "Los datos de Wi-Fi cambiaron desde que se armó el plan.",
                        )
                    )
            except ProvisioningError as exc:
                findings.append(
                    PreflightFinding(
                        "PF-006", "blocking", f"Los datos de Wi-Fi son inválidos: {exc}"
                    )
                )

    # PF-007 — destructive workflows and update safety.
    if (
        plan.mode is CreationMode.FACTORY_RECREATE
        and not plan.factory_recreate_confirmed
    ):
        findings.append(
            PreflightFinding(
                "PF-007",
                "blocking",
                "Factory Recreate necesita una confirmación explícita.",
            )
        )
    if plan.mode is CreationMode.UPDATE_EXISTING and plan.erase_first:
        findings.append(
            PreflightFinding(
                "PF-007",
                "blocking",
                "Una actualización nunca debe borrar la identidad del dispositivo.",
            )
        )

    # PF-008 — port lease exclusivity.
    if leases.holder(plan.port) is not None:
        findings.append(
            PreflightFinding(
                "PF-008", "blocking", "Ya hay un flasheo en curso en este puerto."
            )
        )

    # PF-009 — storage headroom for artifact staging.
    if disk_free_bytes is not None:
        required = sum(segment.size or 0 for segment in plan.manifest.segments)
        if disk_free_bytes < required * 2 + 64 * 1024 * 1024:
            findings.append(
                PreflightFinding(
                    "PF-009",
                    "blocking",
                    "No hay espacio suficiente en disco para preparar el flasheo.",
                )
            )

    # PF-010 — every written segment must declare its size: VERIFYING_FLASH
    # reads the flash back and compares digests, which is impossible without it.
    if any(segment.size is None for segment in plan.manifest.segments):
        findings.append(
            PreflightFinding(
                "PF-010",
                "blocking",
                "El manifiesto no declara el tamaño de todos los segmentos; "
                "no se puede verificar la escritura (fail closed).",
            )
        )

    # PF-013 — UPDATE_EXISTING only applies to a recognized installation;
    # a blank or unknown board must never become a half-configured Stream.
    if plan.mode is CreationMode.UPDATE_EXISTING:
        if installation is None or (
            installation.evidence is not InstallationEvidence.INSTALLED
        ):
            findings.append(
                PreflightFinding(
                    "PF-013",
                    "blocking",
                    "UPDATE_NOT_APPLICABLE: Actualizar requiere una instalación "
                    "Michi reconocible en la placa.",
                )
            )
        elif installation.product_evidence != "michi-stream":
            findings.append(
                PreflightFinding(
                    "PF-013",
                    "blocking",
                    "UPDATE_NOT_APPLICABLE: no se puede confirmar que la placa "
                    "sea un Music Stream compatible (STREAM-REQ-005).",
                )
            )
        if plan.manifest.update_segment_names is None:
            findings.append(
                PreflightFinding(
                    "PF-014",
                    "blocking",
                    "UPDATE_POLICY_MISSING: el firmware no declara segmentos "
                    "seguros para actualizar (ver STREAM-REQ-006). Fail closed.",
                )
            )

    # PF-011 — CREATE_NEW must never erase an existing installation. Without
    # reliable evidence the operation is blocked (fail closed).
    if plan.mode is CreationMode.CREATE_NEW:
        if installation is None:
            findings.append(
                PreflightFinding(
                    "PF-011",
                    "blocking",
                    "No se pudo verificar si la placa ya tiene una instalación. "
                    "Por seguridad, Crear nuevo está bloqueado: usa Actualizar, "
                    "Recuperar o Factory Recreate.",
                )
            )
        elif installation.evidence is InstallationEvidence.INSTALLED:
            findings.append(
                PreflightFinding(
                    "PF-011",
                    "blocking",
                    "Esta placa ya tiene una instalación Michi. Usa Actualizar "
                    "para conservarla, o Factory Recreate si quieres empezar de cero.",
                )
            )
        elif installation.evidence is InstallationEvidence.UNKNOWN:
            findings.append(
                PreflightFinding(
                    "PF-011",
                    "blocking",
                    "No se pudo determinar el estado de la placa "
                    "(fail closed). Vuelve a intentar o usa Factory Recreate "
                    "de forma explícita.",
                )
            )

    # PF-012 — destructive operations require a stable physical identity;
    # without it an approval cannot be bound to a specific board.
    if (
        candidate is not None
        and not candidate.access_denied
        and chip is not None
        and physical_identity is None
    ):
        findings.append(
            PreflightFinding(
                "PF-012",
                "blocking",
                "No se pudo leer la identidad física estable de la placa "
                "(fail closed).",
            )
        )

    return PreflightReport(tuple(findings))
