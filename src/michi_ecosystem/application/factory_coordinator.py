"""Factory operation coordinator (A5/A6/A7).

The FULL pipeline (plan → preflight → approve → flash → verify → reset) runs
on a worker thread; the caller thread only starts, requests cancellation and
receives events. Cancellation policy is explicit:

- before the destructive phase: SAFE_CANCELLED (no hardware touched);
- once erase/write began: CANNOT_CANCEL_DURING_FLASH (esptool is never killed
  mid-write; the operation finishes).

Progress is honest: the flash pipeline exposes stage/phase but no fabricated
percentage; ``determinate`` is False until a real metric exists.
"""

from __future__ import annotations

import threading
import uuid
from collections.abc import Callable
from dataclasses import dataclass, replace
from enum import StrEnum

from michi_ecosystem.application.stream_factory_service import (
    FactoryError,
    StreamFactoryService,
)
from michi_ecosystem.domain.flashing import (
    CreationMode,
    FlashStage,
    ProvisioningRequest,
)
from michi_ecosystem.domain.lifecycle import (
    FlashStatus,
    HomeStatus,
    NetworkStatus,
)


class OperationCancelledError(RuntimeError):
    """Cancellation honored BEFORE the destructive boundary (no hardware)."""


class OperationPhase(StrEnum):
    IDLE = "idle"
    REQUESTED = "requested"
    PREPARING_HOME = "preparing_home"
    RESOLVING = "resolving"
    RESOLVING_FIRMWARE = "resolving_firmware"
    DOWNLOADING_FIRMWARE = "downloading_firmware"
    VERIFYING_FIRMWARE = "verifying_firmware"
    PREFLIGHT = "preflight"
    APPROVING = "approving"
    READY_TO_FLASH = "ready_to_flash"
    DESTRUCTIVE = "destructive"
    VERIFYING = "verifying"
    REBOOTING = "rebooting"
    FLASH_READY = "flash_ready"
    CANCELLED = "cancelled"
    FAILED = "failed"


_DESTRUCTIVE_PHASES = frozenset(
    {
        OperationPhase.DESTRUCTIVE,
        OperationPhase.VERIFYING,
        OperationPhase.REBOOTING,
    }
)

_DESTRUCTIVE_STAGES = frozenset(
    {
        FlashStage.ERASING,
        FlashStage.FLASHING_BOOT,
        FlashStage.FLASHING_PARTITION_TABLE,
        FlashStage.FLASHING_OTA_DATA,
        FlashStage.FLASHING_APP,
        FlashStage.FLASHING_PROVISIONING,
    }
)


@dataclass(frozen=True)
class FactoryRequest:
    mode: CreationMode
    port: str
    board: str
    reference: str = ""
    provisioning: ProvisioningRequest | None = None
    factory_recreate_confirmed: bool = False
    selection: str = "dev_local"
    channel: str = "stable"


@dataclass(frozen=True)
class FactoryEvent:
    operation_id: str
    phase: OperationPhase
    stage: FlashStage | None = None
    determinate: bool = False
    fraction: float | None = None


@dataclass(frozen=True)
class FactoryResult:
    operation_id: str
    ok: bool
    cancelled: bool
    reached_ready: bool = False
    error: str = ""
    error_code: str = ""
    # Post-flash lifecycle, honest and separated (M16): flash / network /
    # home are different claims and never collapse into one bool.
    flash_status: str = ""
    network_status: str = ""
    home_status: str = ""
    recreate_tx_id: str = ""
    recreate_status: str = ""


@dataclass(frozen=True)
class FactoryPipelineHooks:
    """Optional pipeline extensions (C0.3/C0.8): all callables run on the
    coordinator WORKER thread — never on the GUI thread.

    - ``prepare``: Home preparation (crypto/membership/sqlite) before the
      firmware phase; returns an opaque token (or None).
    - ``destructive_started``: called BEFORE the first destructive hardware
      action (e.g. mark the recreate transaction FLASHING).
    - ``settle``: maps (token, result) -> result, producing honest post-flash
      Home statuses and aborting/committing Home state.
    """

    prepare: Callable[[], object | None] | None = None
    destructive_started: Callable[[], None] | None = None
    settle: Callable[[object | None, FactoryResult], FactoryResult] | None = None


