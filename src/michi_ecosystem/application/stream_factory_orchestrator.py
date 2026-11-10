"""Unified Stream Factory orchestrator (C1).

ONE application entry point for factory operations; the bridge only commands.

Composes (never duplicates): firmware acquisition and the flash pipeline stay
in ``FactoryOperationCoordinator``; Home enrollment in ``HomeEnrollmentService``;
replacement transactions in ``FactoryRecreateService``.

Lifecycle (worker thread — nothing blocking runs on the GUI thread):

    REQUESTED -> PREPARING_HOME -> RESOLVING_FIRMWARE -> ... -> settlement

Modes:
- CREATE_NEW: candidate enrollment before the destructive phase; success keeps
  HOME_ENROLLMENT_PENDING_DEVICE_CONFIRMATION (never auto-activates).
- UPDATE_EXISTING: Home is never touched (no enrollment, no identity, no
  provisioning reach the pipeline).
- FACTORY_RECREATE: candidate enrollment + write-ahead recreate transaction;
  fails closed if the recreate machinery or the old device selection is
  missing.
"""

from __future__ import annotations

import contextlib
from dataclasses import dataclass

from michi_ecosystem.application.factory_coordinator import (
    FactoryOperationCoordinator,
    FactoryPipelineHooks,
    FactoryRequest,
    FactoryResult,
)
from michi_ecosystem.application.factory_recreate import (
    FactoryRecreateService,
    RecreateError,
)
from michi_ecosystem.application.home_enrollment import HomeEnrollmentService
from michi_ecosystem.application.stream_factory_service import FactoryError
from michi_ecosystem.domain.flashing import CreationMode
from michi_ecosystem.domain.home import DeviceRole, DomainError
from michi_ecosystem.domain.lifecycle import HomeStatus
from michi_ecosystem.infrastructure.home.recreate_transaction import RecreateState
from michi_ecosystem.ports.device_identity import CandidateDeviceIdentity


@dataclass(frozen=True)
class PreparedProvisioning:
    identity: CandidateDeviceIdentity
    membership_serial: str
    recreate_tx_id: str = ""
    # Concrete services resolved for THIS operation (P0: dynamic Home): the
    # settle phase must use the same instances even if the context changed.
    enrollment: object | None = None
    recreate: object | None = None


