from __future__ import annotations

import threading


class MetadataCancellationToken:
    def __init__(self):
        self._cancelled = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self):
        self._cancelled.set()

    def reset(self):
        self._cancelled.clear()


class MetadataCancellationSource:
    def __init__(self):
        self._token = MetadataCancellationToken()
        self._generation = 0

    @property
    def token(self) -> MetadataCancellationToken:
        return self._token

    def cancel(self):
        self._token.cancel()
        self._generation += 1

    def reset(self):
        self._token.reset()
        self._generation += 1

    @property
    def generation(self) -> int:
        return self._generation

    def is_stale(self, generation: int) -> bool:
        return generation != self._generation