class FactoryOperationCoordinator:
    def __init__(
        self,
        service: StreamFactoryService,
        *,
        on_event: Callable[[FactoryEvent], None],
        on_finished: Callable[[FactoryResult], None],
        acquisition=None,
        developer_mode: bool = False,
        thread_factory: Callable[[Callable[[], None]], threading.Thread] | None = None,
    ) -> None:
        self._service = service
        self._on_event = on_event
        self._on_finished = on_finished
        self._acquisition = acquisition
        self._developer_mode = developer_mode
        self._thread_factory = thread_factory or (
            lambda target: threading.Thread(target=target, daemon=True)
        )
        self._lock = threading.Lock()
        self._hooks = FactoryPipelineHooks()
        self._cancel = threading.Event()
        self._phase = OperationPhase.IDLE
        self._operation_id: str | None = None
        self._thread: threading.Thread | None = None
        self._destructive_started = False

    @property
    def phase(self) -> OperationPhase:
        with self._lock:
            return self._phase

    @property
    def operation_id(self) -> str | None:
        return self._operation_id

    def busy(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(
        self,
        request: FactoryRequest,
        *,
        hooks: FactoryPipelineHooks | None = None,
    ) -> str:
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                raise FactoryError("OPERATION_BUSY", "ya hay una operación en curso")
            self._hooks = hooks or FactoryPipelineHooks()
            self._cancel.clear()
            self._destructive_started = False  # fresh operation state (A1)
            self._operation_id = uuid.uuid4().hex
            operation_id = self._operation_id
            self._phase = OperationPhase.REQUESTED
            self._thread = self._thread_factory(
                lambda: self._run(operation_id, request)
            )
        self._emit(OperationPhase.REQUESTED)
        self._thread.start()
        return operation_id

    def request_cancel(self) -> str:
        with self._lock:
            busy = self._thread is not None and self._thread.is_alive()
            phase = self._phase
        if not busy:
            return "IDLE"
        if phase in _DESTRUCTIVE_PHASES:
            return "CANNOT_CANCEL_DURING_FLASH"
        self._cancel.set()
        return "SAFE_CANCELLED"

    # ── worker ──────────────────────────────────────────────────────────

    def _run(self, operation_id: str, request: FactoryRequest) -> None:
        prepared: object | None = None
        hooks = self._hooks
        try:
            if self._cancel.is_set():
                return self._finish(operation_id, cancelled=True, prepared=prepared)

            if hooks.prepare is not None:
                # Home preparation runs HERE, on the worker thread (C0.3):
                # crypto, membership issuance and sqlite never block the GUI.
                self._set_phase(OperationPhase.PREPARING_HOME)
                prepared = hooks.prepare()
                if self._cancel.is_set():
                    return self._finish(operation_id, cancelled=True, prepared=prepared)

            reference = request.reference
            if request.selection == "official_recommended":
                self._set_phase(OperationPhase.RESOLVING_FIRMWARE)
                if self._acquisition is None:
                    raise FactoryError(
                        "OFFICIAL_FIRMWARE_UNAVAILABLE",
                        "No hay firmware oficial disponible todavía.",
                    )
                try:
                    acquired = self._acquisition.acquire_recommended(
                        request.board,
                        request.channel,
                        progress=self._download_progress,
                    )
                except Exception as exc:  # FirmwareAcquisitionError-alike
                    code = getattr(exc, "code", "ACQUISITION_FAILED")
                    message = getattr(exc, "message", str(exc))
                    raise FactoryError(code, message) from exc
                self._set_phase(OperationPhase.VERIFYING_FIRMWARE)
                reference = acquired.reference
            elif request.selection == "dev_local" and not self._developer_mode:
                raise FactoryError(
                    "DEV_MODE_REQUIRED",
                    "el firmware local requiere modo desarrollador explícito",
                )

            self._set_phase(OperationPhase.RESOLVING)
            draft = self._service.build_plan(
                mode=request.mode,
                port=request.port,
                board=request.board,
                reference=reference,
                provisioning=request.provisioning,
                factory_recreate_confirmed=request.factory_recreate_confirmed,
            )
            if self._cancel.is_set():
                return self._finish(operation_id, cancelled=True, prepared=prepared)

            self._set_phase(OperationPhase.PREFLIGHT)
            self._set_phase(OperationPhase.APPROVING)
            approved = self._service.approve(draft, provisioning=request.provisioning)
            if self._cancel.is_set():
                return self._finish(operation_id, cancelled=True, prepared=prepared)

            self._set_phase(OperationPhase.READY_TO_FLASH)

            def will_start(stage: FlashStage) -> None:
                # BEFORE the hardware action: destructive phase entered
                # pre-action and cancellation honored exactly once, right
                # before the first destructive operation.
                if stage not in _DESTRUCTIVE_STAGES:
                    return
                if not self._destructive_started:
                    if self._cancel.is_set():
                        raise OperationCancelledError()
                    if hooks.destructive_started is not None:
                        hooks.destructive_started()
                    self._destructive_started = True
                    self._set_phase(OperationPhase.DESTRUCTIVE, stage)

            def progress(stage: FlashStage) -> None:
                if stage is FlashStage.VERIFYING_FLASH:
                    self._set_phase(OperationPhase.VERIFYING, stage)
                elif stage is FlashStage.REBOOTING:
                    self._set_phase(OperationPhase.REBOOTING, stage)
                elif stage not in _DESTRUCTIVE_STAGES:
                    self._set_phase(self.phase, stage)

            outcome = self._service.execute(
                approved, progress=progress, will_start=will_start
            )
            if outcome.ok:
                self._set_phase(OperationPhase.FLASH_READY)
                self._deliver(
                    prepared,
                    FactoryResult(
                        operation_id=operation_id,
                        ok=True,
                        cancelled=False,
                        reached_ready=outcome.reached_ready,
                        flash_status=FlashStatus.FLASH_READY.value,
                        network_status=NetworkStatus.WAITING_FOR_DEVICE.value,
                        home_status=HomeStatus.VERIFICATION_PENDING.value,
                    ),
                )
            else:
                self._set_phase(OperationPhase.FAILED)
                self._deliver(
                    prepared,
                    FactoryResult(
                        operation_id=operation_id,
                        ok=False,
                        cancelled=False,
                        error=outcome.error or "El flasheo falló.",
                        error_code=outcome.error_code,
                        flash_status=FlashStatus.FLASH_FAILED.value,
                    ),
                )
        except OperationCancelledError:
            return self._finish(operation_id, cancelled=True, prepared=prepared)
        except FactoryError as exc:
            self._set_phase(OperationPhase.FAILED)
            self._deliver(
                prepared,
                FactoryResult(
                    operation_id=operation_id,
                    ok=False,
                    cancelled=False,
                    error=getattr(exc, "message", "") or str(exc),
                    error_code=exc.code,
                ),
            )
        except Exception as exc:  # A2: never die leaving busy=True
            # Typed orchestrator errors surface their code/message (internal,
            # secret-free); unknown exceptions stay sanitized (type only).
            code = str(getattr(exc, "code", "") or "INTERNAL_FACTORY_ERROR")
            if code != "INTERNAL_FACTORY_ERROR":
                message = str(getattr(exc, "message", "") or str(exc))
            else:
                message = f"Error interno de la fábrica ({type(exc).__name__})."
            self._set_phase(OperationPhase.FAILED)
            self._deliver(
                prepared,
                FactoryResult(
                    operation_id=operation_id,
                    ok=False,
                    cancelled=False,
                    error=message,
                    error_code=code,
                ),
            )

    # ── internals ───────────────────────────────────────────────────────

    def _set_phase(
        self, phase: OperationPhase, stage: FlashStage | None = None
    ) -> None:
        with self._lock:
            self._phase = phase
        self._emit(phase, stage)

    def _download_progress(self, received: int, total: int | None) -> None:
        # Honest determinate progress ONLY for real byte downloads (E4).
        fraction = min(received / total, 1.0) if total else None
        self._on_event(
            FactoryEvent(
                operation_id=self._operation_id or "",
                phase=OperationPhase.DOWNLOADING_FIRMWARE,
                stage=None,
                determinate=total is not None,
                fraction=fraction,
            )
        )

    def _emit(self, phase: OperationPhase, stage: FlashStage | None = None) -> None:
        self._on_event(
            FactoryEvent(
                operation_id=self._operation_id or "",
                phase=phase,
                stage=stage,
                determinate=False,
                fraction=None,
            )
        )

    def _finish(
        self, operation_id: str, *, cancelled: bool, prepared: object | None = None
    ) -> None:
        self._set_phase(
            OperationPhase.CANCELLED if cancelled else OperationPhase.FAILED
        )
        self._deliver(
            prepared,
            FactoryResult(
                operation_id=operation_id,
                ok=False,
                cancelled=cancelled,
                error_code="CANCELLED" if cancelled else "",
            ),
        )

    def _deliver(self, prepared: object | None, result: FactoryResult) -> None:
        """Settlement never swallows the finish signal (A2)."""
        if self._hooks.settle is not None:
            try:
                result = self._hooks.settle(prepared, result)
            except Exception:
                result = replace(result, home_status=HomeStatus.SETTLEMENT_FAILED.value)
        self._on_finished(result)
