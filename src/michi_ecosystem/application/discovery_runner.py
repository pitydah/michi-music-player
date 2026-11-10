"""Bounded discovery runner: verification never runs on the Qt thread.

The host (Player) must not poll multicast sockets or verify signatures from
the GUI thread. This runner owns a single worker thread with a bounded
interval; every poll is serialized so manual refreshes cannot race the worker.
The registry snapshot callback is invoked from that worker and is already
thread-safe in DeviceRegistryService (atomic batch + queued GUI refresh).
"""

from __future__ import annotations

import threading
from collections.abc import Callable

from michi_ecosystem.application.device_registry_service import (
    DeviceRegistryService,
)
from michi_ecosystem.application.discovery_service import DiscoveryService

DEFAULT_INTERVAL_SECONDS = 0.25
DEFAULT_STOP_TIMEOUT_SECONDS = 5.0


class DiscoveryRunner:
    """Lifecycle + health for the background discovery loop."""

    def __init__(
        self,
        discovery: DiscoveryService,
        *,
        registry: DeviceRegistryService | None = None,
        interval_seconds: float = DEFAULT_INTERVAL_SECONDS,
    ) -> None:
        self._discovery = discovery
        self._registry = registry
        self._interval = max(0.05, float(interval_seconds))
        self._stop = threading.Event()
        self._poll_lock = threading.Lock()
        self._lock = threading.Lock()
        self._thread: threading.Thread | None = None
        self._polls = 0
        self._datagrams = 0
        self._errors = 0
        self._last_error = ""

    # ── lifecycle ───────────────────────────────────────────────────────

    def start(self) -> bool:
        """Start the worker; returns False when it was already running."""
        with self._lock:
            if self._thread is not None and self._thread.is_alive():
                return False
            self._stop.clear()
            self._thread = threading.Thread(
                target=self._run,
                name="michi-ecosystem-discovery",
                daemon=True,
            )
            self._thread.start()
            return True

    def stop(self, *, timeout: float = DEFAULT_STOP_TIMEOUT_SECONDS) -> bool:
        """Stop the worker; returns True when the thread finished."""
        with self._lock:
            thread = self._thread
            self._stop.set()
        if thread is None:
            return True
        thread.join(timeout)
        finished = not thread.is_alive()
        with self._lock:
            if finished:
                self._thread = None
        return finished

    @property
    def running(self) -> bool:
        with self._lock:
            return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        while not self._stop.wait(self._interval):
            try:
                with self._poll_lock:
                    count = self._discovery.poll()
            except Exception as exc:  # network stack fault: keep the runner alive
                with self._lock:
                    self._errors += 1
                    # Normalized code only: exception text may carry addresses.
                    self._last_error = type(exc).__name__
                continue
            with self._lock:
                self._polls += 1
                self._datagrams += int(count)

    def refresh(self) -> int:
        """Poll once from the caller thread (serialized with the worker)."""
        with self._poll_lock:
            count = int(self._discovery.poll())
        with self._lock:
            self._polls += 1
            self._datagrams += count
        return count

    # ── host seam ───────────────────────────────────────────────────────

    def subscribe(
        self, listener: Callable[[tuple[object, ...]], None]
    ) -> Callable[[], None]:
        """Subscribe to atomic registry snapshots; returns an unsubscribe callable."""
        if self._registry is None:
            return lambda: None
        return self._registry.subscribe(listener)

    @staticmethod
    def unsubscribe(unsubscribe: Callable[[], None] | None) -> None:
        if callable(unsubscribe):
            unsubscribe()

    def health(self) -> dict[str, object]:
        with self._lock:
            running = self._thread is not None and self._thread.is_alive()
            polls, datagrams = self._polls, self._datagrams
            errors, last_error = self._errors, self._last_error
        # Serialize with the worker: ui_state() reads the node map.
        try:
            with self._poll_lock:
                state = self._discovery.ui_state()
        except Exception:
            state = "unknown"
        return {
            "running": running,
            "state": state,
            "polls": polls,
            "datagrams": datagrams,
            "errors": errors,
            "lastError": last_error,
        }
