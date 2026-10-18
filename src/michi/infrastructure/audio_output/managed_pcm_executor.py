"""AP2-F06 — Managed PCM executor (specific DAC, processed family).

Stages ONE strict ALSA sink for the selected binding in the supervised
GStreamer host, loads the media, installs the compiled DSP through the
canonical processing authority (injected), then verifies the child-reported
runtime identity. It NEVER falls back to the default output and never tags a
managed execution as Direct.

Physical DAC verification remains a separate, evidence-gated tier.
"""

from __future__ import annotations

import contextlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from michi.domain.managed_pcm_output import MANAGED_PCM_PATH, ManagedPcmOutputPlan


class ManagedPcmExecutionError(RuntimeError):
    """Typed managed-execution failure (never a silent fallback)."""

    def __init__(self, code: str, detail: str) -> None:
        super().__init__(f"{code}: {detail}")
        self.code = code
        self.detail = detail


@dataclass(frozen=True, slots=True)
class ManagedPcmExecutionReceipt:
    execution_id: str
    plan_id: str
    stable_device_id: str
    device_locator: str
    terminal_format: str
    rate_hz: int
    channels: int
    processing_plan_id: str | None
    processing_revision: int
    runtime_identity: dict[str, Any]
    lab_sink: bool
    path: str = MANAGED_PCM_PATH


class ManagedPcmExecutor:
    """Executes a Managed plan against the canonical hosted GStreamer port."""

    def __init__(
        self,
        port_provider: Callable[[], object | None],
        *,
        install_processing: Callable[[ManagedPcmOutputPlan], object] | None = None,
    ) -> None:
        self._port_provider = port_provider
        self._install_processing = install_processing

    def execute(
        self,
        plan: ManagedPcmOutputPlan,
        media_path: str | Path,
        *,
        install_processing: (Callable[[ManagedPcmOutputPlan], object] | None) = None,
    ) -> ManagedPcmExecutionReceipt:
        port = self._port_provider()
        if port is None:
            raise ManagedPcmExecutionError(
                "MANAGED_PCM_TRANSPORT_UNAVAILABLE",
                "GStreamer is not the open active engine for Managed output",
            )
        recipe = {
            "plan_id": plan.plan_id,
            "sink_factory": "alsasink",
            "device": plan.device_locator,
            "media_type": "audio/x-raw",
            "gst_format": plan.terminal_format,
            "rate_hz": plan.output_rate_hz,
            "channels": plan.output_channels,
            "layout": "interleaved",
        }
        try:
            port.stage_managed_execution(recipe)
        except Exception as exc:  # noqa: BLE001 - typed boundary
            raise ManagedPcmExecutionError(
                "MANAGED_PCM_STAGE_FAILED", str(exc)
            ) from exc
        try:
            port.load(Path(media_path))
        except Exception as exc:  # noqa: BLE001 - no fallback, typed failure
            self._stop_quietly(port)
            raise ManagedPcmExecutionError("MANAGED_PCM_LOAD_FAILED", str(exc)) from exc

        identity = self._await_accepted(port)
        if identity is None:
            self._stop_quietly(port)
            raise ManagedPcmExecutionError(
                "MANAGED_PCM_IDENTITY_UNAVAILABLE",
                "the child reported no managed identity",
            )
        if identity.get("loaded") is not True:
            # The requested DAC was not accepted. NEVER fall back to the
            # default output: the route is stopped.
            self._stop_quietly(port)
            raise ManagedPcmExecutionError(
                "MANAGED_PCM_LOAD_FAILED",
                "the child did not accept the managed load (no fallback)",
            )

        processing_revision = 0
        installer = install_processing or self._install_processing
        if plan.processing_plan_id is not None:
            if installer is None:
                self._stop_quietly(port)
                raise ManagedPcmExecutionError(
                    "MANAGED_PCM_PROCESSING_UNAVAILABLE",
                    "no processing authority is composed for this route",
                )
            try:
                installed = installer(plan)
            except Exception as exc:  # noqa: BLE001 - fail closed
                self._stop_quietly(port)
                raise ManagedPcmExecutionError(
                    "MANAGED_PCM_PROCESSING_FAILED", str(exc)
                ) from exc
            processing_revision = int(
                getattr(installed, "processing_revision", 0)
                or (installed.get("revision", 0) if isinstance(installed, dict) else 0)
            )

        # D4: re-read the identity AFTER the DSP install; the evidence that
        # justifies the claim must describe the CURRENT topology.
        try:
            identity = port.query_managed_identity()
        except Exception:  # noqa: BLE001 - keep the pre-install identity
            identity = identity
        identity = dict(identity)
        host_generation = getattr(port, "supervisor_generation", None)
        if host_generation is not None:
            identity["host_generation"] = host_generation
        self._verify_identity(plan, identity, port)
        return ManagedPcmExecutionReceipt(
            execution_id=plan.execution_id,
            plan_id=plan.plan_id,
            stable_device_id=plan.stable_device_id,
            device_locator=plan.device_locator,
            terminal_format=plan.terminal_format,
            rate_hz=plan.output_rate_hz,
            channels=plan.output_channels,
            processing_plan_id=plan.processing_plan_id,
            processing_revision=processing_revision,
            runtime_identity=dict(identity),
            lab_sink=bool(identity.get("lab_sink", False)),
            path=MANAGED_PCM_PATH,
        )

    @staticmethod
    def _await_accepted(
        port: object, *, timeout_s: float = 10.0
    ) -> dict[str, Any] | None:
        """Bounded wait for the child to accept (or reject) the managed load.

        Load acceptance is asynchronous in the supervised host; the executor
        never returns a success claim before the child confirms it.
        """
        deadline = time.monotonic() + timeout_s
        last: dict[str, Any] | None = None
        while True:
            try:
                identity = port.query_managed_identity()
            except Exception:  # noqa: BLE001 - retried until the deadline
                identity = None
            if isinstance(identity, dict):
                last = identity
                if identity.get("loaded") is True:
                    return identity
            dispatch = getattr(port, "dispatch_pending", None)
            if callable(dispatch):
                with contextlib.suppress(Exception):
                    dispatch()
            if time.monotonic() >= deadline:
                return last
            time.sleep(0.02)

    def _verify_identity(
        self, plan: ManagedPcmOutputPlan, identity: dict[str, Any], port: object
    ) -> None:
        checks = {
            "managed": identity.get("managed") is True,
            "device": identity.get("device") == plan.device_locator,
            "format": identity.get("format") == plan.terminal_format,
            "rate_hz": int(identity.get("rate_hz") or 0) == plan.output_rate_hz,
            "channels": int(identity.get("channels") or 0) == plan.output_channels,
            "plan_id": identity.get("plan_id") == plan.plan_id,
        }
        if not all(checks.values()):
            self._stop_quietly(port)
            raise ManagedPcmExecutionError(
                "MANAGED_PCM_IDENTITY_MISMATCH",
                f"managed runtime identity differs from the plan: {checks}",
            )

    @staticmethod
    def _stop_quietly(port: object) -> None:
        stop = getattr(port, "stop", None)
        if callable(stop):
            try:
                stop()
            except Exception:  # noqa: BLE001 - teardown is best effort
                return
