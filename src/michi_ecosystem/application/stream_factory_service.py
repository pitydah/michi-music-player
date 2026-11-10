"""Stream Factory application service (E5+hardening): approval-gated flashing.

Authority model (fail closed):

- ``build_plan`` produces a harmless ``FlashPlanDraft``;
- ``preflight`` reports findings for diagnostics;
- ``approve`` re-runs preflight and returns an ``ApprovedFlashPlan`` bound to
  the device fingerprint, manifest digest and provisioning fingerprint;
- ``execute`` accepts ONLY an ``ApprovedFlashPlan`` and re-validates every
  binding before touching the board (any drift → APPROVAL_INVALIDATED).

Blocking work is synchronous and off-GUI by caller contract. ``VERIFYING_FLASH``
performs a real read-back digest comparison; READY is never reached without a
post-flash verifier (added with the post-flash pipeline).
"""

from __future__ import annotations

import hashlib
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from michi_ecosystem.application.approval_registry import (
    ApprovalError,
    ApprovalRegistry,
)
from michi_ecosystem.domain.flashing import (
    SEGMENT_STAGE_ORDER,
    ApprovedFlashPlan,
    CreationMode,
    FlashPlanDraft,
    FlashSegment,
    FlashStage,
    ProvisioningRequest,
    profile_for,
    stage_for_segment,
    stage_sequence,
)
from michi_ecosystem.infrastructure.flashing.esptool_environment import (
    EsptoolEnvironment,
    EsptoolEnvironmentError,
    probe_esptool,
    require_supported_esptool,
)
from michi_ecosystem.infrastructure.flashing.flash_preflight import (
    PortLeaseRegistry,
    PreflightReport,
    run_preflight,
)
from michi_ecosystem.infrastructure.flashing.manifest_verifier import (
    ManifestError,
    verify_artifact,
)
from michi_ecosystem.infrastructure.flashing.provisioning_blob import (
    ProvisioningError,
    build_provisioning_blob,
)
from michi_ecosystem.ports.firmware_catalog import FirmwareCatalogPort
from michi_ecosystem.ports.flash_backend import (
    FlashBackendError,
    FlashBackendPort,
    FlashResetError,
    FlashVerificationError,
)
from michi_ecosystem.ports.installation_detector import (
    InstallationDetectorPort,
    InstallationEvidence,
    InstallationReport,
)
from michi_ecosystem.ports.serial_devices import SerialDevicesPort


def _now_ms() -> int:
    return time.time_ns() // 1_000_000


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


class FactoryError(RuntimeError):
    """Plan/validation level failure (build/approve level)."""

    def __init__(
        self,
        code: str,
        message: str,
        report: PreflightReport | None = None,
    ) -> None:
        self.code = code
        self.report = report
        super().__init__(f"{code}: {message}")


class InstallationChangedError(RuntimeError):
    """The board state changed between approval and the erase boundary."""


class DeviceChangedError(RuntimeError):
    """A different physical board is on the port at the destructive boundary."""


@dataclass(frozen=True)
class FlashOutcome:
    ok: bool
    stages: tuple[FlashStage, ...]
    port: str
    error: str | None = None
    error_code: str = ""
    reached_ready: bool = False


