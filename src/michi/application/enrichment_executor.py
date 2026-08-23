"""Enrichment off-UI-thread execution (M6.9F).

All provider HTTP, JSON parsing, image decoding and asset downloads run
through this boundary — NEVER on the Qt UI thread. Framework-free
ThreadPoolExecutor; max 2 general provider workers (MusicBrainz remains
serialized by its own process-wide rate limiter).
"""

import threading
from concurrent.futures import ThreadPoolExecutor

from michi.application.enrichment_ports import EnrichmentExecutorPort


class ThreadPoolEnrichmentExecutor(EnrichmentExecutorPort):
    """Bounded provider worker pool with deterministic shutdown."""

    def __init__(self, max_workers: int = 2) -> None:
        self._pool = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="michi-enrichment"
        )
        self._lifecycle = threading.Lock()
        self._closed = False

    def submit(self, work) -> bool:
        """R1.2: admission-controlled — False when closed, never raises
        RuntimeError after shutdown."""
        with self._lifecycle:
            if self._closed:
                return False
            self._pool.submit(work)
            return True

    def shutdown(self, wait: bool = True) -> None:
        with self._lifecycle:
            self._closed = True
        # cancel_futures: queued-but-not-started jobs are dropped on
        # shutdown; running jobs finish within a bounded wait.
        self._pool.shutdown(wait=wait, cancel_futures=True)
