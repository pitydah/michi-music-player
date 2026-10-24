"""AP2-F09 — process-supervised DoP ALSA carrier probe.

libasound calls are not cancellable from Python once entered. A child process
provides a real deadline: timeout terminates the probe process instead of
pretending a Future.cancel() stopped libasound.
"""

from __future__ import annotations

import dataclasses
import multiprocessing as mp
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from michi.infrastructure.audio_devices.alsa_dop_probe import (
    DopCarrierProbeEvidence,
    DopCarrierProbeRequest,
    probe_dop_carrier,
)

DEFAULT_PROBE_TIMEOUT_S = 3.0
DEFAULT_MAX_CONCURRENT_PROBES = 2
DEFAULT_QUEUE_LIMIT = 4


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
    cancel_event: threading.Event | None = None,
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
    import time

    deadline = time.monotonic() + float(timeout_s)
    try:
        while not parent.poll(0.02):
            if cancel_event is not None and cancel_event.is_set():
                process.terminate()
                process.join(1.0)
                if process.is_alive():
                    process.kill()
                    process.join(1.0)
                return DopProbeOutcome("CANCELLED", detail="probe cancelled")
            if time.monotonic() >= deadline:
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
            evidence = dataclasses.replace(message[1], provenance="ALSA_SUPERVISED")
            return DopProbeOutcome("OK", evidence=evidence)
        return DopProbeOutcome(
            "ERROR", detail=": ".join(str(item) for item in message[1:])
        )
    finally:
        parent.close()
        process.join(1.0)
        if process.is_alive():
            process.kill()
            process.join(1.0)


class DopProbeQueueFullError(RuntimeError):
    code = "DOP_PROBE_QUEUE_FULL"


@dataclass
class DopProbeFuture:
    """Non-blocking handle for one bounded supervised probe attempt."""

    request_id: str
    stable_device_id: str
    binding_generation: int
    deadline_monotonic: float
    status: str = (
        "PENDING"  # PENDING|RUNNING|COMPLETED|CANCELLED|TIMEOUT|ERROR|STALE_BINDING
    )
    _event: threading.Event = dataclasses.field(default_factory=threading.Event)
    _cancel: threading.Event = dataclasses.field(default_factory=threading.Event)
    _outcome: DopProbeOutcome | None = None

    def cancel(self) -> bool:
        if self.done():
            return False
        self._cancel.set()
        if self.status == "PENDING":
            self.status = "CANCELLED"
            self._outcome = DopProbeOutcome(
                "CANCELLED", detail="cancelled before start"
            )
            self._event.set()
        return True

    def done(self) -> bool:
        return self._event.is_set()

    def result(self, timeout: float | None = None) -> DopProbeOutcome:
        if not self._event.wait(timeout):
            raise TimeoutError("DoP probe result not ready")
        assert self._outcome is not None
        return self._outcome