class StreamFactoryOrchestrator:
    def __init__(
        self,
        *,
        coordinator: FactoryOperationCoordinator,
        enrollment: HomeEnrollmentService | None = None,
        home_provider=None,
        recreate: FactoryRecreateService | None = None,
        old_device_provider=None,
        home_access_provider=None,
        home_lease_provider=None,
        allow_partial_home_bootstrap: bool = False,
    ) -> None:
        self._coordinator = coordinator
        self._enrollment = enrollment
        self._home_provider = home_provider
        self._recreate = recreate
        self._old_device_provider = old_device_provider
        # Locked-Home authority barrier (per operation): None = legacy/tests.
        self._home_access_provider = home_access_provider
        # Context lease (per operation): the manager must not close the
        # context this operation is still using (§13).
        self._home_lease_provider = home_lease_provider
        # I2 (P0): MICHI-F1 v1 carries only Wi-Fi data. A Home-aware factory
        # operation would create a PENDING membership that can never be proven
        # by the device. Product operations fail closed; only an explicit
        # developer/lab mode may run the partial v1 flow (never ACTIVE).
        self._allow_partial_home_bootstrap = bool(allow_partial_home_bootstrap)

    def start(self, request: FactoryRequest) -> str:
        holder: dict[str, PreparedProvisioning | None] = {"prepared": None}

        def prepare() -> object | None:
            if self._home_lease_provider is not None:
                scope = _resolve(self._home_lease_provider)
                holder["lease"] = scope
                scope.__enter__()
            prepared = self._prepare(request)
            holder["prepared"] = prepared
            return prepared

        def destructive_started() -> None:
            prepared = holder["prepared"]
            if (
                isinstance(prepared, PreparedProvisioning)
                and prepared.recreate_tx_id
                and prepared.recreate is not None
            ):
                prepared.recreate.mark_flashing(prepared.recreate_tx_id)

        def settle(prepared: object | None, result: FactoryResult) -> FactoryResult:
            try:
                return self._settle(prepared, result)
            finally:
                # Single release point: every finish path reaches settle,
                # including failures raised during prepare (§13).
                lease = holder.pop("lease", None)
                if lease is not None:
                    lease.__exit__(None, None, None)
                holder["prepared"] = None

        return self._coordinator.start(
            request,
            hooks=FactoryPipelineHooks(
                prepare=prepare,
                destructive_started=destructive_started,
                settle=settle,
            ),
        )

    # ── preparation (worker thread) ─────────────────────────────────────

    def _prepare(self, request: FactoryRequest) -> PreparedProvisioning | None:
        # P0 dynamic Home: providers are resolved PER OPERATION so a Home
        # created/restored mid-session is used without rebuilding the runtime.
        enrollment = _resolve(self._enrollment)
        recreate = _resolve(self._recreate)

        if request.mode is CreationMode.UPDATE_EXISTING:
            # Update is firmware-only: Wi-Fi/identity/Home/membership preserved.
            return None

        if request.mode is CreationMode.FACTORY_RECREATE and (
            recreate is None or self._old_device_provider is None
        ):
            raise FactoryError(
                "FACTORY_RECREATE_UNAVAILABLE",
                "El reemplazo de fábrica no está disponible en este entorno.",
            )

        if enrollment is None or self._home_provider is None:
            return None
        home = _resolve(self._home_provider)
        if home is None:
            if request.mode is CreationMode.FACTORY_RECREATE:
                raise FactoryError(
                    "FACTORY_RECREATE_REQUIRES_HOME",
                    "El reemplazo de fábrica requiere un Michi Home desbloqueado.",
                )
            return None

        if self._home_access_provider is not None and not _resolve(
            self._home_access_provider
        ):
            # Locked Home: fail closed BEFORE any enrollment/tx side effect.
            raise FactoryError(
                "HOME_LOCKED",
                "El Home está bloqueado; desbloquealo para continuar.",
            )

        if not self._allow_partial_home_bootstrap:
            raise FactoryError(
                "HOME_BOOTSTRAP_TRANSPORT_UNAVAILABLE",
                "MICHI-F1 v1 no transporta identidad ni membresía. "
                "Se requiere un bootstrap Home-aware autenticado "
                "(STREAM-REQ-007) antes de crear o recrear un Music Stream "
                "con Michi Home.",
            )
        device_name = (
            request.provisioning.device_name if request.provisioning else ""
        ) or "Music Stream"
        identity, membership = enrollment.begin(
            home=home,
            device_name=device_name,
            roles=(DeviceRole.AUDIO_RECEIVER,),
        )
        if request.mode is not CreationMode.FACTORY_RECREATE:
            return PreparedProvisioning(
                identity=identity,
                membership_serial=membership.serial.value,
                enrollment=enrollment,
            )

        old_device_id = self._old_device_provider()
        if not old_device_id:
            enrollment.abort(identity)
            raise FactoryError(
                "RECREATE_OLD_DEVICE_REQUIRED",
                "Selecciona el dispositivo a reemplazar antes de continuar.",
            )
        try:
            tx_id = recreate.begin(
                old_device_id=old_device_id,
                candidate_michi_id=identity.michi_id,
                candidate_serial=membership.serial.value,
            )
        except RecreateError as exc:
            enrollment.abort(identity)
            raise FactoryError(exc.code, exc.message) from exc
        return PreparedProvisioning(
            identity=identity,
            membership_serial=membership.serial.value,
            recreate_tx_id=tx_id,
            enrollment=enrollment,
            recreate=recreate,
        )

    # ── settlement (worker thread) ──────────────────────────────────────

    def _settle(self, prepared: object | None, result: FactoryResult) -> FactoryResult:
        if not isinstance(prepared, PreparedProvisioning):
            return result
        recreate = prepared.recreate or _resolve(self._recreate)
        enrollment = prepared.enrollment or _resolve(self._enrollment)

        if result.ok:
            recreate_status = ""
            if prepared.recreate_tx_id and recreate is not None:
                recreate.record_flash_success(prepared.recreate_tx_id)
                recreate_status = RecreateState.FLASH_VERIFIED.value
            # Device confirmation is still outstanding: never claim VERIFIED.
            return _with(
                result,
                home_status=HomeStatus.DEVICE_CONFIRMATION_PENDING.value,
                recreate_tx_id=prepared.recreate_tx_id,
                recreate_status=recreate_status,
            )

        recreate_status = ""
        if prepared.recreate_tx_id and recreate is not None:
            try:
                recreate.abort(prepared.recreate_tx_id, "factory operation failed")
                recreate_status = RecreateState.ABORTED.value
            except RecreateError:
                recreate_status = "abort_failed"
        # Roster already resolved is fine; never mask the factory result.
        if enrollment is not None:
            with contextlib.suppress(DomainError):
                enrollment.abort(prepared.identity)
        return _with(
            result,
            home_status=HomeStatus.ABORTED.value,
            recreate_tx_id=prepared.recreate_tx_id,
            recreate_status=recreate_status,
        )


def _resolve(value):
    """Instances or zero-arg providers (P0 dynamic Home lifecycle)."""
    return value() if callable(value) else value


def _with(
    result: FactoryResult,
    *,
    home_status: str,
    recreate_tx_id: str = "",
    recreate_status: str = "",
) -> FactoryResult:
    from dataclasses import replace

    return replace(
        result,
        home_status=home_status,
        recreate_tx_id=recreate_tx_id,
        recreate_status=recreate_status,
    )
