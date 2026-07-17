"""DebouncedQueryController — reusable debounce timer with cancel/generation.

Each change resets a 250ms timer. Enter fires immediately.
Escape clears. Stale results protected by generation counter.
"""
from __future__ import annotations

import logging

from PySide6.QtCore import QObject, QTimer

logger = logging.getLogger(__name__)


class DebouncedQueryController(QObject):
    def __init__(self, callback, delay_ms: int = 250, parent=None):
        super().__init__(parent)
        logger.debug("DebouncedQueryController.__init__ called")
        self._callback = callback
        self._delay = delay_ms
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._fire)
        self._gen = 0
        self._query = ""
        self._last_fired = ""

    def set_query(self, text: str):
        self._query = text
        self._timer.stop()
        if not text:
            self._gen += 1
            self._last_fired = ""
            self._callback("", self._gen)
        else:
            self._timer.start(self._delay)

    def fire_now(self):
        self._timer.stop()
        self._fire()

    def clear(self):
        self._timer.stop()
        self._gen += 1
        self._query = ""
        self._last_fired = ""
        self._callback("", self._gen)

    def cancel(self):
        self._timer.stop()
        self._gen += 1

    @property
    def generation(self) -> int:
        return self._gen

    @property
    def pending(self) -> bool:
        return self._timer.isActive()

    def _fire(self):
        if self._query != self._last_fired:
            self._gen += 1
            gen = self._gen
            q = self._query
            self._last_fired = q
            self._callback(q, gen)
