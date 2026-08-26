"""Async scan runner (M6.4 + M6-PRODUCTION-INTEGRATION) — Qt-based dispatch.

The heavy scan work runs on a plain worker thread; progress/done reach the
owner (GUI) thread through the Qt signal relay (queued connections to the
owner-thread LibraryScanDispatcher). The application service stays Qt-free —
only this infrastructure adapter touches Qt.

Production corrections (M6-PRODUCTION-INTEGRATION-AND-ASYNC-CORRECTION):
- ONE cancellation token PER GENERATION: a cancelled scan can never poison
  a later scan (a fresh token is created for every submit and retired when
  the worker finishes);
- ``cancel(generation)`` targets exactly that generation's token (unknown
  generations are safe no-ops);
- ``shutdown()`` rejects new submissions and cancels every active
  generation; the dispatcher drops the late relay emissions.
"""

import threading

from PySide6.QtCore import QObject, Signal

from michi.application.ports import (
    ScanCancelled,
    ScanCancelToken,
    ScanPipelinePort,
    ScanProgress,
    ScanProgressSnapshot,
)


class ScanRelay(QObject):
    """Thread-safe bridge for worker -> owner-thread dispatch."""

    done = Signal(int, object, object)  # generation, ScanResult|None, error|None
    progress = Signal(int, object)  # generation, ScanProgress


class ThreadScanRunner(ScanPipelinePort):
    """One worker thread per submit; ONE token per generation.

    The service-side callbacks (``on_progress``/``on_done``) are the port
    contract for deterministic test fakes; the production runner dispatches
    through the relay instead (bootstrap connects the relay signals to the
    owner-thread dispatcher), so they are intentionally unused here.
    """

    def __init__(self, relay: ScanRelay) -> None:
        self._relay = relay
        self._tokens: dict[int, ScanCancelToken] = {}
        self._closed = False
        self._lock = threading.Lock()

    def submit(self, generation, work, on_progress, on_done) -> None:
        # A FRESH token per generation: cancelling one scan must never
        # poison the next one.
        with self._lock:
            if self._closed:
                return  # shutdown: reject new submissions
            token = ScanCancelToken()
            self._tokens[generation] = token

        def run() -> None:
            progress = ScanProgress()

            def report() -> None:
                # M6-FINAL-CROSS-PERSISTENCE-GATE: the thread boundary
                # transports an IMMUTABLE snapshot, never the mutable
                # worker-owned builder — the owner thread can never observe
                # a mutating object.
                self._relay.progress.emit(
                    generation, ScanProgressSnapshot.from_progress(progress)
                )

            try:
                result = work(progress, token, report)
            except ScanCancelled:
                self._relay.done.emit(generation, None, ScanCancelled())
                return
            except Exception as exc:  # typed scan errors propagate as-is
                self._relay.done.emit(generation, None, exc)
                return
            finally:
                with self._lock:
                    self._tokens.pop(generation, None)
            self._relay.done.emit(generation, result, None)

        threading.Thread(target=run, daemon=True).start()

    def cancel(self, generation: int) -> None:
        """Cancel exactly ONE generation's token (unknown: safe no-op)."""
        with self._lock:
            token = self._tokens.get(generation)
        if token is not None:
            token.cancelled = True  # cooperative: the worker checks in between

    def disconnect_relay(self) -> None:
        """KCR-010: disconnect production relay signals during owner
        teardown (public API — bootstrap never touches the private relay)."""
        if self._relay is None:
            return
        for signal in (self._relay.done, self._relay.progress):
            try:
                signal.disconnect()
            except (TypeError, RuntimeError):
                pass  # no live connections

    def shutdown(self) -> None:
        """Freeze the runner: reject new submits and cancel every active
        generation. The dispatcher drops the late relay emissions."""
        with self._lock:
            self._closed = True
            for token in self._tokens.values():
                token.cancelled = True
