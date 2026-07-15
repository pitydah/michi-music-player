"""Hover effects — lightweight lift and shine for interactive surfaces."""

from __future__ import annotations

from typing import TYPE_CHECKING

from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QPoint, QEvent
from PySide6.QtWidgets import QGraphicsEffect

if TYPE_CHECKING:
    from PySide6.QtWidgets import QWidget


class HoverLiftFilter:
    """Light lift effect: max 2px upward movement on hover.

    Usage:
        HoverLiftFilter.install(widget, lift=2)
    """

    _installed: set[int] = set()

    @classmethod
    def install(cls, widget: QWidget, lift: int = 2):
        wid = id(widget)
        if wid in cls._installed:
            return
        cls._installed.add(wid)
        widget.installEventFilter(_HoverLift(lift, widget))


class _HoverLift(QGraphicsEffect):
    def __init__(self, lift: int, parent: QWidget):
        super().__init__(parent)
        self._lift = lift
        self._pos = 0
        self._anim = QPropertyAnimation(self, b"pos")
        self._anim.setDuration(120)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        parent.installEventFilter(self)

    def eventFilter(self, obj: QWidget, event: QEvent) -> bool:
        if event.type() == QEvent.Enter:
            self._anim.stop()
            self._anim.setStartValue(QPoint(0, 0))
            self._anim.setEndValue(QPoint(0, -self._lift))
            self._anim.start()
        elif event.type() == QEvent.Leave:
            self._anim.stop()
            self._anim.setStartValue(QPoint(0, -self._lift))
            self._anim.setEndValue(QPoint(0, 0))
            self._anim.start()
        return super().eventFilter(obj, event)