class AsyncDopProbeService:
    """Bounded, non-blocking facade over the process-supervised ALSA probe.

    The owner thread only submits and polls futures; a worker thread owns the
    child process and its cancellation/deadline cleanup. Cancellation reaches
    the child, never a libasound call inside this process.
    """

    def __init__(
        self,
        *,
        max_concurrent: int = DEFAULT_MAX_CONCURRENT_PROBES,
        queue_limit: int = DEFAULT_QUEUE_LIMIT,
        process_context: str = "spawn",
    ) -> None:
        if max_concurrent < 1 or queue_limit < 0:
            raise ValueError("invalid probe concurrency limits")
        self._max_concurrent = max_concurrent
        self._slots = threading.BoundedSemaphore(max_concurrent)
        self._queue_slots = threading.BoundedSemaphore(max_concurrent + queue_limit)
        self._process_context = process_context
        self._lock = threading.Lock()
        self._jobs: dict[str, DopProbeFuture] = {}
        self._threads: dict[str, threading.Thread] = {}
        self._closed = False

    def submit(
        self,
        stable_device_id: str,
        binding_locator: str,
        binding_generation: int,
        request: DopCarrierProbeRequest,
        *,
        environment: str | None = None,
        timeout_s: float = DEFAULT_PROBE_TIMEOUT_S,
        probe_callable: Callable[..., Any] = probe_dop_carrier,
        binding_check: Callable[[str, str, int], bool] | None = None,
    ) -> DopProbeFuture:
        import time
        import uuid

        if timeout_s <= 0:
            raise ValueError("probe timeout must be positive")
        with self._lock:
            if self._closed:
                raise RuntimeError("probe service is closed")
        if not self._queue_slots.acquire(blocking=False):
            raise DopProbeQueueFullError(DopProbeQueueFullError.code)
        future = DopProbeFuture(
            request_id=str(uuid.uuid4()),
            stable_device_id=stable_device_id,
            binding_generation=binding_generation,
            deadline_monotonic=time.monotonic() + float(timeout_s),
        )
        with self._lock:
            self._jobs[future.request_id] = future
        thread = threading.Thread(
            target=self._run,
            args=(
                future,
                stable_device_id,
                binding_locator,
                binding_generation,
                request,
                environment,
                probe_callable,
                binding_check,
            ),
            name=f"michi-dop-probe-{future.request_id[:8]}",
            daemon=True,
        )
        with self._lock:
            self._threads[future.request_id] = thread
        thread.start()
        return future

    def _run(
        self,
        future,
        stable_device_id,
        binding_locator,
        binding_generation,
        request,
        environment,
        probe_callable,
        binding_check,
    ) -> None:
        import time

        try:
            if future._cancel.is_set():
                future.status = "CANCELLED"
                future._outcome = DopProbeOutcome(
                    "CANCELLED", detail="cancelled before start"
                )
                return
            if not self._slots.acquire(
                timeout=max(0.0, future.deadline_monotonic - time.monotonic())
            ):
                future.status = "TIMEOUT"
                future._outcome = DopProbeOutcome(
                    "TIMEOUT", detail="probe queue deadline exceeded"
                )
                return
            try:
                if future._cancel.is_set():
                    future.status = "CANCELLED"
                    future._outcome = DopProbeOutcome(
                        "CANCELLED", detail="cancelled before start"
                    )
                    return
                future.status = "RUNNING"
                remaining = max(0.001, future.deadline_monotonic - time.monotonic())
                outcome = probe_dop_carrier_supervised(
                    stable_device_id,
                    binding_locator,
                    binding_generation,
                    request,
                    environment=environment,
                    timeout_s=remaining,
                    probe_callable=probe_callable,
                    process_context=self._process_context,
                    cancel_event=future._cancel,
                )
                if outcome.status != "OK":
                    future.status = outcome.status
                    future._outcome = outcome
                    return
                if binding_check is not None and not binding_check(
                    stable_device_id, binding_locator, binding_generation
                ):
                    future.status = "STALE_BINDING"
                    future._outcome = DopProbeOutcome(
                        "STALE_BINDING", detail="binding changed during probe"
                    )
                    return
                future.status = "COMPLETED"
                future._outcome = outcome
            finally:
                self._slots.release()
        except BaseException as exc:  # noqa: BLE001 - worker boundary
            future.status = "ERROR"
            future._outcome = DopProbeOutcome(
                "ERROR", detail=f"{type(exc).__name__}: {exc}"
            )
        finally:
            self._queue_slots.release()
            future._event.set()
            with self._lock:
                self._jobs.pop(future.request_id, None)
                self._threads.pop(future.request_id, None)

    def cancel(self, request_id: str) -> bool:
        with self._lock:
            future = self._jobs.get(request_id)
        return bool(future and future.cancel())

    def shutdown(self, timeout: float = 2.0) -> None:
        import time

        with self._lock:
            self._closed = True
            futures = list(self._jobs.values())
            threads = list(self._threads.values())
        for future in futures:
            future.cancel()
        deadline = time.monotonic() + timeout
        for thread in threads:
            thread.join(max(0.0, deadline - time.monotonic()))

    @property
    def active_count(self) -> int:
        with self._lock:
            return len(self._jobs)
