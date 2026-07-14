from __future__ import annotations

import threading


class LyricsCancellationToken:
    def __init__(self):
        self._cancelled = threading.Event()

    @property
    def cancelled(self) -> bool:
        return self._cancelled.is_set()

    def cancel(self):
        self._cancelled.set()

    def reset(self):
        self._cancelled.clear()


class LyricsCancellationSource:
    def __init__(self):
        self._token = LyricsCancellationToken()
        self._generation = 0

    @property
    def token(self) -> LyricsCancellationToken:
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


class LyricsRequestTracker:
    def __init__(self):
        self._current_request_id: str = ""
        self._current_track_hash: str = ""
        self._generation = 0
        self._source = LyricsCancellationSource()

    def begin(self, request_id: str, track_hash: str) -> LyricsCancellationToken:
        if self._current_request_id and self._current_request_id != request_id:
            self._source.cancel()
            self._source = LyricsCancellationSource()
        self._current_request_id = request_id
        self._current_track_hash = track_hash
        self._generation += 1
        return self._source.token

    def cancel_current(self):
        self._source.cancel()

    def is_stale(self, generation: int) -> bool:
        return generation != self._generation

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def current_request_id(self) -> str:
        return self._current_request_id


