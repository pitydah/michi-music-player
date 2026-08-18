"""Async scan runner (M6.4) — Qt-based worker dispatch.

The heavy scan work runs on a plain worker thread; progress/done reach the
owner (GUI) thread through the Qt signal relay (queued connections). The
application service stays Qt-free — only this infrastructure adapter touches
Qt.
"""

import threading

from PySide6.QtCore import QObject, Signal

from michi.application.ports import (
    ScanCancelled,
    ScanCancelToken,
    ScanPipelinePort,
    ScanProgress,
)


class ScanRelay(QObject):
    """Thread-safe bridge for worker -> owner-thread dispatch."""

    done = Signal(int, object, object)  # generation, ScanResult|None, error|None
    progress = Signal(int, object)  # generation, ScanProgress


class ThreadScanRunner(ScanPipelinePort):
    """One worker thread per submit; cooperative cancellation via the token.

    The service-side callbacks (``on_progress``/``on_done``) are the port
    contract for deterministic test fakes; the production runner dispatches
    through the relay instead (bootstrap connects the relay signals to the
    service handlers), so they are intentionally unused here.
    """

    def __init__(self, relay: ScanRelay) -> None:
        self._relay = relay
        self._token = ScanCancelToken()

    def submit(self, generation, work, on_progress, on_done) -> None:
        def run() -> None:
            progress = ScanProgress()
            token = self._token

            def report() -> None:
                self._relay.progress.emit(generation, progress)

            try:
                result = work(progress, token, report)
            except ScanCancelled:
                self._relay.done.emit(generation, None, ScanCancelled())
                return
            except Exception as exc:  # typed scan errors propagate as-is
                self._relay.done.emit(generation, None, exc)
                return
            self._relay.done.emit(generation, result, None)

        threading.Thread(target=run, daemon=True).start()

    def cancel(self, generation: int) -> None:
        self._token.cancelled = True
