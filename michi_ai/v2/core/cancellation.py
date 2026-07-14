from __future__ import annotations

import threading


class CancellationError(Exception):
    pass


class CancellationToken:
    def __init__(self) -> None:
        self._cancelled = threading.Event()
        self._reason = ""

    def cancel(self, reason: str = "cancelled") -> None:
        self._reason = reason
        self._cancelled.set()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    @property
    def reason(self) -> str:
        return self._reason

    def check(self) -> None:
        if self._cancelled.is_set():
            raise CancellationError(self._reason)

    def wait(self, timeout: float = 0.1) -> bool:
        return self._cancelled.wait(timeout=timeout)


class CancellationSource:
    def __init__(self) -> None:
        self._token = CancellationToken()
        self._lock = threading.Lock()

    @property
    def token(self) -> CancellationToken:
        return self._token

    def cancel(self, reason: str = "cancelled") -> None:
        with self._lock:
            self._token.cancel(reason)

    def reset(self) -> None:
        with self._lock:
            self._token = CancellationToken()


class CancellationTokenRegistry:
    def __init__(self) -> None:
        self._sources: dict[str, CancellationSource] = {}
        self._lock = threading.Lock()

    def register(self, key: str, source: CancellationSource) -> None:
        with self._lock:
            self._sources[key] = source

    def cancel(self, key: str, reason: str = "cancelled") -> bool:
        with self._lock:
            source = self._sources.get(key)
            if source is not None:
                source.cancel(reason)
                return True
            return False

    def remove(self, key: str) -> None:
        with self._lock:
            self._sources.pop(key, None)

    def get(self, key: str) -> CancellationSource | None:
        with self._lock:
            return self._sources.get(key)
