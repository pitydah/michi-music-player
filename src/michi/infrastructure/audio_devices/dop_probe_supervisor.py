"""AP2-F09 — process-supervised DoP ALSA carrier probe.

libasound calls are not cancellable from Python once entered. A child process
provides a real deadline: timeout terminates the probe process instead of
pretending a Future.cancel() stopped libasound.
"""

from __future__ import annotations

import multiprocessing as mp
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
    DopCarrierProbeRequest,
    probe_dop_carrier,
)

DEFAULT_PROBE_TIMEOUT_S = 3.0


@dataclass(frozen=True, slots=True)
class DopProbeOutcome:
    status: str  # OK | TIMEOUT | ERROR | CANCELLED
    evidence: DopCarrierProbeEvidence | None = None
    detail: str = ""


def _worker(connection, probe_callable, args, kwargs) -> None:
    try:
        connection.send(("ok", probe_callable(*args, **kwargs)))
    except BaseException as exc:  # noqa: BLE001 - child boundary
        connection.send(("error", type(exc).__name__, str(exc)))
    finally:
        connection.close()


def probe_dop_carrier_supervised(
    stable_device_id: str,
    binding_locator: str,
    binding_generation: int,
    request: DopCarrierProbeRequest,
    *,
    environment: str | None = None,
    timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
    probe_callable: Callable[..., Any] = probe_dop_carrier,
    process_context: str = "spawn",
) -> DopProbeOutcome:
    if timeout_s <= 0:
        raise ValueError("probe timeout must be positive")
    context = mp.get_context(process_context)
    parent, child = context.Pipe(duplex=False)
    process = context.Process(
        target=_worker,
        args=(
            child,
            probe_callable,
            (stable_device_id, binding_locator, binding_generation, request),
            {"environment": environment},
        ),
        daemon=True,
    )
    process.start()
    child.close()
    try:
        if not parent.poll(float(timeout_s)):
            process.terminate()
            process.join(1.0)
            if process.is_alive():
                process.kill()
                process.join(1.0)
            return DopProbeOutcome("TIMEOUT", detail="probe deadline exceeded")
        try:
            message = parent.recv()
        except EOFError as exc:
            return DopProbeOutcome(
                "ERROR", detail=f"worker exited without result: {exc}"
            )
        if not message:
            return DopProbeOutcome("ERROR", detail="empty worker result")
        if message[0] == "ok" and isinstance(message[1], DopCarrierProbeEvidence):
            return DopProbeOutcome("OK", evidence=message[1])
        return DopProbeOutcome(
            "ERROR", detail=": ".join(str(item) for item in message[1:])
        )
    finally:
        parent.close()
        process.join(1.0)
        if process.is_alive():
            process.kill()
            process.join(1.0)
