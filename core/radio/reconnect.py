from __future__ import annotations

import random
import time

from core.radio.models import ReconnectPolicyConfig, RadioError

_RECOVERABLE_ERRORS = frozenset({
    RadioError.CONNECTION_FAILED,
    RadioError.CONNECTION_TIMEOUT,
    RadioError.STREAM_NOT_FOUND,
    RadioError.SERVER_ERROR,
})

_UNRECOVERABLE_ERRORS = frozenset({
    RadioError.URL_INVALID,
    RadioError.URL_UNSUPPORTED_SCHEME,
    RadioError.URL_MALFORMED,
    RadioError.UNSUPPORTED_CONTENT_TYPE,
    RadioError.CANCELLED,
    RadioError.NOT_FOUND,
})


class ReconnectPolicy:
    def __init__(self, config: ReconnectPolicyConfig | None = None):
        self.config = config or ReconnectPolicyConfig()
        self._attempt = 0
        self._start_time: float | None = None
        self._cancelled = False

    def start(self):
        self._attempt = 0
        self._start_time = time.monotonic()
        self._cancelled = False

    def is_error_recoverable(self, error: RadioError) -> bool:
        if error in _RECOVERABLE_ERRORS:
            return True
        if error in _UNRECOVERABLE_ERRORS:
            return False
        return False

    def should_retry(self) -> bool:
        if not self.config.enabled:
            return False
        if self._cancelled:
            return False
        if self._attempt >= self.config.max_attempts:
            return False
        if self._start_time is not None:
            elapsed = time.monotonic() - self._start_time
            if elapsed >= self.config.max_total_seconds:
                return False
        return True

    def next_delay_ms(self) -> int:
        self._attempt += 1
        delay = self._compute_delay()
        return delay

    def cancel(self):
        self._cancelled = True

    def reset(self):
        self._attempt = 0
        self._start_time = None
        self._cancelled = False

    @property
    def attempt(self) -> int:
        return self._attempt

    def _compute_delay(self) -> int:
        if self._attempt <= 1:
            return 0
        base = self.config.base_delay_ms * (2 ** (self._attempt - 2))
        delay = min(base, self.config.max_delay_ms)
        jitter = random.randint(0, self.config.jitter_ms)
        return delay + jitter


class RadioScheduler:
    def __init__(self):
        self._timers: dict[int, object] = {}
        self._counter = 0

    def schedule(self, delay_ms: int, callback: callable) -> int:
        self._counter += 1
        token = self._counter
        import threading
        timer = threading.Timer(delay_ms / 1000.0, callback)
        timer.daemon = True
        self._timers[token] = timer
        timer.start()
        return token

    def cancel(self, token: int):
        timer = self._timers.pop(token, None)
        if timer:
            timer.cancel()

    def close(self):
        for timer in self._timers.values():
            timer.cancel()
        self._timers.clear()
