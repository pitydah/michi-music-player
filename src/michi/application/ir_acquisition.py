"""AP2-F06 — bounded IR acquisition OUTSIDE the pure compiler.

The compiler is pure (no threads, no I/O). The composition acquires provider
data here, with a hard deadline AND a bounded materialization budget:

* the provider call AND the iteration of its result run inside a daemon thread,
  so a slow/infinite iterator cannot hold the preparation worker;
* coefficient consumption is capped at ``MAX_FIR_TAPS`` BEFORE anything is
  copied or hashed, so an infinite generator or a lying ``__len__`` cannot
  materialize an unbounded tuple;
* every acquisition has a whole-operation budget (not only per call);
* the number of in-flight acquisition threads is capped: a permanently hung
  provider cannot accumulate unbounded abandoned threads across retries.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Iterable, Mapping
from typing import Any

from michi.application.processing_graph_compiler import ProcessingCompilationError
from michi.domain.audio_processing import ImpulseResponseMetadata
from michi.domain.fir_kernel import MAX_FIR_TAPS

DEFAULT_IR_TIMEOUT_S = 5.0
# A hung provider keeps its daemon thread alive until it returns; future
# acquisitions are refused typed instead of accumulating threads forever.
MAX_IN_FLIGHT = 4

_in_flight = 0
_in_flight_lock = threading.Lock()


def in_flight_calls() -> int:
    with _in_flight_lock:
        return _in_flight


def _reserve_slot() -> None:
    global _in_flight
    with _in_flight_lock:
        if _in_flight >= MAX_IN_FLIGHT:
            raise ProcessingCompilationError(
                "DSP_FIR_STORE_BUSY",
                f"{_in_flight} IR acquisitions are still blocked; refusing another",
            )
        _in_flight += 1


def _release_slot() -> None:
    global _in_flight
    with _in_flight_lock:
        _in_flight = max(0, _in_flight - 1)


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
    _reserve_slot()
    box: dict[str, Any] = {}

    def run() -> None:
        try:
            box["value"] = operation()
        except BaseException as exc:  # noqa: BLE001 - relayed to the caller
            box["error"] = exc
        finally:
            _release_slot()

    worker = threading.Thread(target=run, name="michi-ir-acquire", daemon=True)
    try:
        worker.start()
    except BaseException:
        _release_slot()
        raise
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


def _materialize_coefficients(value: Any, *, max_taps: int = MAX_FIR_TAPS) -> tuple:
    """Bounded consumption: never convert an open-ended iterable to tuple()."""
    if value is None or isinstance(value, (str, bytes, bytearray, dict)):
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_INVALID", "the IR provider returned a non-kernel value"
        )
    try:
        iterator = iter(value)
    except TypeError as exc:
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_INVALID", "the IR provider returned a non-iterable"
        ) from exc
    out: list[float] = []
    try:
        for item in iterator:
            if len(out) >= max_taps:
                raise ProcessingCompilationError(
                    "FIR_KERNEL_TOO_LARGE",
                    f"IR exceeds the authorized {max_taps}-tap budget",
                )
            try:
                out.append(float(item))
            except (TypeError, ValueError) as exc:
                raise ProcessingCompilationError(
                    "DSP_FIR_STORE_INVALID", "IR coefficients must be finite numbers"
                ) from exc
    except ProcessingCompilationError:
        raise
    except BaseException as exc:
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_INVALID", f"IR iteration failed: {exc}"
        ) from exc
    if not out:
        raise ProcessingCompilationError("FIR_KERNEL_EMPTY", "IR has no taps")
    return tuple(out)


def acquire_kernels(
    assets: Iterable[object],
    provider: object,
    *,
    timeout_s: float = DEFAULT_IR_TIMEOUT_S,
    total_timeout_s: float = DEFAULT_IR_TIMEOUT_S,
) -> dict[str, tuple[float, ...]]:
    """Bounded acquisition of every ConvolutionNode asset (immutable snapshot).

    The provider call and the bounded iteration of its result share ONE
    deadline inside the daemon thread; the whole acquisition shares a second,
    total budget across all assets.
    """
    total = float(total_timeout_s)
    if total <= 0:
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_TIMEOUT", "IR acquisition budget must be positive"
        )
    deadline = time.monotonic() + total
    kernels: dict[str, tuple[float, ...]] = {}
    for asset in assets:
        asset_id = str(asset.asset_id)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProcessingCompilationError(
                "DSP_FIR_STORE_TIMEOUT",
                f"IR acquisition budget exhausted before asset {asset_id}",
            )
        coefficients = bounded_ir_call(
            lambda asset_id=asset_id: _materialize_coefficients(
                provider.load_float32_mono(asset_id)
            ),
            timeout_s=min(float(timeout_s), remaining),
            detail=f"asset {asset_id} was not delivered within the budget",
        )
        kernels[asset_id] = coefficients
    return kernels


def _parse_metadata(asset_id: str, metadata: Any) -> ImpulseResponseMetadata:
    """Validate provider-declared identity inside the bounded operation."""
    if not isinstance(metadata, Mapping):
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_INVALID", "the IR provider returned no metadata mapping"
        )
    sha = str(metadata.get("sha256") or "").strip().lower()
    if len(sha) != 64 or any(ch not in "0123456789abcdef" for ch in sha):
        raise ProcessingCompilationError(
            "DSP_FIR_ASSET_HASH_UNAVAILABLE",
            "the IR provider must declare the asset SHA-256",
        )
    rate_hz = metadata.get("rate_hz")
    channels = metadata.get("channels")
    for name, value in (("rate_hz", rate_hz), ("channels", channels)):
        if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
            raise ProcessingCompilationError(
                "DSP_FIR_STORE_INVALID",
                f"IR metadata {name} must be a positive integer",
            )
    return ImpulseResponseMetadata(
        asset_id=asset_id,
        sha256=sha,
        rate_hz=rate_hz,
        channels=channels,
    )


def acquire_ir_assets(
    nodes: Iterable[object],
    provider: object,
    *,
    timeout_s: float = DEFAULT_IR_TIMEOUT_S,
    total_timeout_s: float = DEFAULT_IR_TIMEOUT_S,
) -> tuple[tuple[ImpulseResponseMetadata, ...], dict[str, tuple[float, ...]]]:
    """Metadata + coefficients under ONE shared deadline.

    A provider that is slow in metadata and/or coefficients cannot multiply
    the preparation budget by the number of FIR nodes.
    """
    total = float(total_timeout_s)
    if total <= 0:
        raise ProcessingCompilationError(
            "DSP_FIR_STORE_TIMEOUT", "IR acquisition budget must be positive"
        )
    deadline = time.monotonic() + total
    assets: list[ImpulseResponseMetadata] = []
    kernels: dict[str, tuple[float, ...]] = {}
    for node in nodes:
        asset_id = str(node.asset_id)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProcessingCompilationError(
                "DSP_FIR_STORE_TIMEOUT",
                f"IR acquisition budget exhausted before asset {asset_id}",
            )
        asset = bounded_ir_call(
            lambda asset_id=asset_id: _parse_metadata(
                asset_id, provider.metadata(asset_id)
            ),
            timeout_s=min(float(timeout_s), remaining),
            detail=f"metadata for asset {asset_id} exceeded the acquisition budget",
        )
        assets.append(asset)
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise ProcessingCompilationError(
                "DSP_FIR_STORE_TIMEOUT",
                f"IR acquisition budget exhausted before coefficients of {asset_id}",
            )
        kernels[asset_id] = bounded_ir_call(
            lambda asset_id=asset_id: _materialize_coefficients(
                provider.load_float32_mono(asset_id)
            ),
            timeout_s=min(float(timeout_s), remaining),
            detail=f"coefficients for asset {asset_id} exceeded the acquisition budget",
        )
    return tuple(assets), kernels