class StreamFactoryService:
    def __init__(
        self,
        *,
        serial: SerialDevicesPort,
        catalog: FirmwareCatalogPort,
        backend: FlashBackendPort,
        installation_detector: InstallationDetectorPort,
        leases: PortLeaseRegistry | None = None,
        approvals: ApprovalRegistry | None = None,
        clock: Callable[[], int] | None = None,
        tooling_check: Callable[[], EsptoolEnvironment] | None = probe_esptool,
    ) -> None:
        self._serial = serial
        self._catalog = catalog
        self._backend = backend
        self._installation_detector = installation_detector
        self._leases = leases or PortLeaseRegistry()
        self._approvals = approvals or ApprovalRegistry()
        self._clock = clock or _now_ms
        self._tooling_check = tooling_check

    @property
    def leases(self) -> PortLeaseRegistry:
        return self._leases

    def detect_devices(self):
        return self._serial.scan()

    # ── planning and approval ───────────────────────────────────────────

    def build_plan(
        self,
        *,
        mode: str | CreationMode,
        port: str,
        board: str,
        reference: str,
        provisioning: ProvisioningRequest | None = None,
        factory_recreate_confirmed: bool = False,
    ) -> FlashPlanDraft:
        try:
            parsed_mode = CreationMode(mode)
        except ValueError as exc:
            raise FactoryError("INVALID_MODE", str(exc)) from exc

        try:
            manifest = self._catalog.load(reference)
        except (KeyError, ManifestError) as exc:
            raise FactoryError("ARTIFACT_ERROR", str(exc)) from exc

        if parsed_mode is CreationMode.UPDATE_EXISTING and provisioning is not None:
            raise FactoryError(
                "UPDATE_PROVISIONING_FORBIDDEN",
                "Actualizar nunca reconfigura la red ni escribe factory_cfg.",
            )

        blob = None
        if provisioning is not None:
            try:
                blob = build_provisioning_blob(provisioning)
            except ProvisioningError as exc:
                raise FactoryError("PROVISIONING_ERROR", str(exc)) from exc
            descriptor = manifest.factory_partition
            if descriptor is not None and len(blob) > descriptor.capacity:
                raise FactoryError(
                    "FACTORY_BLOB_TOO_LARGE",
                    f"el provisioning ({len(blob)} B) excede la partición "
                    f"factory ({descriptor.capacity} B)",
                )

        return FlashPlanDraft(
            mode=parsed_mode,
            port=port,
            board=board,
            manifest=manifest,
            artifacts_dir=str(Path(manifest.source).parent),
            erase_first=parsed_mode is not CreationMode.UPDATE_EXISTING,
            factory_recreate_confirmed=factory_recreate_confirmed,
            provisioning_blob=blob,
        )

    def preflight(
        self,
        draft: FlashPlanDraft,
        *,
        provisioning: ProvisioningRequest | None = None,
        disk_free_bytes: int | None = None,
    ) -> PreflightReport:
        candidate = next(
            (item for item in self._serial.scan() if item.port == draft.port),
            None,
        )
        identity = None
        chip: str | None = None
        if candidate is not None and not candidate.access_denied:
            identity = self._backend.read_device_identity(draft.port)
            chip = (
                identity.chip_target
                if identity is not None
                else self._backend.probe_chip(draft.port)
            )

        installation: InstallationReport | None = None
        if (
            draft.mode in {CreationMode.CREATE_NEW, CreationMode.UPDATE_EXISTING}
            and candidate is not None
            and not candidate.access_denied
            and chip is not None
        ):
            installation = self._installation_detector.inspect(draft.port)

        return run_preflight(
            draft,
            candidate=candidate,
            chip=chip,
            artifacts_dir=Path(draft.artifacts_dir),
            leases=self._leases,
            provisioning=provisioning,
            disk_free_bytes=disk_free_bytes,
            installation=installation,
            physical_identity=identity,
        )

    def approve(
        self,
        draft: FlashPlanDraft,
        *,
        provisioning: ProvisioningRequest | None = None,
        disk_free_bytes: int | None = None,
    ) -> ApprovedFlashPlan:
        """Preflight gate: blocking findings or drift make approval impossible."""
        if self._tooling_check is not None:
            try:
                require_supported_esptool(self._tooling_check())
            except EsptoolEnvironmentError as exc:
                raise FactoryError(exc.code, exc.message) from exc

        report = self.preflight(
            draft, provisioning=provisioning, disk_free_bytes=disk_free_bytes
        )
        if report.blocking:
            raise FactoryError("PREFLIGHT_BLOCKED", report.blocking[0].message, report)

        candidate = next(
            (item for item in self._serial.scan() if item.port == draft.port),
            None,
        )
        identity = None
        if candidate is not None and not candidate.access_denied:
            identity = self._backend.read_device_identity(draft.port)
        if identity is None:
            raise FactoryError(
                "PREFLIGHT_BLOCKED",
                "No se pudo leer la identidad física estable de la placa.",
                report,
            )
        manifest_digest = _sha256(Path(draft.manifest.source).read_bytes())
        provisioning_fingerprint = (
            _sha256(draft.provisioning_blob)
            if draft.provisioning_blob is not None
            else ""
        )
        approved = ApprovedFlashPlan(
            plan=draft,
            approval_id=uuid.uuid4().hex,
            manifest_digest=manifest_digest,
            device_fingerprint=identity.fingerprint(),
            provisioning_fingerprint=provisioning_fingerprint,
            approved_at_ms=self._clock(),
            finding_codes=tuple(finding.code for finding in report.findings),
        )
        self._approvals.register(approved)
        return approved

    # ── execution ───────────────────────────────────────────────────────

    def execute(
        self,
        approved: ApprovedFlashPlan,
        *,
        progress: Callable[[FlashStage], None] | None = None,
        will_start: Callable[[FlashStage], None] | None = None,
    ) -> FlashOutcome:
        if not isinstance(approved, ApprovedFlashPlan):
            raise TypeError(
                "execute() requires an ApprovedFlashPlan produced by approve()"
            )

        draft = approved.plan
        stages_done: list[FlashStage] = []

        def fail(code: str, message: str) -> FlashOutcome:
            stages_done.append(FlashStage.FAILED)
            return FlashOutcome(
                ok=False,
                stages=tuple(stages_done),
                port=draft.port,
                error=message,
                error_code=code,
            )

        # Re-validate every approval binding before touching the board.
        candidate = next(
            (item for item in self._serial.scan() if item.port == draft.port),
            None,
        )
        if candidate is None or candidate.access_denied:
            return fail(
                "APPROVAL_INVALIDATED",
                "El puerto cambió desde la aprobación. Vuelve a preparar el flasheo.",
            )
        identity = self._backend.read_device_identity(draft.port)
        if identity is None or identity.fingerprint() != approved.device_fingerprint:
            return fail(
                "APPROVAL_INVALIDATED",
                "La placa cambió desde la aprobación. Vuelve a preparar el flasheo.",
            )
        try:
            manifest_digest = _sha256(Path(draft.manifest.source).read_bytes())
        except OSError:
            return fail(
                "APPROVAL_INVALIDATED",
                "El firmware aprobado ya no está disponible. Vuelve a preparar.",
            )
        if manifest_digest != approved.manifest_digest:
            return fail(
                "APPROVAL_INVALIDATED",
                "El firmware cambió desde la aprobación. Vuelve a preparar.",
            )
        if draft.provisioning_blob is not None and (
            _sha256(draft.provisioning_blob) != approved.provisioning_fingerprint
        ):
            return fail(
                "APPROVAL_INVALIDATED",
                "Los datos de Wi-Fi cambiaron desde la aprobación.",
            )

        operation_id = uuid.uuid4().hex
        if not self._leases.acquire(draft.port, operation_id):
            return fail("LEASE_HELD", "Ya hay un flasheo en curso en este puerto.")
        try:
            # Single-use: consume atomically before ANY destructive action.
            self._approvals.consume(approved)
        except ApprovalError as exc:
            self._leases.release(draft.port, operation_id)
            return fail(exc.code, exc.message)

        factory_name = (
            draft.manifest.factory_partition.name
            if draft.provisioning_blob is not None
            and draft.manifest.factory_partition is not None
            else None
        )
        profile = profile_for(draft.manifest, draft.mode)
        written_segments = [
            segment
            for segment in draft.manifest.segments
            if segment.name != factory_name and profile.allows(segment.name)
        ]
        segment_map: dict[FlashStage, list[FlashSegment]] = {
            stage: [] for stage in SEGMENT_STAGE_ORDER
        }
        for segment in sorted(written_segments, key=lambda s: s.offset):
            segment_map[stage_for_segment(segment.name)].append(segment)

        sequence = stage_sequence(
            erase_first=draft.erase_first,
            segment_names=tuple(segment.name for segment in written_segments),
            include_provisioning=draft.provisioning_blob is not None,
        )

        writes_done: list[tuple[int, bytes]] = []
        try:
            for stage in sequence:
                if will_start is not None:
                    # BEFORE the action: observers may abort here (e.g. a
                    # cancellation request must be honored before erase/write).
                    will_start(stage)
                if stage is FlashStage.VERIFYING_FIRMWARE:
                    for segment in written_segments:
                        try:
                            verify_artifact(
                                draft.manifest,
                                segment,
                                Path(draft.artifacts_dir),
                            )
                        except ManifestError as exc:
                            raise FlashBackendError(str(exc)) from exc
                elif stage is FlashStage.PREPARING_FLASH:
                    self._prepare(segment_map)
                elif stage is FlashStage.ERASING:
                    self._assert_destructive_boundary(
                        approved,
                        require_blank=draft.mode is CreationMode.CREATE_NEW,
                    )
                    self._backend.erase_flash(draft.port)
                elif stage in SEGMENT_STAGE_ORDER:
                    for segment in segment_map[stage]:
                        # Operation-wide continuity: the SAME physical board
                        # must be present before every destructive write.
                        self._guard_identity(approved)
                        payload = (
                            Path(draft.artifacts_dir) / segment.file
                        ).read_bytes()
                        self._backend.write_segment(draft.port, segment.offset, payload)
                        writes_done.append((segment.offset, payload))
                elif stage is FlashStage.FLASHING_PROVISIONING:
                    blob = draft.provisioning_blob
                    if blob is not None:
                        self._guard_identity(approved)
                        descriptor = draft.manifest.factory_partition
                        if descriptor is None:
                            raise FlashBackendError(
                                "manifest lacks the factory partition descriptor"
                            )
                        self._backend.write_segment(draft.port, descriptor.offset, blob)
                        writes_done.append((descriptor.offset, blob))
                elif stage is FlashStage.VERIFYING_FLASH:
                    if writes_done:
                        self._guard_identity(approved)
                    for offset, payload in writes_done:
                        verified = self._backend.verify_segment(
                            draft.port,
                            offset,
                            len(payload),
                            _sha256(payload),
                        )
                        if not verified:
                            raise FlashVerificationError(
                                f"La verificación de escritura falló en {hex(offset)}."
                            )
                elif stage is FlashStage.REBOOTING:
                    self._guard_identity(approved)
                    self._backend.hard_reset(draft.port)

                stages_done.append(stage)
                if progress is not None:
                    progress(stage)

            # No post-flash verifier yet: the board is flashed and verified on
            # the wire, but READY is NOT claimed (requires discovery/identity).
            return FlashOutcome(
                ok=True,
                stages=tuple(stages_done),
                port=draft.port,
                error=None,
                error_code="",
                reached_ready=False,
            )
        except FlashVerificationError as exc:
            return fail("FLASH_VERIFY_MISMATCH", str(exc))
        except DeviceChangedError as exc:
            return fail("APPROVAL_INVALIDATED_DEVICE", str(exc))
        except InstallationChangedError as exc:
            return fail("INSTALLATION_CHANGED", str(exc))
        except FlashResetError as exc:
            return fail("RESET_FAILED", str(exc))
        except FlashBackendError as exc:
            return fail("FLASH_BACKEND_ERROR", str(exc))
        finally:
            self._leases.release(draft.port, operation_id)

    def _guard_identity(self, approved: ApprovedFlashPlan) -> None:
        """The same physical board must be present for every destructive op.

        Called immediately before each write/verify/reset; residual hardware
        TOCTOU between the identity read and the following command cannot be
        eliminated by the host (documented in the factory docs).
        """
        draft = approved.plan
        identity = self._backend.read_device_identity(draft.port)
        if identity is None or identity.fingerprint() != approved.device_fingerprint:
            raise DeviceChangedError(
                "La placa cambió durante la operación. No se continuó escribiendo."
            )

    def _assert_destructive_boundary(
        self, approved: ApprovedFlashPlan, *, require_blank: bool
    ) -> None:
        """Minimize TOCTOU at the destructive boundary.

        Sequence for CREATE_NEW: identity check → installation inspection →
        identity check again → erase immediately. Residual hardware races
        between the final read and the erase command cannot be eliminated by
        the host and are documented in the factory docs.
        """
        draft = approved.plan
        identity = self._backend.read_device_identity(draft.port)
        if identity is None or identity.fingerprint() != approved.device_fingerprint:
            raise DeviceChangedError(
                "La placa cambió justo antes de la operación destructiva. "
                "No se tocó nada."
            )
        if require_blank:
            evidence = self._installation_detector.inspect(draft.port)
            if evidence.evidence is not InstallationEvidence.BLANK:
                raise InstallationChangedError(
                    "La placa cambió desde la aprobación "
                    f"({evidence.evidence}). No se borró nada."
                )
            identity_again = self._backend.read_device_identity(draft.port)
            if (
                identity_again is None
                or identity_again.fingerprint() != approved.device_fingerprint
            ):
                raise DeviceChangedError(
                    "La placa cambió durante la inspección previa al borrado. "
                    "No se tocó nada."
                )

    def _prepare(self, segment_map: dict[FlashStage, list[FlashSegment]]) -> None:
        """Bookkeeping gate: every segment to write must carry its size."""
        for segments in segment_map.values():
            for segment in segments:
                if segment.size is None:
                    raise FlashBackendError(
                        f"segment {segment.name} has no size; cannot verify"
                    )
