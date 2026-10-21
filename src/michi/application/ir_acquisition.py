"""AP2-F06 — bounded IR acquisition OUTSIDE the pure compiler.

The compiler is pure (no threads, no I/O). The composition acquires provider
data here, with a hard deadline, so a slow or hung IR provider can never hold
the preparation worker or prevent supersession/cancellation of the session.
Python cannot kill a blocked thread; the call runs in a DAEMON thread and the
caller fails typed at the deadline (the abandoned thread cannot keep the
process alive).
"""

from __future__ import annotations

import threading
from collections.abc import Callable, Iterable
from typing import Any

from michi.application.processing_graph_compiler import ProcessingCompilationError

DEFAULT_IR_TIMEOUT_S = 5.0


def bounded_ir_call(
    operation: Callable[[], Any],
    *,
    timeout_s: float = DEFAULT_IR_TIMEOUT_S,
    code: str = "DSP_FIR_STORE_TIMEOUT",
    detail: str = "the IR provider did not answer within the deadline",
) -> Any:
    timeout = float(timeout_s)
    if timeout <= 0:
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_TIMEOUT", "IR provider timeout must be positive"
        )
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = operation()
        except BaseException as exc:  # noqa: BLE001 - relayed to the caller
            box["error"] = exc

    worker = threading.Thread(target=run, name="michi-ir-acquire", daemon=True)
    worker.start()
    worker.join(timeout)
    if worker.is_alive():
        raise ProcessingCompilationError(code, detail)
    error = box.get("error")
    if error is not None:
        if isinstance(error, ProcessingCompilationError):
            raise error
        raise ProcessingCompilationError(
            str(getattr(error, "code", "DSP_FIR_STORE_FAILED")), str(error)
        ) from error
    return box.get("value")


def acquire_kernels(
    assets: Iterable[object],
    provider: object,
    *,
    timeout_s: float = DEFAULT_IR_TIMEOUT_S,
) -> dict[str, tuple[float, ...]]:
    """Bounded acquisition of every ConvolutionNode asset (immutable snapshot)."""
    kernels: dict[str, tuple[float, ...]] = {}
    for asset in assets:
        asset_id = str(asset.asset_id)
        coefficients = bounded_ir_call(
            lambda asset_id=asset_id: provider.load_float32_mono(asset_id),
            timeout_s=timeout_s,
            detail=f"asset {asset_id} was not delivered within {timeout_s}s",
        )
        kernels[asset_id] = tuple(coefficients)
    return kernels
